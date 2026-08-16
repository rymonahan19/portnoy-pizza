"""
PSI engine — Portnoy Score Index (working name).

Input : raw review records from https://api.onebite.app/review?userType=DAVE (list of dicts)
Output: metrics.json  (everything the public site needs, recomputed on every new score)
        reviews.json  (compact ledger, one row per scoring event)
        reviews.csv   (same, for spreadsheets)

Data policy (see SPEC.md §3):
  Tier A  ARCHIVE      = every DAVE record, verbatim. Never deleted.
  Tier B  CALIBRATION  = ARCHIVE minus protest scores (< 1.0) minus pre-era backfill (< 2016-01-01)
Metrics are computed on CALIBRATION; the site displays ARCHIVE with badges.
"""
import json, csv, math, os, datetime as dt
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
def _load_json(name, default):
    for path in (os.path.join(os.getcwd(), name), os.path.join(_HERE, name)):
        if os.path.exists(path):
            return json.load(open(path))
    return default
CONFIG = _load_json("config.json", {})
PROTEST_CEILING = CONFIG.get("protest_ceiling", 1.0)   # scores strictly below this are statements, not measurements
ERA_START       = CONFIG.get("era_start", "2016-01-01")  # systematic reviewing begins; earlier records are retro-logged
WINDOW_DAYS     = CONFIG.get("window_days", 365)       # "current regime" = trailing 12 months
ROLL_N          = CONFIG.get("roll_n", 200)            # rolling window (in reviews) for the inflation curve
BASE_YEAR       = CONFIG.get("base_year", 2019)        # reference year for the headline translation
GRADES = [tuple(g) for g in CONFIG.get("grades", [[97,"Rarefied air"],[90,"Elite"],[75,"Great"],[55,"Above average"],[40,"Average"],[25,"Below average"],[10,"Poor"],[0,"Bad"]])]
OVERRIDES = _load_json("overrides.json", {})            # manual enrichment for records with missing venue data (see SPEC §3.3)

STATE_ABBR = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia"}
def norm_state(s):
    if not s: return None
    s = s.strip()
    return STATE_ABBR.get(s.upper(), s)

def _coords(r, v):
    for c in ((v.get("loc") or {}).get("coordinates"), (r.get("loc") or {}).get("coordinates")):
        if c and len(c) == 2 and not (abs(c[0]) < 1e-6 and abs(c[1]) < 1e-6):
            return c
    return [None, None]

# ---------- normalization ----------
def normalize(raw):
    rows = []
    for r in raw:
        v = r.get("venue") or {}
        date = (r.get("date") or r.get("created_at") or "")[:10]
        score = r.get("score")
        if score is None or not date:
            continue
        loc = _coords(r, v)
        row = dict(
            id=r.get("id"), date=date, score=float(score),
            venue=r.get("title") or v.get("name"), city=v.get("city"), state=norm_state(v.get("state")),
            country=v.get("country"), place_id=v.get("placeId"), slug=v.get("slug"),
            lng=loc[0], lat=loc[1],
            protest=float(score) < PROTEST_CEILING,
            pre_era=date < ERA_START,
            venue_unresolved=not v.get("name"),
        )
        row["venue_source"] = "onebite"
        ov = OVERRIDES.get(row["id"])
        if ov:
            if ov.get("venue"):
                row["venue"] = ov["venue"]; row["venue_unresolved"] = False
                row["venue_source"] = f"override:{ov.get('confidence','?')}"
            for k in ("city", "state"):
                if ov.get(k) and not row.get(k): row[k] = ov[k]
            if ov.get("evidence", "").startswith("http"): row["evidence_url"] = ov["evidence"]
        row["in_calibration"] = not row["protest"] and not row["pre_era"]
        row["url"] = f"https://onebite.app/restaurant/{v['slug']}/review/{r.get('id')}" if v.get("slug") else None
        rows.append(row)
    rows.sort(key=lambda x: (x["date"], x["id"] or ""))
    return rows

# ---------- stats helpers ----------
def quantile(sorted_vals, q):
    """Linear-interpolated empirical quantile (numpy 'linear' / R type 7). q in [0,1]."""
    n = len(sorted_vals)
    if n == 0: return None
    if n == 1: return sorted_vals[0]
    pos = q * (n - 1); lo = math.floor(pos); hi = math.ceil(pos)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)

def pct_rank(sorted_vals, s):
    """Mid-rank percentile (0-100): share below + half the share equal."""
    n = len(sorted_vals)
    if n == 0: return None
    below = sum(1 for v in sorted_vals if v < s - 1e-9)
    equal = sum(1 for v in sorted_vals if abs(v - s) < 1e-9)
    return 100.0 * (below + 0.5 * equal) / n

def summarize(vals):
    if not vals: return None
    s = sorted(vals); n = len(s); mean = sum(s) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in s) / n)
    return dict(n=n, mean=round(mean, 3), median=round(quantile(s, .5), 2), sd=round(sd, 3),
                min=s[0], max=s[-1], p10=round(quantile(s, .10), 2), p25=round(quantile(s, .25), 2),
                p75=round(quantile(s, .75), 2), p90=round(quantile(s, .90), 2),
                share_ge_8=round(100 * sum(1 for x in s if x >= 8.0) / n, 1),
                share_ge_9=round(100 * sum(1 for x in s if x >= 9.0) / n, 1),
                count_ge_9=sum(1 for x in s if x >= 9.0))

def grade_for(p):
    for lo, label in GRADES:
        if p >= lo: return label
    return GRADES[-1][1]

# ---------- the index ----------
def compute(rows, as_of=None):
    as_of = as_of or dt.date.today()
    cal = [r for r in rows if r["in_calibration"]]
    years = sorted({r["date"][:4] for r in cal})
    by_year = {y: sorted(r["score"] for r in cal if r["date"].startswith(y)) for y in years}
    year_stats = {y: summarize(v) for y, v in by_year.items()}

    # current regime = trailing WINDOW_DAYS
    cutoff = (as_of - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    window = sorted(r["score"] for r in cal if r["date"] > cutoff)
    regime = summarize(window)

    # eras (breakpoints observed in the data; see SPEC.md §4.3)
    era_defs = [("Wide scale", "2016", "2019"), ("Compression", "2020", "2023"), ("Narrow band", "2024", "2099")]
    eras = []
    for name, a, b in era_defs:
        vals = sorted(r["score"] for r in cal if a <= r["date"][:4] <= b)
        st = summarize(vals)
        if st: eras.append(dict(name=name, start=a, end=min(b, years[-1]), **st))

    # rolling inflation curve (by review count) — mean & sd of last ROLL_N calibration scores
    roll = []
    for i in range(ROLL_N - 1, len(cal), 5):
        seg = [r["score"] for r in cal[i - ROLL_N + 1:i + 1]]
        m = sum(seg) / len(seg); sd = math.sqrt(sum((x - m) ** 2 for x in seg) / len(seg))
        roll.append(dict(date=cal[i]["date"], mean=round(m, 3), sd=round(sd, 3)))

    # translation table for the score grid: for each 0.1 score, percentile-now, grade, equivalents by year
    def equivalents(p):
        return {y: round(quantile(by_year[y], p / 100.0), 1) for y in years if year_stats[y]["n"] >= 30}
    grid = []
    for k in range(0, 101):
        s = round(k / 10, 1); p = pct_rank(window, s)
        grid.append(dict(score=s, pct_now=round(p, 1), grade=grade_for(p), equiv=equivalents(p)))

    # latest verdict
    latest = rows[-1]
    p_latest = pct_rank(window, latest["score"])
    higher_in_window = sum(1 for v in window if v > latest["score"] + 1e-9)
    verdict = dict(**{k: latest[k] for k in ("id", "date", "score", "venue", "city", "state", "url", "protest", "in_calibration")},
                   pct_now=round(p_latest, 1), grade=grade_for(p_latest), higher_in_window=higher_in_window,
                   window_n=len(window), equiv=equivalents(p_latest),
                   equiv_base_year=round(quantile(by_year[str(BASE_YEAR)], p_latest / 100.0), 1))

    # 9-drought
    nines = [r for r in cal if r["score"] >= 9.0]
    last9 = nines[-1] if nines else None
    since9 = sum(1 for r in cal if last9 and r["date"] > last9["date"])
    nines_by_year = {y: year_stats[y]["count_ge_9"] for y in years}

    counts = dict(archive=len(rows), calibration=len(cal),
                  protest=sum(r["protest"] for r in rows), pre_era=sum(r["pre_era"] for r in rows),
                  venue_unresolved=sum(r["venue_unresolved"] for r in rows),
                  first_date=rows[0]["date"], last_date=rows[-1]["date"])

    return dict(generated_at=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z"), as_of=as_of.isoformat(),
                methodology_version=CONFIG.get("methodology_version", "1.2"),
                params=dict(protest_ceiling=PROTEST_CEILING, era_start=ERA_START, window_days=WINDOW_DAYS,
                            roll_n=ROLL_N, base_year=BASE_YEAR, grades=GRADES),
                counts=counts, year_stats=year_stats, regime=regime, eras=eras, rolling=roll,
                grid=grid, latest=verdict, nines=dict(last=last9, reviews_since=since9, by_year=nines_by_year))

def write_outputs(rows, metrics, outdir="."):
    json.dump(metrics, open(f"{outdir}/metrics.json", "w"), indent=1)
    keep = ["id", "date", "score", "venue", "city", "state", "country", "lat", "lng", "protest", "pre_era",
            "venue_unresolved", "venue_source", "in_calibration", "url"]
    json.dump([{k: r[k] for k in keep} for r in rows], open(f"{outdir}/reviews.json", "w"))
    with open(f"{outdir}/reviews.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keep + ["place_id"]); w.writeheader()
        for r in rows: w.writerow({k: r.get(k) for k in keep + ["place_id"]})

if __name__ == "__main__":
    import sys
    raw = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "dave_api_raw.json"))
    rows = normalize(raw); m = compute(rows); write_outputs(rows, m)
    print(json.dumps(dict(counts=m["counts"], regime=m["regime"], latest={k: m["latest"][k] for k in ("date","score","venue","pct_now","grade","equiv_base_year","higher_in_window")}), indent=1))
    for y, s in m["year_stats"].items():
        print(f"{y}: n={s['n']:3d} mean={s['mean']:.2f} med={s['median']:.2f} sd={s['sd']:.2f} p10={s['p10']} p90={s['p90']} max={s['max']} ge8={s['share_ge_8']}% n9={s['count_ge_9']}")
    print("eras:", [(e['name'], e['start'], e['end'], e['n'], e['mean'], e['sd']) for e in m['eras']])
    print("nines:", m["nines"]["last"]["date"] if m["nines"]["last"] else None, m["nines"]["reviews_since"], m["nines"]["by_year"])
    for s in (7.0, 7.5, 8.0, 8.5, 9.0):
        g = next(x for x in m["grid"] if abs(x["score"] - s) < 1e-9)
        print(f"  {s} today -> p{g['pct_now']} {g['grade']} | 2017:{g['equiv'].get('2017')} 2019:{g['equiv'].get('2019')} 2021:{g['equiv'].get('2021')} 2023:{g['equiv'].get('2023')} 2025:{g['equiv'].get('2025')}")
