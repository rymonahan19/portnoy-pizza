"""
PSI poller — run on a schedule (every 5–10 min). Detects new Dave scores, merges them into the
ledger, recomputes metrics.json, and (optionally) pings a webhook.

  python psi_poller.py            # incremental: fetch newest 25, merge, recompute if anything changed
  python psi_poller.py --full     # weekly reconcile: re-pull the entire archive, detect edits/removals

Source: https://api.onebite.app/review?userType=DAVE&limit=100&offset=N   (newest first, no auth)
Fallback: https://onebite.app/reviews/dave?page=N  (same records inside <script id="__NEXT_DATA__">)
"""
import json, os, re, sys, time, urllib.request, datetime as dt
import psi_engine

API   = "https://api.onebite.app/review?userType=DAVE&limit={limit}&offset={offset}"
HTML  = "https://onebite.app/reviews/dave?page={page}&minScore=0&maxScore=10"
HDRS  = {"User-Agent": "portnoy.pizza index bot/1.0 (+https://portnoy.pizza; contact: hello@portnoy.pizza)", "Origin": "https://onebite.app",
         "Referer": "https://onebite.app/reviews/dave"}
STATE = os.environ.get("PSI_STATE", "ledger_raw.json")   # the archive of raw API records
OUT   = os.environ.get("PSI_OUT", ".")
WEBHOOK = os.environ.get("PSI_WEBHOOK")                   # optional: POST here when a new score lands

class SchemaDrift(Exception):
    """Upstream records no longer look like reviews (missing id/score/date). Never write on drift."""

def validate(batch):
    bad = [r for r in batch if not isinstance(r, dict) or r.get("id") is None or r.get("score") is None or not (r.get("date") or r.get("created_at"))]
    if bad:
        raise SchemaDrift(f"{len(bad)} of {len(batch)} records missing id/score/date")
    return batch

def write_status(ok, message, source, records=None, extra=None):
    latest = max((r.get("date") or r.get("created_at") or "" for r in (records or [])), default=None)
    st = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"), "ok": ok, "message": message,
          "source": source, "archive_count": len(records or []), "last_score_date": (latest or "")[:10] or None}
    if extra: st.update(extra)
    try:
        st["stale"] = bool(latest) and (dt.datetime.now(dt.timezone.utc).date() - dt.date.fromisoformat(latest[:10])).days > 10
    except Exception: st["stale"] = False
    try: json.dump(st, open(os.path.join(OUT, "status.json"), "w"), indent=1)
    except Exception as e: print("status write failed:", e, file=sys.stderr)
    return st

def _get(url, tries=4):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=HDRS), timeout=60).read().decode("utf-8", "ignore")
        except Exception as e:
            err = e; time.sleep(2 * (i + 1))
    raise err

def fetch_api(limit=100, offset=0):
    return validate(json.loads(_get(API.format(limit=limit, offset=offset))))

def fetch_html_fallback(page=1):
    html = _get(HTML.format(page=page))
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return validate(json.loads(m.group(1))["props"]["pageProps"]["reviews"])

SOURCE_USED = {"name": "api"}
def fetch_newest(n=25):
    try:
        SOURCE_USED["name"] = "api"
        return fetch_api(limit=n, offset=0)
    except SchemaDrift:
        raise
    except Exception as e:
        print("API failed, using HTML fallback:", e, file=sys.stderr)
        SOURCE_USED["name"] = "html_fallback"
        return fetch_html_fallback(1)

def fetch_all():
    out, off = [], 0
    while True:
        batch = fetch_api(limit=100, offset=off)
        if not batch: break
        out.extend(batch); off += 100
        if len(batch) < 100: break
        time.sleep(0.3)
    return out

def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else []

def save_state(records):
    json.dump(records, open(STATE, "w"))

def _q(v):
    if v is None: return "NULL"
    if isinstance(v, bool): return "1" if v else "0"
    if isinstance(v, (int, float)): return repr(v)
    return "'" + str(v).replace("'", "''") + "'"

def write_seed_sql(rows, metrics, outdir):
    """D1 loader consumed by: wrangler d1 execute psi --remote --file out/seed.sql  (idempotent: full replace)."""
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    cols = ["id","date","score","venue","city","state","country","lat","lng","protest","pre_era","venue_unresolved","venue_source","in_calibration","url","place_id"]
    with open(os.path.join(outdir, "seed.sql"), "w") as f:
        f.write("DELETE FROM reviews;\n")
        for i in range(0, len(rows), 50):   # ~40 KB per statement, safely under D1's per-statement ceiling
            vals = ",".join("(" + ",".join(_q(r.get(c)) for c in cols) + ")" for r in rows[i:i+50])
            f.write(f"INSERT INTO reviews ({','.join(cols)}) VALUES {vals};\n")
        # reviews.json is NOT stored as a blob (too large for one statement); the Pages Function builds it from the reviews table
        for key, path in (("metrics.json", "metrics.json"), ("status.json", "status.json")):
            fp = os.path.join(outdir, path)
            if os.path.exists(fp):
                f.write(f"INSERT OR REPLACE INTO blobs (key, value, updated_at) VALUES ({_q(key)}, {_q(open(fp).read())}, {_q(now)});\n")

def recompute(records):
    rows = psi_engine.normalize(records)
    metrics = psi_engine.compute(rows)
    psi_engine.write_outputs(rows, metrics, OUT)
    return metrics

def notify(metrics, new_records):
    if not WEBHOOK: return
    payload = {"event": "new_scores", "new": [{"id": r["id"], "score": r["score"], "date": r["date"],
               "venue": r.get("title") or (r.get("venue") or {}).get("name")} for r in new_records],
               "latest_verdict": metrics["latest"]}
    req = urllib.request.Request(WEBHOOK, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req, timeout=30)
    except Exception as e: print("webhook failed:", e, file=sys.stderr)

def main():
    full = "--full" in sys.argv
    state = load_state()
    by_id = {r["id"]: r for r in state}
    try:
        _run(full, state, by_id)
    except SchemaDrift as e:
        write_status(False, f"SCHEMA DRIFT — nothing written: {e}", SOURCE_USED["name"], state)
        print("ALERT schema drift:", e, file=sys.stderr); sys.exit(2)
    except Exception as e:
        write_status(False, f"poll failed: {type(e).__name__}: {e}", SOURCE_USED["name"], state)
        print("ALERT poll failed:", e, file=sys.stderr); sys.exit(1)

def _run(full, state, by_id):
    if full or not state:
        fresh = fetch_all()
        fresh_ids = {r["id"] for r in fresh}
        removed = [i for i in by_id if i not in fresh_ids]
        changed = [r for r in fresh if r["id"] in by_id and by_id[r["id"]].get("score") != r.get("score")]
        added   = [r for r in fresh if r["id"] not in by_id]
        print(f"full reconcile: {len(fresh)} records | +{len(added)} new, {len(changed)} score edits, {len(removed)} removed")
        if removed or changed:
            with open(os.path.join(OUT, "changelog.jsonl"), "a") as f:
                for r in changed: f.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(), "type": "score_edit", "id": r["id"], "old": by_id[r["id"]].get("score"), "new": r.get("score")}) + "\n")
                for i in removed: f.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(), "type": "removed", "id": i, "record": by_id[i]}) + "\n")
        save_state(fresh); m = recompute(fresh); notify(m, added)
        write_status(True, f"full reconcile ok: +{len(added)} new, {len(changed)} edits, {len(removed)} removed", "api", fresh, {"changed": max(1, len(added)+len(changed)+len(removed))})
        write_seed_sql(psi_engine.normalize(fresh), m, OUT)
        return
    newest = fetch_newest(25)
    added = [r for r in newest if r["id"] not in by_id]
    edited = [r for r in newest if r["id"] in by_id and by_id[r["id"]].get("score") != r.get("score")]
    if not added and not edited:
        write_status(True, "no change", SOURCE_USED["name"], state, {"changed": 0})
        print(dt.datetime.now().isoformat(), "no change"); return
    for r in added + edited: by_id[r["id"]] = r
    records = list(by_id.values())
    save_state(records); m = recompute(records); notify(m, added)
    write_status(True, f"+{len(added)} new, {len(edited)} edits", SOURCE_USED["name"], records, {"changed": len(added)+len(edited), "latest_verdict": {k: m["latest"][k] for k in ("date","score","venue","pct_now","grade")}})
    write_seed_sql(psi_engine.normalize(records), m, OUT)
    for r in added:
        print(f"NEW  {r['date'][:10]}  {r['score']}  {r.get('title') or (r.get('venue') or {}).get('name')}  -> p{m['latest']['pct_now']} {m['latest']['grade']}")
    for r in edited:
        print(f"EDIT {r['id']} score now {r['score']}")

if __name__ == "__main__":
    main()
