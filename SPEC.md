# Portnoy Score Index (PSI) — Specification v1.2

**Live domain: [portnoy.pizza](https://portnoy.pizza)** (registered). **onebitescores.com** (registered) forwards to it with a 301 and is never branded or linked as a site of its own — see §6.4 and §8.

**What it is.** A public, continuously updated reference that takes any pizza score Dave Portnoy gives and answers two questions instantly: *how good is that score right now* (percentile within his current scoring regime), and *what would that score have been in any past year* (era-adjusted equivalent). Think CPI for pizza scores: a nominal number, deflated into constant terms, published by an independent body every time a new score drops.

**Status of this document.** The data has been pulled in full and verified, the engine has been written and run, and the prototype is built from real numbers. Everything below is grounded in the actual archive as of 15 Aug 2026, not estimates.

---

## 1. Headline findings from the full archive

| | |
|---|---|
| Total Dave reviews in the One Bite system | **2,150** (matches the app's own count for his account exactly) |
| Date span | 13 Mar 2013 → 13 Aug 2026 |
| Lifetime mean (all records) | 7.03 |
| Trailing 12 months (calibration set) | n=155 · mean 7.40 · median 7.5 · sd 0.69 · p90 8.1 · max 8.5 · 15.5% of scores ≥ 8.0 · zero 9s |
| Latest score | 8.2, Liguria Pizzeria (Philadelphia), 13 Aug 2026 → **95th percentile of the last 12 months, "Elite"**; only 2 higher scores in the past year; ≈ 8.4 in 2019 terms |
| Scores of 9.0+ ever | 22 in 13 years; four since 2020; **205 reviews since the last one** (Ceres, 13 May 2025) |
| Only 10 ever | Monte's Restaurant, Lynn MA (2015) |

**The shape of the inflation.** Three eras are visible in the numbers, with breaks at 2020 and 2024:

| Era | Years | n | Mean | SD | p10 | p90 | Max |
|---|---|---|---|---|---|---|---|
| Wide scale | 2016–2019 | 705 | 6.64 | 1.60 | ~4.0–4.9 | 8.1–8.3 | 9.4 |
| Compression | 2020–2023 | 895 | 7.20 | 0.93 | ~6.1–6.6 | 8.1 | 9.4 |
| Narrow band | 2024–present | 521 | 7.43 | 0.67 | ~6.5–6.8 | 8.1–8.2 | 9.2 |

The critical nuance, and the reason the method in §4 is quantile-based rather than a simple average shift: **his ceiling has barely moved, his floor has risen dramatically.** The 90th percentile has been 8.1 in nearly every year since 2018. What changed is the bottom: p10 climbed from 3.9 (2016) to 6.8 (2026). Consequences the site will make visible:

- A **7.0 today is a bad score** — 20th percentile of the last 12 months, the equivalent of a 5.2 in 2017 or a 6.1 in 2019.
- An **8.0 today is roughly still an 8.0** across eras (85th percentile now; ~8.1 in 2017 terms). It's genuinely a great score, which is exactly the point people miss when they're disappointed by it.
- Above 8.3 the compression bites: an **8.5 today ≈ 9.1 in 2019 / 9.3 in 2017**, and a **9.0 today is above every score of the past year.**
- 2026 year-to-date is the tightest year on record (sd 0.48, range 6.3–8.5) and the first year since 2017 where more than 20% of scores are 8.0+ (22.9%). Real inflation at the top may be starting; the index will show it if it continues.

Full per-year table (calibration set):

| Year | n | Mean | Median | SD | p10 | p90 | Min | Max | ≥8.0 | 9s |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 65 | 6.55 | 6.90 | 1.87 | 3.9 | 8.3 | 1.5 | 9.3 | 21.5% | 3 |
| 2017 | 185 | 6.48 | 6.90 | 1.81 | 4.0 | 8.3 | 1.0 | 9.4 | 22.2% | 5 |
| 2018 | 208 | 6.65 | 6.90 | 1.51 | 4.6 | 8.1 | 1.2 | 9.3 | 13.5% | 3 |
| 2019 | 247 | 6.78 | 7.10 | 1.42 | 4.9 | 8.1 | 1.4 | 9.2 | 13.0% | 3 |
| 2020 | 185 | 7.22 | 7.40 | 0.86 | 6.3 | 8.1 | 1.9 | 8.9 | 14.1% | 0 |
| 2021 | 227 | 7.22 | 7.30 | 0.81 | 6.6 | 8.1 | 2.9 | 9.3 | 10.6% | 1 |
| 2022 | 239 | 7.15 | 7.40 | 1.10 | 6.1 | 8.1 | 1.2 | 9.4 | 15.5% | 1 |
| 2023 | 244 | 7.24 | 7.40 | 0.91 | 6.2 | 8.1 | 1.2 | 9.1 | 13.5% | 1 |
| 2024 | 236 | 7.46 | 7.60 | 0.58 | 6.6 | 8.1 | 4.8 | 8.6 | 16.5% | 0 |
| 2025 | 202 | 7.32 | 7.40 | 0.81 | 6.5 | 8.1 | 2.8 | 9.2 | 14.4% | 1 |
| 2026 YTD | 83 | 7.59 | 7.70 | 0.48 | 6.8 | 8.2 | 6.3 | 8.5 | 22.9% | 0 |

(2013–2015: 14 retro-logged reviews, excluded from calibration — see §3.4.)

---

## 2. Scope decisions (confirmed)

**Portnoy only.** Every record carries `userType: "DAVE"` and `user.username: "stoolpresidente"`. Celebrity, fan, and "critic" reviews live under separate user types and are excluded at the query level. The archive contains no separately recorded guest scores (`guests` is empty on all 2,150 records), so every score in the set is his.

**Pizza only.** The One Bite archive is pizza by construction — it is a pizza app, and every one of his reviews in it is a pizza review at a venue (bars, breweries, delis and Italian restaurants included, because he scored their pizza). A short **manual verification queue** exists for edge cases: MrBeast Burger (29 Dec 2022, 7.1) is the one venue whose name suggests a possible non-pizza review; it stays in the archive with a `verify` flag until confirmed against the video. Frozen-pizza and other off-venue reviews do not appear in the archive at all (zero matches for "frozen").

**Every score counts as a scoring event**, including re-reviews of the same venue. The unit of analysis is the score, not the restaurant.

---

## 3. Data: source, access, verification, policy

### 3.1 Source
The One Bite backend at `https://api.onebite.app` — the same store the iPhone app and onebite.app read from. The reviews resource is public and unauthenticated:

```
GET https://api.onebite.app/review?userType=DAVE&limit=100&offset=0
```

Newest first, hard ceiling of 100 per call (500 returns HTTP 500), 22 calls for the full archive. Each record includes: `id`, `date`, `score`, `title`, `venue{name, city, state, country, placeId, slug, categories, loc}`, `loc.coordinates`, `media` (Mux video asset id), `featured`, `intro`, `status`, engagement counts. Field-level schema is in `psi_engine.normalize()`.

**Fallback source:** the same records are embedded verbatim in the HTML of `https://onebite.app/reviews/dave?page=N` inside `<script id="__NEXT_DATA__">` (30 per page, 72 pages). Both paths are implemented in `psi_poller.py`; if the API changes shape, the poller flips to HTML and raises an alert.

### 3.2 Verification performed
Both sources were pulled independently and reconciled: 2,150 records each, identical ID sets, zero differences. The count matches `user.reviewStats.count = 2150` reported by the app for his account. All records are `status: VISIBLE`, all `media.type: VIDEO`. No missing scores, no missing dates.

### 3.3 Known data quirks (all handled)
- **15 protest scores below 1.0** (Blaze Pizza 0, Amtrak 0.08, 7-Eleven 0.02, Cumberland Farms 0.08, Churchill Downs 0.2, LexLive 0.04, etc.). Real reviews, but statements rather than measurements — the equivalent of a boycott, not a price. Kept in the archive, badged, excluded from calibration.
- **14 retro-logged reviews dated 2013–2015** — Boston-area favorites (Town Spa 9.0, Monte's 10, Pepe's 9.4). Selection-biased greatest hits, not a sample of his scoring in those years. Kept, badged "archival", excluded from calibration.
- **38 records with no venue** (name/city/state null) — **25 now resolved** in `overrides.json` (each with a confidence level and evidence link): 21 *high* by matching the review date to Barstool's own story titles ("Barstool Pizza Review – {Venue} ({City}, {ST})", pulled from `union.barstoolsports.com/v2/stories/search`, indexed back to March 2023) and confirming the coordinates by reverse geocoding; 4 *medium* from the OSM point-of-interest sitting exactly at the coordinates (Luigi's Pizza 8th Ave 2017, Lions & Tigers & Squares 2018, Owl's Nest 2020, Siena Pizza & Cannoli 2021 — verify against the videos before quoting them by name); Wawa, Sea Isle City (Sept 2021) is *high* (POI plus press coverage). **13 remain**: 10 with a street location but no name (kept in calibration; shown as "Unidentified venue" with the city), and 3 from 2017 with no coordinates at all — including the 9.3 of 16 Jan 2017 that sits in the 9.0 club. Resolution path for those: the One Bite YouTube channel's uploads for that week (title carries venue and city). Score and date are intact throughout, so **all 38 stay in calibration**.
- **Odd decimals** — 6.66 (Marquis Pizza), 7.74 (Ducali) — are real and kept.
- **Score edits and removals** happen occasionally upstream. The weekly full reconcile (`psi_poller.py --full`) diffs the whole archive and logs any changed score or vanished ID; the archive is append-only with a change log rather than silently overwritten.

### 3.4 Data policy — two tiers
- **Tier A · Archive** — every DAVE record, verbatim, append-only. What the site's ledger shows. Currently 2,150.
- **Tier B · Calibration set** — Archive minus protest scores (<1.0) minus pre-era records (before 1 Jan 2016). What every statistic is computed from. Currently 2,121.

Each row carries flags: `protest`, `pre_era`, `venue_unresolved`, `in_calibration`, plus a link back to the review on onebite.app.

---

## 4. Methodology

### 4.1 The current regime
"Right now" = the trailing 365 days of calibration scores as of the moment of computation (currently n=155). The window slides daily and is recomputed on every new score. Twelve months is long enough to be stable (~200 reviews at his cadence) and short enough to track a change in his scoring within a season. Configurable (`WINDOW_DAYS`).

### 4.2 Percentile now
Mid-rank percentile within the current regime: share of window scores strictly below *s*, plus half the share exactly equal to *s*, ×100. Reported as "top X%" on the site. A score above the window maximum reports as the 100th percentile with an explicit "higher than every score in the past 12 months" callout rather than a fake decimal.

### 4.3 Era equivalence (the deflator) — quantile mapping
For a score *s* today and a target year *Y*:

1. p = percentile of *s* in the current regime (§4.2).
2. Equivalent(s → Y) = the score at percentile p in year Y's calibration distribution, linearly interpolated between order statistics (R type 7 / numpy "linear"), rounded to 0.1.

Worked example, today: 8.2 → p95.2 → the 95.2nd percentile of 2019 is 8.4, of 2017 is 8.6. So "8.2 today ≈ 8.4 in 2019, 8.6 in 2017." The reverse direction (a past score into today's terms) uses the same map inverted and appears in the ledger for every historical review.

**Why not a simple average shift** ("subtract 0.4 because his mean is up 0.4"): it assumes his whole scale moved together. It didn't. An additive shift would say an 8.0 today was a 7.6 in 2019 — but the 2019 90th percentile was 8.1, so 8.0 was already an elite score then. Quantile mapping handles the average *and* the spread, and it is exactly the machinery behind chained price indices. It is what makes "governing body" defensible.

**Base year for the headline number:** 2019 — the last full year before compression, n=247. Every year is available in the translator; 2019 is the one quoted in the one-line verdict.

### 4.4 Grades (public labels for percentile bands)
Rarefied air ≥97 · Elite 90–97 · Great 75–90 · Above average 55–75 · Average 40–55 · Below average 25–40 · Poor 10–25 · Bad <10. Under the current regime that puts 8.5 in "Rarefied air", 8.2 in "Elite", 8.0 in "Great", 7.5 dead "Average", 7.0 "Poor". Labels are configuration, not code.

### 4.5 Supporting series
- **Year-over-year**: n, mean, median, sd, min, max, p10, p25, p75, p90, share ≥8.0, share ≥9.0 per calendar year (the table in §1). Current year is labelled YTD.
- **Rolling inflation curve**: mean and sd of the last 200 calibration reviews, stepped every 5 reviews — the "price level" line.
- **The 9 drought**: reviews (and days) since the last 9.0+, and 9s per year.
- **Eras**: the three regimes in §1, with breakpoints stated as observed rather than assumed.

### 4.5b Era-adjusted rank (leaderboard)
z = (score − mean of that calendar year's calibration set) ÷ that year's standard deviation. Ranks by z, ties by raw score. Pre-2016 records are measured against the 2016 field and marked as such. This is the leaderboard's alternate ordering, not the site's headline metric; the headline metric remains percentile-now with quantile mapping (§4.2–4.3).

### 4.6 Refresh semantics
Every metric is recomputed from scratch on each new score (the whole computation takes well under a second for 2k rows). No incremental approximations, so there is nothing to drift. Methodology is versioned (v1.0); any change to window, base year, grade bands, or exclusion rules is a version bump with a dated note on the site's method page, so past verdicts remain explainable.

---

## 5. What the public site shows

1. **Latest verdict** — the newest score, venue, and one sentence: "8.2 · Liguria Pizzeria · 95th percentile of the last 12 months (Elite) · only 2 higher scores this year · ≈ 8.4 in 2019 terms."
2. **The translator** — enter or drag any score 0–10; see percentile now, grade, and its equivalent in every year 2016–present. This is the product.
3. **Year-over-year chart** — per year: high/low range, interquartile band, median dot, mean line, with the current year marked YTD.
4. **Current regime card** — trailing-12-month n, mean, median, sd, p90, max, share ≥8.0, and the 9 drought counter.
5. **The ledger** — every review, newest first, with score, venue, date, percentile-at-the-time and today's-terms equivalent, badges for protest/archival/unresolved, and a link back to onebite.app.
6. **Method page** — §3–4 in plain English, plus a changelog and a data-freshness stamp ("last checked 3 minutes ago; last new score 13 Aug").
7. **Near me** (added v1.2) — a Zillow-style map: every scored venue as a pin labelled with his score, colour-banded (red 8.5+, black 8.0–8.4, white 7.5–7.9, grey below), a "use my location" button (browser geolocation; nothing stored), a city/state search (state = whole state; city = 5/15/50/150-mile radius that auto-widens if fewer than 8 results), quick chips for the big pizza cities, and a card list below sortable by nearest / highest / newest with distance, score, and each score's "top X% of its year". 2,147 of 2,150 reviews carry coordinates from the app's own venue records; every venue also has a Google Place ID, so production can attach hours, photos and directions via Places. Prototype uses Leaflet with CARTO light tiles and falls back to a distance-ring "radar" if the map library or tiles are blocked; production should use Google Maps or MapTiler with a proper key and attribution.
8. **All-time leaderboard** (added v1.2) — the prestige page. Uses the Archive tier (retro-logged 2013–15 reviews count, badged "archival"; protest scores excluded). Monte's 10 holds №1 alone; the board runs №2 through every score of 8.5 or better (70 rows today), tiered "The 9.0 club" and "8.5 and up", ties sharing a rank with the earlier review first, each row showing where the score sat in its own year ("top 0.5% of 2017"). A second mode, **Era-adjusted**, ranks by standard deviations above that year's mean — the index's own measure of dominance — and reshuffles the board in a way that makes the whole thesis visible: Luigi's 9.3 (2021, +2.58σ) is the most dominant score ever given; Calabria's 8.9 (2021) outranks DeLucia's 9.4 (2022). Gold is used on this page and nowhere else.

---

## 6. Real-time architecture for the public site

```
 every 5 min ─▶ poller ──▶ api.onebite.app/review?userType=DAVE&limit=25
                  │            (fallback: onebite.app/reviews/dave HTML)
                  ├─ diff by id + score ─▶ append to ledger (D1 / Postgres / JSON)
                  ├─ recompute metrics (psi_engine.compute)
                  ├─ write metrics.json + reviews.json to edge storage (KV / R2 / S3)
                  └─ optional webhook (Slack / X post / push) on a new score
 site (static) ◀── reads metrics.json (cache 60s) ── shows verdict, translator, charts
 weekly ────▶ poller --full : re-pull all 22 pages, detect edits/removals, log changes
```

**Provisioned 16 Aug 2026 via your Cloudflare connector:** KV namespace `psi-data` (`b90a2a5a7fbf44b5ac1af0b6d0fc00ac`) and D1 database `psi` (`dd27023a-5b94-4a34-bd4c-d08d520336d8`, ENAM) with `reviews` / `blobs` / `changelog` tables. R2 requires a one-time enable in the dashboard. The poller emits `seed.sql` (idempotent full replace) so D1 fills on the first workflow run; the Pages Function reads KV first and falls back to D1.

**Recommended stack (cheapest, and you already have Cloudflare connected):** Cloudflare Worker with a Cron Trigger (`*/5 * * * *`) running the poller logic; D1 for the ledger; KV or R2 for `metrics.json`; Cloudflare Pages for the static site. Cost is effectively $0/month at this volume (~300 API calls/day). Equivalent alternative: Vercel cron + Supabase. The Python engine ports to a Worker in ~150 lines of JS; the algorithms are the ones already in `psi_engine.py`, so the port is mechanical, not a redesign.

**"Real time" in practice:** he posts roughly four reviews a week, usually around 6pm ET (`date` fields are consistently 22:00Z), so a 5-minute poll is indistinguishable from live. If you want a true push (a "new score" banner without reload), have the site subscribe to a lightweight SSE endpoint the worker updates; polling the JSON every 60s is simpler and adequate.

**Resilience:** retries with backoff, alert on 3 consecutive failures, alert on schema drift (missing `score`/`date`), alert if the newest record is older than 10 days (he rarely goes quiet that long). Keep the User-Agent honest with a contact address.

### 6.4 Domains, redirect, and SEO plumbing
- **portnoy.pizza** is canonical. Every page sets `<link rel="canonical" href="https://portnoy.pizza/…">`; the wordmark on the site is the domain itself ("portnoy.pizza"), with "The Portnoy Score Index" as the descriptor.
- **onebitescores.com → 301 → portnoy.pizza, path-preserving.** Cheapest correct setup is to put both zones on Cloudflare (you're already connected): add the onebitescores.com zone, create a proxied placeholder A record (`@` → `192.0.2.1`, orange cloud) and a Redirect Rule: *when hostname is in {"onebitescores.com","www.onebitescores.com"} → dynamic redirect to* `concat("https://portnoy.pizza", http.request.uri.path)`, *301, preserve query string*. If the DNS stays at GoDaddy, use GoDaddy Domain Forwarding → `https://portnoy.pizza`, **301 permanent, forwarding only (no masking)** — masking would show onebitescores.com in the address bar and framing the site under that name is exactly what we don't want.
- The redirect is a catcher's mitt for type-ins and social posts, not a ranking play: Google gives essentially no ranking credit for a redirected exact-match domain, and Barstool ranks #1 for "one bite" queries regardless. The traffic for that phrase is won by *pages*, not the domain — see the SEO page plan below.
- **SEO page plan (phase 5):** one URL per review (`portnoy.pizza/score/{venue-slug}` — title "Dave Portnoy's {Venue} pizza score: {score}, top {x}% of {year}"), one URL per score value (`/is/7.8` — "Is 7.8 a good Dave Portnoy pizza score?"), one URL per city and state (`/near/boston` — "Dave Portnoy pizza scores in Boston, ranked"), the leaderboard (`/leaderboard`), and the method page. Body copy may refer to "his One Bite reviews" descriptively (that is what they are called); titles, wordmark, and metadata never use "One Bite". Sitemap regenerated by the poller after every new score; OG share image per review ("8.2 · Liguria · Elite · top 5% of the last 12 months") is what earns links from local news, which is where most of the current search traffic for these queries goes.

---

## 7. Build plan

| Phase | Scope | Status |
|---|---|---|
| 0 | Data discovery, full pull, reconciliation, profiling | **Done** (this document) |
| 1 | Engine + poller (`psi_engine.py`, `psi_poller.py`), verified end-to-end; `config.json` + `overrides.json`; schema-drift guard, `status.json`, changelog | **Done** |
| 1b | Test suite (10 tests: statistics, golden output on frozen archive, new-score / edit / API-down / drift / staleness simulations) | **Done — 10/10** |
| 1c | Deployment scaffold: GitHub Actions poller (5-min + weekly reconcile, KV/R2 publish, fail-loud), Pages Function serving `/data/*`, `wrangler.toml`, security `_headers`, README with the exact commands | **Done — needs your Cloudflare IDs/secrets** |
| 2 | Front end (`index.html` preview with embedded data; `site/index.html` production build that loads `/data/*` live and shows "checked N min ago") | **Done** |
| 3 | Decisions in §9; domain, name, visual identity | You |
| 4 | Port poller to Cloudflare Worker + D1; deploy site to Pages; hook `metrics.json` | ~1–2 days |
| 5 | Method page + share cards ("Is 7.8 good?" OG images) + venue pages (one URL per review for SEO: "Dave Portnoy [Venue] score") | ~2 days |
| 6 | Enrichment: 25/38 venues resolved (see §3.3); 13 remain; verify the 4 medium-confidence names and MrBeast Burger against video; backfill video links | mostly done; ~2 hrs left |
| 7 | Nice-to-haves: state/city breakdowns, style tags (bar pie vs NY slice), embeds, "notify me on a 9" | later |

---

## 8. Legal and risk notes (not legal advice — worth a lawyer's hour before launch)

- The scores, dates, and venue names are **facts**; facts are not copyrightable in the US. What we publish is a database of facts plus our own computed statistics. We do **not** rehost videos, thumbnails, or their text, and every review links back to onebite.app.
- The API is undocumented and Barstool's Terms of Use may restrict automated access. Realistic risk is a block or a takedown request, not damages, and the HTML fallback and low request rate mitigate the first. A courtesy heads-up to Barstool before launch is worth considering; this is free promotion for the app and they may prefer to be told.
- **onebitescores.com:** holding a domain containing Barstool's mark carries some UDRP/cease-and-desist exposure even as a bare redirect. Keep it purely a 301 (no content, no email, no branding, no "One Bite" anywhere on the destination site) so it cannot be read as trading on the mark; if Barstool ever objects, releasing it costs nothing because none of the site's equity lives there. Do not use "One Bite" or Barstool marks in the name, logo, or wordmark. "Portnoy Score Index" uses a public figure's name descriptively (nominative use), which is generally acceptable for commentary/statistics; run it past counsel anyway.
- Publish the method openly. Being transparent about exclusions (protest scores, pre-era) is what earns the "governing body" position; hiding them is what loses it.

---

## 9. Decisions needed from you

1. ~~Name and domain~~ — **Resolved: portnoy.pizza (live), onebitescores.com (301 redirect).** Product name stays "Portnoy Score Index"; the wordmark is the domain.
2. **Window** — trailing 12 months (recommended) vs trailing 200 reviews.
3. **Base year** for the one-line verdict — 2019 (recommended) vs 2016–19 pooled.
4. **Grade labels** — keep the eight in §4.4, or fewer, or Barstool-flavored copy.
5. **Protest scores** — excluded from calibration (recommended); confirm you're comfortable saying so publicly.
6. **Hosting** — Cloudflare (recommended, already connected; also handles both zones and the redirect in one place) vs Vercel/Supabase.

---

## 10. Files delivered (repo layout in `portnoy-pizza-repo.zip`)
- `config.json` — window, base year, grades, exclusions, methodology version (edit here, never in code)
- `overrides.json` — venue enrichment with confidence and evidence
- `tests/test_psi.py` + `tests/fixtures/` — 10 tests, frozen 2,150-row archive, golden metrics
- `.github/workflows/poll.yml`, `tests.yml` — the live pipeline and CI
- `functions/data/[[key]].js`, `wrangler.toml`, `_headers`, `README.md` — Cloudflare Pages deployment
- `site/index.html` — production front end (loads `/data/*`); `index.html` — preview with data embedded

- `SPEC.md` — this document
- `index.html` — interactive prototype, real data embedded: The index · Near me (map) · Leaderboard (tabs / #hash routes)
- `reviews.csv` / `reviews.json` — the full cleaned ledger, 2,150 rows with flags and links
- `metrics.json` — the computed index as of today (what the site consumes)
- `psi_engine.py` — the compute module (normalize → calibrate → yearly/era/rolling stats → quantile map → verdict)
- `psi_poller.py` — the scheduled fetcher/merger with HTML fallback and weekly reconcile
