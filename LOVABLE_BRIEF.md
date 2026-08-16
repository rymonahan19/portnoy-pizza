# Build brief — portnoy.pizza (Portnoy Score Index)
*For Lovable. Attach: `SPEC.md`, `LAUNCH.md`, `metrics.json`, `reviews.json`, `config.json`, `overrides.json`, `preview.html` (working reference of every screen), `psi_engine.py` (reference implementation of every formula), `tests/fixtures/metrics_golden.json`.*

## 1. What this is (read first)
A public, independent website at **https://portnoy.pizza** that takes any pizza score Dave Portnoy gives and answers two things instantly: **how good that score is right now** (percentile within his last 12 months of scores) and **what it would have been in any past year** (era-adjusted equivalent). Think CPI for pizza scores. It updates itself within minutes of each new score. It also shows every scored venue on a map near the visitor, and an all-time leaderboard.

Non-negotiables:
- Every number on the site must reproduce the acceptance values in §8 exactly. The formulas are in §5 and in `psi_engine.py`. Do not "improve" the statistics.
- Not affiliated with Barstool Sports or the One Bite app. Never use "One Bite" or Barstool marks in the site name, logo, page titles, or metadata. Body copy may say "his One Bite reviews" descriptively. Footer disclaimer on every page.
- Every review links back to its original page on onebite.app (`url` field). Never re-host videos or thumbnails.
- No user accounts, no cookies beyond privacy-friendly analytics, geolocation only on tap and never stored.
- Domain: portnoy.pizza (canonical). onebitescores.com 301-redirects to it (handled at DNS; nothing to build).

## 2. Data — two options. **Use Option A unless told otherwise.**

### Option A (preferred): consume the existing pipeline
Three read-only JSON endpoints, refreshed automatically after each new score:
- `https://portnoy.pizza/data/metrics.json` — everything computed (schema in §3). ~60 KB. Cache 60 s.
- `https://portnoy.pizza/data/reviews.json` — every review, one object each (schema in §3). ~1 MB. Cache 5 min. Load lazily; paginate the ledger.
- `https://portnoy.pizza/data/status.json` — `{checked_at, ok, message, source, archive_count, last_score_date, changed, stale}`. Drives the "checked N min ago" stamp and a red banner if `ok=false` or `stale=true`.
The site is a front end over these files. Until the pipeline is on the live domain, use the attached `metrics.json`/`reviews.json` as fixtures.

### Option B (only if asked): also build the pipeline
- Source: `GET https://api.onebite.app/review?userType=DAVE&limit=100&offset={n}` — public, no auth, newest first, max 100 per call (500 returns HTTP 500), 22 calls for the full archive. Send a real User-Agent with a contact address. Fallback: the same records live in `https://onebite.app/reviews/dave?page={n}&minScore=0&maxScore=10` inside `<script id="__NEXT_DATA__">` → `props.pageProps.reviews`.
- Poll every 5 minutes for the newest 25; diff by `id`; on new or changed `score`, recompute everything from scratch (fast; ~2k rows) and publish. Weekly full re-pull to catch edits/removals; log them.
- Guard: if any fetched record lacks `id`, `score`, or `date`, write nothing and alert ("schema drift"). Alert also on 3 consecutive failures and if the newest record is older than 10 days.
- Fields to keep per record: `id, date (YYYY-MM-DD from "date"), score, title→venue, venue.name, venue.city, venue.state (normalize abbreviations to full names), venue.country, venue.placeId, venue.slug, venue.loc.coordinates [lng,lat] (fall back to review.loc), url = https://onebite.app/restaurant/{slug}/review/{id}`.
- Apply `overrides.json` (venue enrichment keyed by id) and `config.json` (all parameters). Flags per row: `protest` (score < 1.0), `pre_era` (date < 2016-01-01), `venue_unresolved` (no venue name), `in_calibration` (= not protest and not pre_era).

## 3. Schemas
`reviews.json` item: `{id, date, score, venue, city, state, country, lat, lng, protest, pre_era, venue_unresolved, venue_source, in_calibration, url}`.
`metrics.json`: `{as_of, methodology_version, params{window_days, base_year, protest_ceiling, era_start, grades[[lowerPct,label]...]}, counts{archive, calibration, protest, pre_era, venue_unresolved, first_date, last_date}, year_stats{YYYY:{n,mean,median,sd,min,max,p10,p25,p75,p90,share_ge_8,share_ge_9,count_ge_9}}, regime{same fields, trailing 365 days}, eras[{name,start,end,...}], rolling[{date,mean,sd}], grid[{score, pct_now, grade, equiv{YYYY:score}}] (0.0–10.0 in 0.1 steps), latest{id,date,score,venue,city,state,url,pct_now,grade,higher_in_window,window_n,equiv{},equiv_base_year}, nines{last{...}, reviews_since, by_year{}}}`.

## 4. Pages
1. **/** The index — (a) Latest verdict card: score, venue, city, grade badge, three facts (percentile in last 12 mo; count of higher scores in the window; equivalent in 2019), one sentence: "An 8.2 right now beats 95% of what he's scored in the past year (155 reviews). At the same percentile, that's an 8.4 in 2019 and an 8.6 in 2017." (b) **Translator** — number input + slider 0–10 (0.1 steps); shows percentile now, grade, count higher/equal in window, and the equivalent score in every year 2016→current (base year outlined). Rail under the slider shows every window score as ticks plus median and p90 markers. Quick buttons 6.5/7.0/7.5/8.0/8.5/9.0/latest. (c) Year-over-year chart: per year min–max hairline, p10–p90 band, p25–p75 band, median dot, mean line; current year marked YTD; n under each year. (d) Last-12-months KPI grid (n, median, mean, sd, p90, max, % ≥ 8.0, count ≥ 9.0, reviews since last 9). (e) 9-drought bar chart by year + sentence. (f) Rolling inflation: mean of last 200 reviews with ±1 sd band, year gridlines. (g) Ledger: newest first, 40 rows then "show 50 more"; columns Review (venue link, city, date, badges), Score, Pct then (percentile within its own calendar year), Today's terms (score at that percentile in the trailing window). Badges: protest / archival / unresolved. (h) Method section (plain-English §5) + disclaimer.
2. **/near** Near me — map with every scored venue as a pin labelled with its score; colours: ≥8.5 brick red fill/white text, 8.0–8.4 black, 7.5–7.9 white with black border, <7.5 grey. Controls: "◎ Me" (browser geolocation on tap; center on user), text search for city or state (state name/abbrev → whole state, no radius; city → radius 5/15/50/150 mi, default 15, auto-widen to nearest 12 if fewer than 8 results), quick chips (Manhattan, Brooklyn, Boston, Philadelphia, Chicago, Miami, New Haven, Nantucket, New Jersey). Cap 400 pins for performance. Card list below: score, "top X%" of its year, venue, city, distance (straight-line miles), year; sort nearest/highest/newest. Tap pin → popup with score, venue, city, date, distance, link.
3. **/leaderboard** — dark header "The highest scores he has ever given." Hero card "THE ONLY 10 · №1 ALL TIME": Monte's Restaurant, Lynn MA, 2015-08-21 (retro-logged). Board from №2 through every score ≥ 8.5 (70 rows today), tiers "The 9.0 club" then "8.5 and up"; ties share a rank, earlier review first; each row: rank, score, venue (link), city · date, "top X% of YYYY". Toggle **Era-adjusted**: rank all non-protest scores by z = (score − that year's calibration mean) ÷ that year's sd (pre-2016 rows use 2016 stats), top 50, show "+2.58σ · 2021 mean 7.22". Retro-logged rows badged "archival". Gold accent is allowed on this page only.
4. **SEO pages (static, generated from data):** `/score/{venue-slug}` one per review — title "Dave Portnoy's {Venue} pizza score: {score} — top {x}% of {year}"; verdict, equivalents, map thumbnail, link to original. `/is/{score}` for 0.0–10.0 — "Is {score} a good Dave Portnoy pizza score?" — percentile now, grade, year equivalents, how many times he's given it. `/near/{city}` and `/near/{state}` — "Dave Portnoy pizza scores in {place}, ranked". `/method`, `/about`, `/privacy`. sitemap.xml regenerated on each new score; canonical tags; OG image per review and per /is/ page ("8.2 · Liguria · Elite · top 5% of the last 12 months"); JSON-LD WebSite.
5. Global: sticky top nav (The index · Near me · Leaderboard), header stamp "● live · checked N min ago · last score {date} · {n} reviews on record", footer disclaimer, 404 page.

## 5. The math (must match `psi_engine.py`)
- **Calibration set** = all reviews minus protest (score < 1.0) minus pre-era (date < 2016-01-01). All statistics use it. Excluded rows still display with badges.
- **Window (current regime)** = calibration scores with date > (as_of − 365 days), where as_of = today (UTC).
- **Percentile now** of score s = 100 × (count of window scores < s + 0.5 × count equal) / n. Above the window max → show ">100th, higher than every score in the past 12 months".
- **Quantile** q of a sorted list (type 7 / numpy linear): pos = q·(n−1); interpolate between floor and ceil.
- **Equivalent in year Y** = quantile(Y's calibration scores, pct_now/100), rounded to 0.1. Base year 2019 for the one-line verdict.
- **Grades** by percentile: ≥97 Rarefied air · ≥90 Elite · ≥75 Great · ≥55 Above average · ≥40 Average · ≥25 Below average · ≥10 Poor · else Bad.
- **Year table**: n, mean, median, population sd, min, max, p10, p25, p75, p90, % ≥ 8.0, % ≥ 9.0, count ≥ 9.0.
- **Rolling**: mean & sd of the last 200 calibration reviews, stepped every 5 reviews.
- **Eras**: 2016–2019 "Wide scale", 2020–2023 "Compression", 2024–present "Narrow band".
- **Era-adjusted rank**: z = (score − year mean) / year sd; pre-2016 uses 2016.
- All parameters live in `config.json`; methodology_version bumps on any change.

## 6. Design (see `preview.html` — it is the reference; match its feel, don't invent a new one)
Palette: paper `#EEEFEA`, panel `#FFFFFF`, ink `#17181A`, ash `#6B7075`, line `#D6D9D1`, brick `#A6231A`, brick-soft `#F3DDD9`, band `#CBD0C4`, band-strong `#8E968A`, gold `#B08D3A` (leaderboard only), gold-soft `#F1E7CF`. Type: display Barlow Condensed 700/800 (big numbers, headings), body IBM Plex Sans, figures IBM Plex Mono. Wordmark is the domain: "portnoy.pizza" with a brick-red dot; descriptor "The Portnoy Score Index · what a Dave Portnoy pizza score is really worth". Mobile-first, max width 720 px, one column, no decorative gradients, no emoji, minimal motion (respect prefers-reduced-motion). Big condensed numerals are the personality; keep everything else quiet.

## 7. Ops (Option A: mostly done; Option B: build)
- Analytics: Cloudflare Web Analytics or Plausible. No cookie banner needed.
- Performance: Lighthouse ≥ 90 mobile on /, /near, /leaderboard; do not embed the 1 MB reviews file in the HTML.
- Accessibility: keyboard focus, AA contrast, alt text, reduced motion.
- Security: HTTPS, CSP, no secrets client-side.
- Status handling: if `status.ok=false` or `stale=true`, show a small red banner "Data feed paused — last checked …" (never hide the site).

## 8. Acceptance tests — the site must show exactly these with the attached data (as of 2026-08-15)
- Counts: 2,150 reviews on record; 2,121 in calibration; 15 protest; 14 pre-era; span 2013-03-13 → 2026-08-13.
- Window: n=155, mean 7.395 (display 7.4), median 7.5, sd 0.69, p90 8.1, max 8.5, 15.5% ≥ 8.0, zero 9s.
- Latest verdict: 8.2, Liguria Pizzeria (Philadelphia), 2026-08-13 → 95th percentile (95.2), grade Elite, 2 higher scores in window, ≈ 8.4 in 2019 and 8.6 in 2017.
- Translator: 7.0 → 20th pct, Poor, 5.2 in 2017, 6.1 in 2019, 6.7 in 2023 · 7.8 → 72nd, Above average · 8.0 → 84th/85th, Great, 8.1 in 2017 · 8.5 → 99th, Rarefied air, 9.3 in 2017 / 9.1 in 2019 · 9.0 → above every score in the window.
- Year means: 2016 6.55 · 2017 6.48 · 2019 6.78 · 2020 7.22 · 2024 7.46 · 2026 YTD 7.59; p90 = 8.1 every year 2018–2025; p10 3.9 (2016) → 6.8 (2026).
- Nines: 22 scores ≥ 9.0 all-time; last = Ceres 9.2 on 2025-05-13; 205 reviews since.
- Leaderboard (raw): №1 Monte's Restaurant 10 (2015-08-21, archival); №2 tie 9.4 — Frank Pepe (Newton MA, 2015-12-22, archival), Di Fara (Brooklyn, 2017-02-28), DeLucia's Brick Oven (Raritan NJ, 2022-01-06); then 9.3s — Lazzara's (2016-10-14), John's of Bleecker (2016-11-09), Unidentified venue (2017-01-16, record incomplete), Oath Nantucket (2017-08-17), Lucali (2018-10-19), Luigi's Brooklyn (2021-09-21). Board runs through all 70 scores ≥ 8.5.
- Leaderboard (era-adjusted): #1 Luigi's 9.3 (2021) +2.58σ · #2 Ceres 9.2 (2025) +2.34σ · #3 Calabria 8.9 (2021) +2.08σ · #4 The Little Rendezvous 9.1 (2023) +2.05σ · #5 DeLucia's 9.4 (2022) +2.04σ.
- Near me: "New Jersey" → 233 pins, high 9.4 DeLucia's; "Philadelphia" (15 mi) → 56 results, high 9.1 Angelo's; "Boston" works; "Timbuktu" → "no reviews match".
- Ledger first row: Liguria Pizzeria · 8.2 · 93rd (pct within 2026) · 8.2 (today's terms).
- Wawa (Sea Isle City, NJ, 2021-09-07, 7.6) appears by name (from `overrides.json`); 13 rows show "Unidentified venue".

## 9. Definition of done
All §8 values render; three routes + SEO pages live on portnoy.pizza; status stamp updates; Lighthouse ≥ 90; disclaimer everywhere; no "One Bite" in titles/branding; every review links to onebite.app; a change to `config.json` (e.g. window 365→300) changes every dependent number consistently.
