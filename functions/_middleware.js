// Cloudflare Pages middleware: per-page SEO for the single-page site.
// Each view has a real path. For those paths we serve site/index.html with the
// <title>, meta description, canonical and Open Graph tags rewritten at the edge,
// so every view is a distinct, indexable URL while the HTML stays one file.
// Everything else (/, /data/*, static assets) passes straight through.

const ORIGIN = "https://portnoy.pizza";

const ROUTES = {
  "/leaderboard": {
    title: "Dave Portnoy's highest pizza scores ever — All-time leaderboard | portnoy.pizza",
    description: "Every Dave Portnoy One Bite pizza score ranked №1 to the lowest. The only 10 (Monte's), the 9.0 club, and an era-adjusted board that corrects for score inflation.",
  },
  "/the-index": {
    title: "The Portnoy Score Index — what a Dave Portnoy pizza score is really worth | portnoy.pizza",
    description: "Is an 8.3 from Dave Portnoy good? Translate any One Bite score into its percentile over the last 12 months and its equivalent in any past year. Score inflation, year over year, and the method.",
  },
  "/search": {
    title: "Dave Portnoy pizza scores near you — search by city, state or ZIP | portnoy.pizza",
    description: "Find every pizzeria Dave Portnoy has reviewed near you. Search any city, state or ZIP for One Bite scores on a map, sorted by distance, score or date.",
  },
  "/grade-scale": {
    title: "Dave Portnoy pizza score grade scale — Elite, Great, Solid, Skip | portnoy.pizza",
    description: "What counts as a good Dave Portnoy pizza score today? The grade scale maps One Bite scores to percentile bands of his last 12 months of reviews, updated as he reviews.",
  },
};

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);
  let path = url.pathname;

  // normalize trailing slash: /leaderboard/ -> /leaderboard
  if (path.length > 1 && path.endsWith("/")) {
    const clean = path.replace(/\/+$/, "");
    if (ROUTES[clean]) return Response.redirect(url.origin + clean + url.search, 301);
  }

  const route = ROUTES[path];
  if (!route || (request.method !== "GET" && request.method !== "HEAD")) return next();

  // Serve the single index.html for this route, with the SEO tags swapped in.
  const asset = await env.ASSETS.fetch(new URL("/", request.url));
  const canonical = ORIGIN + path;

  return new HTMLRewriter()
    .on("title", { element(e) { e.setInnerContent(route.title); } })
    .on('meta[name="description"]', { element(e) { e.setAttribute("content", route.description); } })
    .on('link[rel="canonical"]', { element(e) { e.setAttribute("href", canonical); } })
    .on('meta[property="og:title"]', { element(e) { e.setAttribute("content", route.title); } })
    .on('meta[property="og:description"]', { element(e) { e.setAttribute("content", route.description); } })
    .on('meta[property="og:url"]', { element(e) { e.setAttribute("content", canonical); } })
    .transform(new Response(asset.body, asset));
}
