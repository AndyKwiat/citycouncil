// Static files (every page, plus _redirects for /) are served without running this. It only runs for
// www and /api/search, which forwards searches to the private API with the site's secret key.
const PARAMS = ['q', 'kinds', 'cities', 'from', 'to', 'limit'];
const CACHE_SECONDS = 3600;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.hostname.startsWith('www.')) {
      url.hostname = url.hostname.slice(4);
      return Response.redirect(url.toString(), 301);
    }
    if (url.pathname === '/api/search') return search(request, env, ctx, url);
    return env.ASSETS.fetch(request);
  },
};

async function search(request, env, ctx, url) {
  if (request.method !== 'GET') return json({ error: 'Use GET.' }, 405);
  if (!env.APP_KEY) return json({ error: 'Search is not set up yet.' }, 503);
  // Only the parameters the API knows, in a fixed order, so identical searches share one cache entry.
  const upstream = new URL('/search', env.API_ORIGIN);
  for (const name of PARAMS) {
    const value = url.searchParams.get(name);
    if (value) upstream.searchParams.set(name, value.slice(0, 300));
  }
  const cacheKey = new Request('https://cache.cityhallvotes.ca' + upstream.pathname + upstream.search);
  const cache = caches.default;
  const hit = await cache.match(cacheKey);
  if (hit) {
    console.log('search (cached)', url.searchParams.get('q'));
    return hit;
  }
  // Repeats are served from the cache above for free; only new searches count against the limit.
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  if (env.SEARCH_LIMIT) {
    const { success } = await env.SEARCH_LIMIT.limit({ key: ip });
    if (!success) return json({ error: 'Too many searches in a short time. Wait a minute and try again.' }, 429);
  }
  console.log('search', url.searchParams.get('q'));
  let answer;
  try {
    answer = await fetch(upstream, {
      headers: { 'X-App-Key': env.APP_KEY, 'X-Client-IP': ip },
    });
  } catch (err) {
    return json({ error: "Couldn't reach the search service. Try again shortly." }, 502);
  }
  const body = await answer.text();
  const response = new Response(body, {
    status: answer.status,
    headers: { 'Content-Type': 'application/json; charset=utf-8',
               'Cache-Control': answer.ok ? `public, max-age=${CACHE_SECONDS}` : 'no-store' },
  });
  if (answer.ok) ctx.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
}

function json(body, status) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
}
