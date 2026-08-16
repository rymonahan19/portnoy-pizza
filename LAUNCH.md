# portnoy.pizza — Verify & Launch Checklist

Owner key: **You** · **Dev** (whoever builds; can be Claude Code) · **Legal** · **Claude** (I can do it from here on request)
Format: `[ ] task — done when: <observable result>`

---

## Phase 0 — Confirm what exists is right (today, ~2 hours)

### 0.1 Open the prototype outside the Claude preview
- [ ] **You** — Open `index.html` in Safari on your iPhone *and* Chrome on a desktop — done when: map tiles render on the Near-me tab, "◎ Me" prompts for location and drops the red dot, translator drags, leaderboard toggles, ledger links open onebite.app review pages.
- [ ] **You** — Tap through 5 leaderboard rows and 5 Near-me cards — done when: every link lands on the correct review at onebite.app.

### 0.2 Prove the data is complete and accurate (independent of me)
- [ ] **You** — On onebite.app/reviews/dave, note the newest 3 reviews (score, venue, date) — done when: they match rows 1–3 of `reviews.csv` sorted by date desc.
- [ ] **You** — Pick 10 random rows in `reviews.csv`, open the `url` column — done when: 10/10 match score and venue on onebite.app.
- [ ] **You** — Check the top 22 (score ≥ 9.0) the same way — done when: 22/22 match (one is "unidentified venue", see 0.4).
- [ ] **Dev** — Run `python3 psi_poller.py --full` — done when: output says `full reconcile: 2150 records | +0 new, 0 score edits, 0 removed` (or +N new if he has posted since 13 Aug, each visible on onebite.app).

### 0.3 Hand-check the index math in Excel (from reviews.csv, `in_calibration = TRUE` rows only)
- [ ] **You** — *Percentile now:* filter date > (today − 365 days). Count rows with score > 8.2 → should be **2** (Fermento 8.5, Bucky's 8.5); count = 8.2 → **4**; total rows → **155**. Percentile = (155 − 2 − 4×0.5) / 155 = **95.2%**. Matches the verdict card.
- [ ] **You** — *Year table:* AVERAGEIFS / MEDIAN / STDEV.P by year → 2017 mean **6.48**, 2019 mean **6.78**, 2024 mean **7.46**, 2026 YTD mean **7.59**. Matches SPEC §1.
- [ ] **You** — *Era-adjusted:* Luigi's 9.3 (2021): (9.3 − 7.22) / 0.81 = **+2.57σ**; DeLucia's 9.4 (2022): (9.4 − 7.15) / 1.10 = **+2.05σ**. Luigi's ranks higher. Matches the leaderboard toggle.

### 0.4 Close the data loose ends
- [x] **Claude** — 25 of 38 venue-less records resolved into `overrides.json` (21 high via Barstool story API + geocode, 4 medium via POI at coordinates); engine applies them. **13 remain** (10 location-only, 3 with no coordinates incl. the 9.3 of 2017-01-16) — residue documented in SPEC §3.3. Remaining path: One Bite YouTube uploads for those weeks.
- [ ] **You** — Eyeball the 4 medium-confidence names against the videos (Luigi's 8th Ave 2017-04-11, Lions & Tigers & Squares 2018-05-11, Owl's Nest 2020-11-18, Siena Pizza & Cannoli 2021-05-04) — done when: confirmed or corrected in `overrides.json`.
- [ ] **You** — Watch the MrBeast Burger review (2022-12-29, 7.1) — done when: confirmed pizza (keep) or burger (flag `non_pizza`, exclude from calibration, keep in archive).
- [ ] **You** — Sign off the §9 decisions: trailing **12 months**, base year **2019**, the 8 grade labels, protest scores **excluded** — done when: you've read `config.json` (already baked in) and left it or edited it.

### 0.5 Legal hour (before anything is public)
- [ ] **Legal** — One hour on: (a) nominative use of "Portnoy" in the name and domain, (b) onebitescores.com as a bare 301 (no content, no email, no branding), (c) posture on Barstool ToS / undocumented API with HTML fallback and low request rate, (d) disclaimer wording — done when: you have written OK-to-launch notes and the disclaimer text.
- [ ] **You** — Decide whether to send Barstool a courtesy heads-up before launch (recommended: short, friendly, "we link every review back to onebite.app").

---

## Phase 1 — Infrastructure on Cloudflare (½ day)

- [ ] **You** — Add both zones to Cloudflare; move nameservers for portnoy.pizza and onebitescores.com — done when: both zones show "Active".
- [ ] **Dev** — SSL/TLS: Full (strict); Always Use HTTPS on; HSTS *after* everything else works.
- [ ] **Dev** — **Redirect:** on onebitescores.com create a proxied placeholder A record `@ → 192.0.2.1` and `www → 192.0.2.1`; Rules → Redirect Rules → *hostname in {"onebitescores.com","www.onebitescores.com"}* → dynamic `concat("https://portnoy.pizza", http.request.uri.path)`, **301**, preserve query — done when:
  `curl -sI http://onebitescores.com/leaderboard | grep -i location` → `location: https://portnoy.pizza/leaderboard`
  (Also test `https://www.onebitescores.com/?x=1` → `https://portnoy.pizza/?x=1`.)
- [x] **Claude** — KV namespace `psi-data` created (`b90a2a5a7fbf44b5ac1af0b6d0fc00ac`) and D1 database `psi` created (`dd27023a-5b94-4a34-bd4c-d08d520336d8`, ENAM) with tables `reviews`, `blobs`, `changelog` — ids already in `wrangler.toml` and the workflow.
- [ ] **You** — Enable R2 in the Cloudflare dashboard (R2 → Get started; free tier, card on file), then `wrangler r2 bucket create psi-backups` — done when: the bucket exists. Until then the workflow's backup step just logs a note.
- [ ] **Dev** — Email: Cloudflare Email Routing `hello@portnoy.pizza` → your inbox — done when: a test email arrives.
- [ ] **Dev** — Cloudflare Web Analytics (or Plausible) — cookie-free, no banner needed.

---

## Phase 2 — The live pipeline (choose one path; A launches fastest)

**Path A (recommended for launch, ~2 hours):** keep the Python exactly as delivered.
- [ ] **You/Dev** — Create the GitHub repo from `portnoy-pizza-repo.zip` (everything is in it, including `ledger_raw.json` with the initial 2,150) — done when: `tests.yml` is green on the first push.
- [x] GitHub Actions workflow written (`.github/workflows/poll.yml`): `*/5` poll, weekly `--full`, publish to KV/R2, commit, fail-loud. Needs secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `KV_NAMESPACE_ID`, optional `PSI_WEBHOOK`.
- [ ] **Dev** — Add the secrets, run `workflow_dispatch` once — done when: KV holds `metrics.json`, `reviews.json`, `status.json`.
- [x] Pages Function `functions/data/[[key]].js` serves `/data/*` from KV with 60 s cache; `wrangler.toml` binds `PSI_DATA`; `_headers` sets security headers.
- [ ] **Dev** — Cloudflare Pages project connected to the repo, output dir `site/`, KV binding `PSI_DATA` — done when: `https://portnoy.pizza/data/status.json` returns JSON.

**Path B (later, true 5-minute edge polling):** port the ~250 lines of engine+poller to a Worker with a Cron Trigger; identical algorithms; keep Path A's golden test to prove parity.

**Tests that must pass before either path is "on":** — all written in `tests/test_psi.py`, **10/10 passing** on the frozen archive:
- [x] Golden test (frozen 2,150-row snapshot reproduces `metrics_golden.json`; also asserts the Excel hand-check values).
- [x] New-score simulation (verdict `Elite`, `status.changed = 1`).
- [x] Score-edit simulation (`1 edits`, `changelog.jsonl` written).
- [x] API-down → HTML fallback (`status.source = html_fallback`).
- [x] Schema drift → exit code 2, `status.ok = false`, nothing written.
- [x] Staleness signal (`status.stale` when no new score in 10+ days).
- [ ] **Dev** — Alerts delivered: the workflow's last step fails on `ok=false` or `stale=true`, so GitHub emails you; forward to Slack if you want — done when: you trigger `workflow_dispatch` once and see the run go green, then break the API URL in a branch and see it go red.

---

## Phase 3 — Production site (2–3 days)

- [ ] **Dev** — Turn the prototype into routes: `/` (index), `/near`, `/leaderboard`, `/method`, `/about`, `/privacy`; static build (Astro/Eleventy/Next static) reading `metrics.json` + `reviews.json`; do **not** embed the 450 KB blob in every page — load reviews async, paginate the ledger.
- [ ] **Dev** — SEO pages generated from data: `/score/{venue-slug}` (one per review, links back to onebite.app), `/is/{score}` (0.0–10.0), `/near/{city}` and `/near/{state}`; sitemap.xml regenerated on every new score; canonical on every page; robots.txt; custom 404.
- [ ] **Dev** — Map in production: Google Maps JS using the stored Place IDs (hours, photos, directions) or MapTiler; key restricted to portnoy.pizza; attribution shown; geolocation only on tap, never stored.
- [ ] **Dev** — OG share image per review and per `/is/` page (Worker + Satori/resvg, or pre-rendered at build) — done when: the X and iMessage card previews show "8.2 · Liguria · Elite · top 5% of the last 12 months".
- [ ] **Dev** — Header stamp reads `status.json` ("checked 3 min ago · last new score 13 Aug").
- [ ] **Dev** — Pages: About (independence + disclaimer + method summary + changelog), Privacy (no location storage; analytics vendor), Contact.
- [ ] **Dev** — Accessibility & performance: keyboard focus visible, contrast AA, reduced-motion respected, Lighthouse ≥ 90 mobile on `/`, `/near`, `/leaderboard`.
- [ ] **Dev** — Security headers (CSP, HSTS, X-Content-Type-Options); no secrets in client; rate-limit `/data/*` at Cloudflare.

---

## Phase 4 — Pre-launch QA (1 day)

- [ ] **You** — Cross-device pass: iPhone Safari, Android Chrome, desktop Chrome/Safari/Firefox — done when: no layout breaks, map works, location prompt works.
- [ ] **You** — Numbers parity: verdict, YoY table, regime card, leaderboard top 10 on the live site equal `metrics.json` (spot-check 10 values).
- [ ] **Dev** — Redirect re-verified from the public internet (phone on cellular): onebitescores.com → portnoy.pizza, http → https, www → apex.
- [ ] **Dev** — Backups: confirm an R2 snapshot exists and a restore rebuilds the site.
- [ ] **Dev** — Uptime monitor on `https://portnoy.pizza/status.json` (Cloudflare Health Check or UptimeRobot) — done when: a test outage pages you.
- [ ] **Dev** — Google Search Console + Bing Webmaster: verify domain, submit sitemap — done when: sitemap "Success" status.
- [ ] **You** — Read every visible sentence once as a stranger — done when: nothing implies affiliation with Barstool, "One Bite" appears only descriptively in body copy, disclaimer present in footer and About.

---

## Phase 5 — Launch

- [ ] **Soft launch (48h):** DNS live, share with ~10 people, watch logs — done when: **the first real new score is detected live** (he posts ~4/week, ~6pm ET) and the verdict updates within 5 minutes with no manual touch. Do not announce before this happens.
- [ ] **Announce:** X/Instagram/TikTok/Reddit (r/barstoolsports, r/Pizza) — lead with the era-adjusted leaderboard ("Luigi's 9.3 in 2021 is the most dominant score he has ever given") and post the "Is X a good score?" card the moment the next review drops.
- [ ] **Local press hook:** every future review → auto-generated share card + one-line verdict; that is what local outlets (the ones ranking today) will link to.
- [ ] Optional: courtesy note to Barstool/One Bite.

---

## Phase 6 — First two weeks after launch

- [ ] Weekly: `--full` reconcile log reviewed; HTML fallback tested once by hand.
- [ ] Watch Search Console for which query family lands first ("dave portnoy pizza score" vs "one bite score" vs venue names) and add pages accordingly.
- [ ] Enrichment backlog: YouTube link per review, Google Place details, remaining unresolved venues.
- [ ] Methodology changelog: any change to window/base year/grades/exclusions = version bump + dated note on /method.
- [ ] Nice-to-haves queue: "notify me on a 9" email list, embeds for pizzerias ("PSI: 8.2 · Elite"), city pages, style tags (bar pie vs NY slice).

---

## Definition of "live"
1. `curl -sI http://onebitescores.com/` → 301 to portnoy.pizza.
2. `https://portnoy.pizza/status.json` shows a poll in the last 10 minutes.
3. A real new score has been detected and published without human intervention.
4. Every visible number matches `metrics.json`; every review links back to onebite.app.
5. Legal notes filed; disclaimer visible; privacy page live.
