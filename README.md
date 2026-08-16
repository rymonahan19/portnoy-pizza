# portnoy.pizza — Portnoy Score Index

Independent, continuously updated index of Dave Portnoy's pizza scores. See `SPEC.md` (methodology, data policy, architecture), `LAUNCH.md` (verify-and-launch checklist).

## Layout
- `psi_engine.py` — normalize → calibrate → yearly/era/rolling stats → quantile mapping → verdict. Reads `config.json` (window, base year, grades, exclusions) and `overrides.json` (venue enrichment with confidence + evidence).
- `psi_poller.py` — scheduled fetcher (One Bite API, HTML fallback), schema-drift guard, `status.json` every run, `changelog.jsonl` on edits/removals, `--full` weekly reconcile.
- `tests/` — 10 tests: statistics, golden output on the frozen 2,150-row archive, and offline simulations (new score, score edit, API down → HTML fallback, schema drift blocks writes, staleness).
- `.github/workflows/poll.yml` — every 5 minutes; publishes to Cloudflare KV/R2; commits data. `tests.yml` on push.
- `functions/data/[[key]].js` + `wrangler.toml` + `_headers` — Cloudflare Pages: serves `/data/{metrics,reviews,status}.json` from KV with 60s cache.
- `site/index.html` — the front end (prototype build; embed-free production version loads `/data/*`).

## Cloudflare resources (already created on 2026-08-16)
- KV namespace **psi-data** — id `b90a2a5a7fbf44b5ac1af0b6d0fc00ac` (bound as `PSI_DATA`)
- D1 database **psi** — id `dd27023a-5b94-4a34-bd4c-d08d520336d8`, region ENAM (bound as `PSI_DB`); tables `reviews`, `blobs`, `changelog` created; first workflow run loads all rows via `out/seed.sql`
- R2 bucket **psi-backups** — *not yet*: enable R2 in the dashboard (R2 → Get started; free tier) then `wrangler r2 bucket create psi-backups`. Until then the backup step logs a note and continues.

## One-time setup (≈20 minutes)
```bash
npm i -g wrangler && wrangler login
wrangler r2 bucket create psi-backups           # after enabling R2 in the dashboard
```
GitHub → Settings → Secrets: `CLOUDFLARE_API_TOKEN` (Workers KV + D1 + R2 edit), `CLOUDFLARE_ACCOUNT_ID`, optional `KV_NAMESPACE_ID` (defaults to the id above), optional `PSI_WEBHOOK`.
Seed KV once so the site is never empty:
```bash
python3 psi_poller.py --full && wrangler kv key put --namespace-id $KV metrics.json --path metrics.json --remote \
  && wrangler kv key put --namespace-id $KV reviews.json --path reviews.json --remote \
  && wrangler kv key put --namespace-id $KV status.json --path status.json --remote
```
Cloudflare Pages → connect this repo, build output `site/`, bind KV `PSI_DATA`, custom domains `portnoy.pizza` + `www`.
Redirect (onebitescores.com zone → Rules → Redirect Rules): hostname in {onebitescores.com, www.onebitescores.com} → 301 → `concat("https://portnoy.pizza", http.request.uri.path)`, preserve query. Needs a proxied placeholder A record `@`/`www` → `192.0.2.1`.

## Run locally
```bash
python3 psi_poller.py --full      # pulls the full archive (22 API calls), writes metrics.json / reviews.json / status.json
python3 tests/test_psi.py         # 10/10
```
Not affiliated with Barstool Sports or the One Bite app. Every review links back to onebite.app.
