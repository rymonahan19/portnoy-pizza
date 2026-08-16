// Cloudflare Pages Function: serves /data/metrics.json, /data/reviews.json, /data/status.json
// KV (PSI_DATA) first; falls back to D1 (PSI_DB): blobs table for metrics/status, the reviews table for reviews.json.
const ALLOWED = new Set(["metrics.json", "reviews.json", "status.json"]);
const ORIGIN_OK = [/^https:\/\/(www\.)?portnoy\.pizza$/, /^https:\/\/[a-z0-9-]+\.lovable\.app$/, /^https:\/\/[a-z0-9-]+\.lovableproject\.com$/, /^https:\/\/id-preview--[a-z0-9-]+\.lovable\.app$/, /^http:\/\/localhost(:\d+)?$/];
function corsOrigin(request){ const o = request.headers.get("Origin") || ""; return ORIGIN_OK.some(re => re.test(o)) ? o : "https://portnoy.pizza"; }
export async function onRequestOptions({ request }) {
  return new Response(null, { status: 204, headers: { "Access-Control-Allow-Origin": corsOrigin(request), "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "*", "Access-Control-Max-Age": "86400", "Vary": "Origin" } });
}
export async function onRequestGet({ params, env, request }) {
  const key = (params.key || []).join("/");
  if (!ALLOWED.has(key)) return new Response("Not found", { status: 404 });
  let body = env.PSI_DATA ? await env.PSI_DATA.get(key) : null;
  if (body === null && env.PSI_DB) {
    if (key === "reviews.json") {
      const { results } = await env.PSI_DB.prepare(
        "SELECT id,date,score,venue,city,state,country,lat,lng,protest,pre_era,venue_unresolved,venue_source,in_calibration,url FROM reviews ORDER BY date, id").all();
      if (results && results.length) body = JSON.stringify(results.map(r => ({ ...r, protest: !!r.protest, pre_era: !!r.pre_era, venue_unresolved: !!r.venue_unresolved, in_calibration: !!r.in_calibration })));
    } else {
      const row = await env.PSI_DB.prepare("SELECT value FROM blobs WHERE key = ?").bind(key).first();
      body = row ? row.value : null;
    }
  }
  if (body === null) return new Response(JSON.stringify({ error: "not ready" }), { status: 503, headers: { "Retry-After": "60", "Content-Type": "application/json" } });
  const maxAge = key === "reviews.json" ? 300 : 60;
  return new Response(body, { headers: {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": `public, max-age=${maxAge}, s-maxage=${maxAge}, stale-while-revalidate=300`,
    "Access-Control-Allow-Origin": corsOrigin(request), "Vary": "Origin",
    "X-Content-Type-Options": "nosniff" } });
}
