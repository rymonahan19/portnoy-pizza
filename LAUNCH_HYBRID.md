# LAUNCH — Hybrid runbook for portnoy.pizza
*Pipeline + data endpoint: GitHub Actions → Cloudflare KV/D1 → `https://data.portnoy.pizza/data/*.json` (built, tested).*
*Front end: Lovable, published to `https://portnoy.pizza`, reading those three JSON files.*
*Order matters: data endpoint first, then Lovable builds against live URLs, then domain.*

Already done for you: KV namespace `psi-data` (`b90a2a5a7fbf44b5ac1af0b6d0fc00ac`), D1 database `psi` (`dd27023a-5b94-4a34-bd4c-d08d520336d8`) with tables, `wrangler.toml` wired, workflow written, function written, tests 10/10, repo zip ready.

Time: about 2 hours of clicking, spread over a day for DNS and SSL to settle. Do the steps in order; each ends with a check.

---

## Part A — Pipeline + data endpoint (Cloudflare + GitHub) · ~45 min

### A1. Create the GitHub repo
1. github.com → New repository → name `portnoy-pizza` → **Public** (public repos get unlimited Actions minutes; the data is public anyway) → Create.
2. Unzip `portnoy-pizza-repo.zip` and push its contents to `main` (GitHub Desktop: "Add local repository" → publish; or `git init && git add . && git commit -m "init" && git branch -M main && git remote add origin … && git push -u origin main`).
   - **Check:** Actions tab → "PSI tests" runs and turns green (10 tests).
   - Note: the `.github` folder is hidden on macOS Finder — make sure it was included (Actions tab shows workflows if it was).

### A2. Cloudflare API token + account id
1. Cloudflare dashboard → My Profile → API Tokens → Create Token → "Create Custom Token":
   Permissions: **Account · Workers KV Storage · Edit**, **Account · D1 · Edit**, **Account · Workers R2 Storage · Edit** (R2 optional). Account resources: your account. Create → copy the token once.
2. Account ID: dashboard → Workers & Pages → right sidebar "Account ID" → copy.
3. GitHub repo → Settings → Secrets and variables → Actions → New repository secret:
   `CLOUDFLARE_API_TOKEN` = the token · `CLOUDFLARE_ACCOUNT_ID` = the id · (optional) `PSI_WEBHOOK` = a Slack/Discord webhook URL if you want a ping on each new score.
   (`KV_NAMESPACE_ID` is optional; it defaults to `b90a2a5a7fbf44b5ac1af0b6d0fc00ac`.)

### A3. First run — loads KV and D1 with all 2,150 reviews
1. GitHub → Actions → "PSI poll" → Run workflow → set **full = true** → Run.
2. Open the run: every step green. The D1 step prints ~46 statements executed; the R2 step prints a note if R2 isn't enabled yet (fine).
   - **Check:** rerun with full=false a minute later → log ends "no change".

### A4. Move DNS for both domains to Cloudflare (needed for the data subdomain, the redirect, and Lovable's records)
1. Cloudflare → Add a domain → `portnoy.pizza` → Free plan → it scans records → Continue → it shows two nameservers.
2. GoDaddy → My Products → portnoy.pizza → DNS → Nameservers → Change → "I'll use my own" → paste the two Cloudflare nameservers → Save.
3. Repeat for `onebitescores.com`.
   - **Check:** Cloudflare shows both zones "Active" (5 min to a few hours). Don't proceed with B/D until they're Active.

### A5. Deploy the data endpoint (Cloudflare Pages)
1. Cloudflare → Workers & Pages → Create → **Pages** → Connect to Git → pick `portnoy-pizza` repo.
2. Project name **`portnoy-pizza`** (must match `wrangler.toml`), production branch `main`, Framework preset **None**, Build command *(leave empty)*, Build output directory **`site`** → Save and Deploy.
3. After the first deploy: Settings → Bindings (or Functions) → confirm **KV `PSI_DATA` → psi-data** and **D1 `PSI_DB` → psi** are present (wrangler.toml supplies them; if the UI shows none, add them by hand with those exact variable names). Redeploy once if you added them by hand.
4. Custom domains → Set up a custom domain → **`data.portnoy.pizza`** → Cloudflare creates the CNAME itself → wait for "Active".
   - **Check (the moment of truth):**
     `curl -s https://data.portnoy.pizza/data/status.json` → JSON with `"ok": true`, `"archive_count": 2150`
     `curl -s https://data.portnoy.pizza/data/metrics.json | head -c 200` → starts with `{"generated_at"`
     Open `https://data.portnoy.pizza/` in your phone → the full prototype renders live from `/data/*` (this page is `noindex`; it's your fallback UI and your smoke test).
   - Add `https://data.portnoy.pizza/data/status.json` to an uptime monitor (Cloudflare Health Checks or UptimeRobot, alert on non-200 or on the JSON containing `"ok": false`).

### A6. onebitescores.com → 301 → portnoy.pizza (path-preserving)
1. Cloudflare → onebitescores.com → DNS → Add record: **A** `@` → `192.0.2.1` **Proxied (orange)**; **A** `www` → `192.0.2.1` Proxied.
2. Rules → Redirect Rules → Create → name "to portnoy.pizza" → When incoming requests match: *Custom filter*: field **Hostname**, operator *is in*, value `onebitescores.com` `www.onebitescores.com` → Then: **Dynamic**, expression `concat("https://portnoy.pizza", http.request.uri.path)`, status **301**, "Preserve query string" ✔ → Deploy.
   - **Check:** `curl -sI http://onebitescores.com/leaderboard | grep -i location` → `location: https://portnoy.pizza/leaderboard` (works even before the apex is live).
3. Optional (recommended): R2 → "Get started" (one-time enable, free tier, card on file) → then `wrangler r2 bucket create psi-backups` (or Cloudflare UI → R2 → Create bucket) → the workflow's backup step starts working on the next run.

**Part A done when:** status/metrics/reviews load from `data.portnoy.pizza`, the workflow runs green every 5 minutes, and the redirect answers 301.

---

## Part B — Front end on Lovable · ~1–2 hrs of prompting

### B1. Project
1. lovable.dev → New project. Paste `LOVABLE_BRIEF.md` in full as the first message, prefixed with one line: **"Build Option A. Data lives at https://data.portnoy.pizza/data/metrics.json, /data/reviews.json, /data/status.json (CORS is enabled). Attached preview.html is the visual reference for every screen. Start with the three routes: /, /near, /leaderboard."** Attach `preview.html`, `metrics.json`, `reviews.json` (fixtures) and `SPEC.md`.
2. Let it scaffold, then iterate **one page per prompt** in this order — it keeps Lovable focused:
   - "Build `/` exactly as §4.1 of the brief; wire the translator to the grid and by-year data; match the acceptance values in §8 for 8.2, 7.0, 8.0, 8.5."
   - "Build `/leaderboard` per §4.3 including the Era-adjusted toggle; gold only here."
   - "Build `/near` per §4.2 with Leaflet or Mapbox, geolocation on tap, city/state search, radius rules, card list."
   - "Add the sticky nav, header status stamp from status.json (checked N min ago), footer disclaimer, /method, /about, /privacy, 404."
   - "Add a runtime self-check page at /qa that asserts every value in brief §8 against the live data and shows PASS/FAIL." (This is your regression guard against future prompts.)
3. Verify in Lovable's preview: the numbers in §8 (95th percentile / Elite / 2 higher / 8.4 in 2019 / 205 reviews since the last 9 / Luigi's +2.58σ at the top of era-adjusted / New Jersey → 233 pins). If anything is off, paste the exact expected value back — do not accept "close".
   - Note: the preview reads live data, so as soon as he posts a new score the "latest" values will legitimately move; §8 is pinned to 2026-08-15 — compare against `/qa` logic, not memory.

### B2. Publish + custom domain in Lovable
1. Lovable → Publish (top right) → publish to the `*.lovable.app` URL first. Open it on your phone; check all three routes and that the map tiles and "◎ Me" prompt work outside the editor.
2. Lovable → Project Settings → **Domains** → Connect domain → `portnoy.pizza`. It shows the DNS records to add (typically an **A** record for `@` and one for `www` pointing at Lovable's IP, sometimes a TXT). **Use exactly what the dialog shows.** (Custom domains require a paid Lovable plan.)
3. Cloudflare → portnoy.pizza → DNS → add those records **DNS only (grey cloud, not proxied)** — Lovable issues its own SSL and needs to see the domain directly. If Cloudflare auto-created any old A/CNAME for `@` or `www` during the import, delete them first. Keep the `data` CNAME (Pages) as is.
4. Back in Lovable → Verify. SSL is usually issued within minutes; allow up to a few hours.
   - **Check:** `https://portnoy.pizza` and `https://www.portnoy.pizza` load the Lovable app over HTTPS; `https://portnoy.pizza/leaderboard` deep-links directly.
   - `curl -sI https://portnoy.pizza | head -1` → `HTTP/2 200`.

### B3. Search plumbing (10 min)
1. Lovable → SEO settings (or ask it): page titles/descriptions per route from the brief; canonical `https://portnoy.pizza/…`; robots allowed; sitemap listing `/`, `/near`, `/leaderboard`, `/method`, `/about`.
2. Google Search Console → Add property (Domain) → verify with the TXT record it gives you (add in Cloudflare DNS) → Sitemaps → submit `https://portnoy.pizza/sitemap.xml`. Same on Bing Webmaster (import from GSC).
3. Analytics: ask Lovable to add Cloudflare Web Analytics (a `<script>` snippet from Cloudflare → Web Analytics → Add site → copy) or Plausible. No cookie banner needed for either.

**Part B done when:** portnoy.pizza serves the Lovable app over HTTPS, `/qa` passes, and every review link opens onebite.app.

---

## Part C — Pre-launch checks (30 min) · all must pass
- [ ] Phone on cellular: `https://portnoy.pizza` (Lovable), `https://data.portnoy.pizza/data/status.json` (JSON), `http://onebitescores.com/x` → lands on `https://portnoy.pizza/x`.
- [ ] Header stamp shows "checked N min ago" with N < 10 at any time.
- [ ] `/qa` (or a manual read) matches: latest score/venue equals onebite.app's newest; leaderboard №1 Monte's 10; era-adjusted #1 Luigi's +2.58σ.
- [ ] Every visible sentence read once as a stranger: "One Bite" only descriptively in body copy; disclaimer in footer and About; no Barstool marks.
- [ ] Legal hour done (nominative use of "Portnoy", redirect posture, ToS posture, disclaimer text).
- [ ] Uptime monitor and workflow failure emails go to you (GitHub emails on failed runs by default — make sure notifications are on).

## Part D — Launch gate, then announce
1. **Wait for the first real new score to be detected and published with no human touch.** He posts ~4/week around 6pm ET. Watch: workflow log shows `NEW  <date>  <score>  <venue> -> pXX Grade`, then within 60 s the site's verdict card updates. That event is "live". Do not announce before it.
2. Announce with the era-adjusted leaderboard ("Luigi's 9.3 in 2021 is the most dominant score he has ever given") and the "Is X a good score?" framing when the next review drops. Optional courtesy note to Barstool/One Bite.

## Part E — Ongoing (5 min/week)
- Monday: glance at the weekly full-reconcile run (edits/removals logged in `out/changelog.jsonl`).
- Any Lovable change: re-run `/qa` before publishing. If a §8 value breaks, revert or paste the expected value back.
- If `status.ok=false` email arrives: open the workflow log — schema drift means api.onebite.app changed shape; the HTML fallback covers most cases; otherwise it's an hour of `psi_poller.py` surgery.
- Later: SEO pages (`/score/{slug}`, `/is/{score}`, `/near/{city}`) — ask Lovable to prerender them, or generate them statically from the pipeline; enable R2 backups; resolve the 13 unnamed venues.

## Rollback (if Lovable is ever down or broken)
Cloudflare → portnoy.pizza → DNS: point `@`/`www` at the Pages project instead (Pages → Custom domains → add `portnoy.pizza`), and remove `noindex` from `site/index.html`. The prototype UI serves the identical live data. Ten minutes.
