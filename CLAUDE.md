# Personal Website — Cloudflare Workers + Static Assets

Minimal personal site deployed to Cloudflare Workers. The stack is
intentionally simple: a GitHub repo is the source of truth, Cloudflare
Workers serves the site, and every push to `main` deploys automatically.
No build step beyond `npm install`, no CI pipeline, no hosting fees.

## Goals

A personal site should embody these principles. Use them to guide decisions
about what to add, change, or remove.

- **Simple** — the deployment pipeline should allow fast iteration without
  gatekeeping: push to `main` and it's live, no review or approval step
  required. No unnecessary dependencies, feature bloat, or heavyweight
  libraries. Every addition should earn its place.

- **Fast** — pages should load instantly. Serve static assets from the edge,
  minimize JavaScript, inline critical CSS, and avoid render-blocking
  resources. The site should feel immediate on any connection. Prune dead
  code and unused assets regularly — they add weight without value.

- **Search engine friendly** — every public page should have a descriptive
  `<title>`, `<meta name="description">`, Open Graph tags, and a canonical
  URL. The sitemap should be current. Structured data (JSON-LD) helps search
  engines understand page hierarchy and content type.

- **AI friendly** — maintain `llms.txt` as a plain-text summary of the site
  for LLM crawlers. Use semantic HTML so content is easy to parse. Keep
  `robots.txt` permissive for legitimate crawlers.

- **Secure** — apply a strict Content Security Policy, security headers on
  every response, and WAF rules to block scanners before they reach the
  worker. Security contact information should be in `.well-known/security.txt`.

- **Private** — no third-party tracking pixels, ad scripts, or cross-site
  cookies. Default to no analytics at all; if you do want traffic numbers,
  the only acceptable option is cookieless, privacy-first analytics injected
  at the edge (e.g. Cloudflare Web Analytics) — and its endpoint must be
  explicitly whitelisted in the CSP. External requests (fonts, APIs) should
  be minimised and explicitly whitelisted in the CSP.

- **Durable** — no build step of your own and a minimal dependency surface:
  ideally one runtime dependency, `hono` (the zero-dependency router), plus
  `marked` only if you add the Markdown article feature. The site should be
  readable and deployable years from now without any tooling changes.

- **Free to run** — Cloudflare Workers free tier is sufficient. Keep the
  architecture within those limits.

- **Perfect PageSpeed score** — every page should score 100 in Performance,
  Accessibility, Best Practices, and SEO in Google PageSpeed Insights. Treat
  any score below 100 as a bug. Use the audit results to guide fixes rather
  than working around them.

## Deployment

**Push to `main` → site is live. There is no separate deploy step.**

Cloudflare's Git integration runs `npm install` and then `wrangler deploy`
on every push to `main`. Never run `wrangler deploy` manually or suggest it.
Never push to a branch other than `main` without explicit permission.

## Architecture

Requests flow through three layers:

1. **Cloudflare edge** — WAF rules block bot scanners before the worker is
   invoked. Static files (favicon, robots.txt, etc.) are served directly from
   the asset layer without invoking the worker.
2. **`worker.js` (router)** — a [Hono](https://hono.dev) app. Matches the
   incoming URL and calls the appropriate page module. No HTML lives here.
3. **`pages/*.js` (page modules)** — one file per server-rendered page, each
   exporting a single function that takes request data and returns a
   `Response`. Pages are built on a layout (`layouts/`, one file per layout)
   and compose reusable pieces from `components/` (one file per component):
   - `layouts/minimal.js` — bare document shell + standardised SEO head,
     plus the shared document infra (`CSP`, `htmlResponse`, `escapeHtml`,
     `safeJsonLd`, font presets). Used by pages that bring their own chrome,
     such as the homepage and 404.
   - `layouts/site.js` — extends the minimal layout with the shared
     content-page chrome (column width, back link, `h1` typography, footer
     menu, and any site-wide overlays). Used by ordinary content pages.
   - `components/` — one file per reusable piece (footer, nav, any shared
     widget or script). Each exports `raw()`-wrapped CSS/markup/script blobs
     or small helper functions. Extract a component when markup is reused
     across pages; don't create one for single use.

Static assets bypass the worker entirely and are served by Cloudflare's asset
layer. Only dynamic routes invoke the worker.

### Routing pattern

```
bare domain/*               → 301 www
/CLAUDE.md, /NOTES.md, …    → 404 (BLOCKED repo files; also /cdn-cgi/*)
/security.txt               → 301 /.well-known/security.txt
/your-page                  → pages/your-page.js
/api/*                      → server-side proxy handlers (if any), CORS-gated
*                           → env.ASSETS.fetch() → static file or pages/not-found.js
```

Register both `/path` and `/path/` for every page route. `:slug` routes that
don't match a known item should fall through to the asset handler (then the
404 page).

## Stack & files

- `worker.js` — Hono router only. No HTML. Page routes register both `/path`
  and `/path/`; redirects, the `BLOCKED` repo-file list (`/CLAUDE.md`,
  `/NOTES.md`, `/README.md`, `/wrangler.jsonc`, `/package.json`,
  `/package-lock.json`, plus `/cdn-cgi/*`) returned as 404 before the asset
  layer, any CORS config (`hono/cors`), and the asset/404 fallback
  (`serveAssets`, also the `notFound` handler) live here.
- `package.json` — runtime dependencies kept to a minimum: `hono` (router)
  and, only if you use Markdown articles, `marked`. Cloudflare's Git
  integration runs `npm install` before `wrangler deploy`, which bundles them
  into the worker.
- `.assetsignore` — keeps `node_modules`, the package manifests, and the
  worker source (`worker.js`, `pages/`, `layouts/`, `components/`, and any
  data/source dirs) out of the static asset upload, since the assets
  directory is the repo root. Source files imported as ES modules must not be
  served raw.
- `layouts/` — one file per layout: `minimal.js` (document shell, SEO head,
  font presets, plus shared document infra: `CSP`, `htmlResponse`,
  `escapeHtml`, `safeJsonLd`) and `site.js` (content-page chrome on top of
  it). Add further layouts only when a group of pages shares chrome that the
  base layouts don't provide.
- `components/` — one file per reusable component. Each exports
  `raw()`-wrapped CSS/markup/script blobs or small helper functions.
- `pages/` — one JS module per server-rendered page (plus any `/api/*`
  request handlers).
- `wrangler.jsonc` — Worker config: `main: worker.js`, `assets: .`,
  `nodejs_compat`, `workers_dev: false`.
- Static files at repo root served directly by the asset layer (no worker
  invocation): `favicon.svg`, `favicon.ico`, `apple-touch-icon.png`,
  `og-default.png` (or similar), `robots.txt`, `sitemap.xml`, `llms.txt`,
  `.well-known/security.txt`, and any `images/` tree.
- Data files imported by the worker as ES modules (e.g. JSON content files,
  a generated article index).

### Required static files

These files must exist in the repo root. Generate them if missing — do not
leave them absent.

**`robots.txt`** — controls crawler access. Disallow `/.well-known/` so security.txt
is not indexed by search engines:
```
User-agent: *
Allow: /
Disallow: /.well-known/
Sitemap: https://www.example.com/sitemap.xml
```

**`sitemap.xml`** — lists all public URLs for search engines. Update the
`<lastmod>` date on any URL whose content changes:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.example.com/</loc>
    <lastmod>YYYY-MM-DD</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
```

**`llms.txt`** — a plain-text summary of the site for LLMs and AI crawlers.
Keep it in sync with the actual site content. Suggested structure:
```
# Your Name

> One-line description.

Brief paragraph about the site and its owner.

## Pages

- [Home](https://www.example.com/) — what's on the home page.
- [About](https://www.example.com/about) — bio and contact.

## Links

- [Website](https://www.example.com/)
```

**`.well-known/security.txt`** — security contact information per RFC 9116:
```
Contact: mailto:you@example.com
Expires: YYYY-MM-DDT00:00:00Z
Preferred-Languages: en
```
Update `Expires` annually. The worker should redirect `/security.txt` →
`/.well-known/security.txt`. Do not add this path to `sitemap.xml` — it is a
machine-readable file, not a page for search engines. The `robots.txt` disallow
rule for `/.well-known/` keeps it out of search indexes.

**`favicon.ico`** — a real `.ico` file (not just `.svg`) so that browser
requests for `/favicon.ico` are served by the asset layer without invoking
the worker. A 32×32 PNG embedded in ICO format is sufficient.

## Keeping files in sync

When making changes, check whether any of these files need updating:

| Change | Files to update |
|---|---|
| Add or remove a page | `sitemap.xml`, `llms.txt`, OG/Twitter tags on the new page |
| Update page content | `sitemap.xml` (`lastmod`), `llms.txt` |
| Change bio or contact | `llms.txt`, `.well-known/security.txt` |
| Add or update a social preview image | `og:image` and `twitter:image` on affected pages |
| Add external `fetch()` call | `CSP` (`connect-src`) in `layouts/minimal.js` |
| New page uses external font | `CSP` (`font-src`, `style-src`) in `layouts/minimal.js` |
| Year rolls over | `.well-known/security.txt` (`Expires`) |
| Remove a feature or page | Delete its code, route, and any assets; remove from `sitemap.xml` and `llms.txt` |

## Cloudflare configuration

- `workers_dev: false` in `wrangler.jsonc` is essential — without it,
  wrangler re-enables the `*.workers.dev` subdomain on every deploy,
  overriding any manual dashboard setting.
- A WAF Custom Rule (managed challenge or block) in the Cloudflare dashboard
  suppresses bot scanner paths before the worker is invoked. Go to
  **Security → WAF → Custom rules** and create a rule with this expression
  (action: Managed Challenge). The token list uses `lower()` so case tricks
  don't slip through, and is derived from probe families commonly seen in
  worker logs (LFI `/etc/`,`/proc/`; F5 BIG-IP `/tmui`+`.jsp`; framework
  debug `/actuator`,`trace.axd`,`/telescope`; `graphql`; Cisco `+cscoe+`;
  web-shell `alfacgiapi`; cPanel `/___proxy`). **Before enabling, verify
  none of these tokens collide with your own real worker routes** (a route
  like `/backup-guide` would be caught by the `/backup` token):

  ```
  (lower(http.request.uri.path) contains "wp-")
  or (lower(http.request.uri.path) contains ".php")
  or (lower(http.request.uri.path) contains ".env")
  or (lower(http.request.uri.path) contains "/.git")
  or (lower(http.request.uri.path) contains "xmlrpc")
  or (lower(http.request.uri.path) contains "phpmyadmin")
  or (lower(http.request.uri.path) contains "phpinfo")
  or (lower(http.request.uri.path) contains "/.aws")
  or (lower(http.request.uri.path) contains "/.ssh")
  or (lower(http.request.uri.path) contains "/cgi-bin")
  or (lower(http.request.uri.path) contains "/autodiscover")
  or (lower(http.request.uri.path) contains "/.svn")
  or (lower(http.request.uri.path) contains "/.hg")
  or (lower(http.request.uri.path) contains "/.vscode")
  or (lower(http.request.uri.path) contains "/.circleci")
  or (lower(http.request.uri.path) contains "/etc/")
  or (lower(http.request.uri.path) contains "/proc/")
  or (lower(http.request.uri.path) contains "/storage/")
  or (lower(http.request.uri.path) contains "/config/")
  or (lower(http.request.uri.path) contains "/secrets")
  or (lower(http.request.uri.path) contains "/credentials")
  or (lower(http.request.uri.path) contains "web.config")
  or (lower(http.request.uri.path) contains "vercel.json")
  or (lower(http.request.uri.path) contains ".jsp")
  or (lower(http.request.uri.path) contains "/tmui")
  or (lower(http.request.uri.path) contains "/actuator")
  or (lower(http.request.uri.path) contains "/server-status")
  or (lower(http.request.uri.path) contains "trace.axd")
  or (lower(http.request.uri.path) contains "/telescope")
  or (lower(http.request.uri.path) contains "/helm/")
  or (lower(http.request.uri.path) contains "/vendor/")
  or (lower(http.request.uri.path) contains "/debug/")
  or (lower(http.request.uri.path) contains "/backup")
  or (lower(http.request.uri.path) contains "graphql")
  or (lower(http.request.uri.path) contains "/api/gql")
  or (lower(http.request.uri.path) contains "+cscoe+")
  or (lower(http.request.uri.path) contains "alfacgiapi")
  or (lower(http.request.uri.path) contains "alfa_data")
  or (lower(http.request.uri.path) contains "/___proxy")
  or (http.request.uri.path eq "/CLAUDE.md")
  or (http.request.uri.path eq "/NOTES.md")
  or (http.request.uri.path eq "/README.md")
  or (http.request.uri.path eq "/wrangler.jsonc")
  or (http.request.uri.path eq "/package.json")
  or (lower(http.request.uri.path) contains "/cdn-cgi")
  or (lower(http.request.uri.path) contains ".htaccess")
  or (lower(http.request.uri.path) contains ".htpasswd")
  or (lower(http.request.uri.path) contains "id_rsa")
  or (lower(http.request.uri.path) contains "/.azure")
  or (lower(http.request.uri.path) contains "docker-compose")
  or (lower(http.request.uri.path) contains "node_modules")
  or (lower(http.request.uri.path) contains "swagger")
  ```

  A second optional rule (also Managed Challenge) catches named scanner
  user-agents that probe legitimate-looking paths. It deliberately excludes
  bare `curl/`, `python-requests`, and `Go-http-client` so scripted clients
  and uptime monitors you run yourself are not challenged:

  ```
  (lower(http.user_agent) contains "l9scan")
  or (lower(http.user_agent) contains "leakix")
  or (lower(http.user_agent) contains "nuclei")
  or (lower(http.user_agent) contains "sqlmap")
  or (lower(http.user_agent) contains "nikto")
  or (lower(http.user_agent) contains "masscan")
  ```

  Blocked requests appear in Security Events, not worker invocation logs.
- `observability.enabled: true` — worker invocation logs.
- Static files are served by Cloudflare's asset layer without invoking the
  worker. Add a real `favicon.ico` so browser icon requests don't fall
  through to the worker.

## Cache busting

Goal: a push to `main` is visible within ~1 minute, with no manual version
bumps and no Cloudflare API key. Only relevant if you add dynamic `/api/*`
handlers that cache upstream responses; static assets are versioned by
Cloudflare automatically.

Two layers cooperate:

1. **Edge cache (`caches.default`)** — every `/api/*` handler keys its cache
   entries with a `CACHE_VERSION` constant. A `pre-commit` hook
   (`.githooks/pre-commit`) rewrites `CACHE_VERSION` to a UTC timestamp on
   **every commit**, so each deploy lands in a fresh cache namespace and the
   worker recomputes with the new code. One-time local setup:
   `git config core.hooksPath .githooks` (run it after a fresh clone if
   commits stop stamping).
2. **Browser cache** — handlers store long-lived copies in `caches.default`
   (cheap reuse) but **return** responses with a short `max-age` so a
   returning visitor picks up a new deploy quickly instead of serving a stale
   copy from their own cache. HTML responses use `max-age=60, must-revalidate`
   for the same reason.

When adding a new `/api/*` handler, follow the pattern: key the cache with
`CACHE_VERSION`, store long, return with a short `max-age`. Do **not** hardcode
`?v=N` cache keys.

## Security headers

Every HTML response gets security headers from the `CSP` constant in
`layouts/minimal.js` — applied by `htmlResponse()` for server-rendered pages
and by `serveAssets()` in `worker.js` for HTML from the asset layer:

```js
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data:",
  "connect-src 'self'",   // add external API origins here
  "object-src 'none'",
  "frame-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ');
```

Also applied to every HTML response: `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
`Strict-Transport-Security: max-age=63072000`, and
`Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`.

**Adding a new external `fetch()` target requires updating `connect-src`** —
but only origins the *browser* talks to directly. Anything reached
server-side through an `/api/*` proxy needs no `connect-src` entry, since the
browser only ever talks to same-origin `/api/*`.

## Fonts

Worker-rendered pages load fonts through font presets defined in
`layouts/minimal.js`. Follow this guidance regardless of typeface:

- Always use a synchronous `<link rel="stylesheet">` for Google Fonts — no
  `media="print" onload` async trick. Async loading causes a flash of
  unstyled text (FOUT) that is especially jarring with display or monospace
  faces (visible serif fallback before the real font loads).
- Always append `&display=block` to the Google Fonts URL, never
  `&display=swap`. `swap` renders the fallback font immediately and then swaps
  — visually jarring. `block` holds text invisible briefly until the font is
  ready, which is imperceptible.
- Keep the number of typefaces small and give each a distinct job (e.g. a
  display face for headings, a body serif/sans for copy, a monospace for
  labels/code). Don't add a face without a clear role.

## Performance

Apply these automatically — do not wait to be asked.

- `<meta name="viewport" content="width=device-width, initial-scale=1">` must
  be present on every page.
- Images should be served in WebP format where possible. Always include explicit
  `width` and `height` attributes to prevent layout shift (CLS).
- Use `loading="lazy"` on below-fold images. Never lazy-load the first visible
  image — it delays LCP.
- No render-blocking scripts. Use `defer` or `async` on all `<script>` tags
  that are not critical to first render.

## Design and quality bar

Apply these standards to every change involving HTML, CSS, or layout — do not wait to be asked.

**Accessibility:**
- Color contrast must meet WCAG AA (4.5:1 for body text, 3:1 for large text)
- All interactive elements must be keyboard-navigable and have visible focus styles
- Use semantic HTML so screen readers get structure for free (headings, landmarks, lists)
- Images need meaningful `alt` text; purely decorative images use `alt=""`

**Responsive layout:**
- Design mobile-first — small viewports are the baseline, not an afterthought
- No horizontal scroll on any viewport width
- Touch targets should be at least 44×44px

**Visual consistency:**
- Match the existing design language (palette, type scale, spacing rhythm) before introducing anything new
- Prefer refinement over decoration — whitespace and typography carry more weight than added elements
- New UI patterns need a strong reason to exist; default to what's already on the page

**Code quality:**
- CSS should use existing custom properties rather than hardcoded values
- No inline styles unless dynamically computed
- Keep markup clean and minimal — avoid wrapper divs that exist only for styling convenience

## SEO and AI checklist

Apply these automatically whenever adding or updating a page — do not wait to be asked.

**Every server-rendered page must have:**
- `<title>` — descriptive, unique per page, ideally under 60 characters
- `<meta name="description">` — 1–2 sentence summary, under 160 characters
- `<link rel="canonical">` — the page's own absolute URL (with `www`)
- Open Graph tags: `og:title`, `og:description`, `og:url`, `og:type`,
  `og:image` (absolute URL, 1200×630px), `og:image:alt`
- Twitter/X card tags: `twitter:card` (`summary_large_image`), `twitter:title`,
  `twitter:description`, `twitter:image`

If no page-specific image exists, fall back to a default at a known static path
(e.g. `/og-default.png`) rather than omitting the tag.

**Structured data (JSON-LD):**
- Homepage: `Person` or `WebSite` schema
- Content listing pages: `ItemList` schema
- Individual content pages: `Article` or `WebPage` schema
- Embed in a `<script type="application/ld+json">` tag in `<head>`

**Semantic HTML:**
- Use `<main>`, `<article>`, `<nav>`, `<header>`, `<footer>` appropriately
- One `<h1>` per page matching the page title
- Images must have meaningful `alt` text; decorative images use `alt=""`
- Link text should be descriptive — not "click here" or "read more"

**AI crawlers:**
- Update `llms.txt` whenever page content or structure changes meaningfully.
  Each page entry should include a one-sentence description so LLM crawlers
  get useful context, not just a URL.
- Keep `robots.txt` permissive — don't accidentally block legitimate crawlers

**Sitemap:**
- Update `<lastmod>` on any URL whose content changes
- Add new pages immediately; remove deleted ones

## Adding a new page

1. Create `pages/my-page.js` — export a default function that returns
   `siteLayout({ meta, current, css, jsonLd, main, bodyEnd })` from
   `layouts/site.js` (or `minimalLayout` from `layouts/minimal.js` for
   chrome-less pages). Page fragments are `` html`...` `` templates from
   `hono/html`; the layout handles the document shell, SEO head, security
   headers, and (for the site layout) the chrome. Pull shared pieces from
   `components/`; extract a new component when markup is reused across pages.
2. Add a route in `worker.js` that calls it (register both `/path` and
   `/path/`).
3. Apply the full SEO and AI checklist above.
4. Add the URL to `sitemap.xml`.
5. Update `llms.txt`.

## 404 page

`pages/not-found.js` handles all unmatched routes (see routing pattern above).
It must always exist and must include a link back to the homepage (`/`). Keep
it simple: a short message and a "Go home" link styled to match the site.
Return a 404 status code — do not return 200 for missing pages.

## Templating with hono/html

Pages are built with the `` html`...` `` tagged template from `hono/html`:

- **Interpolated `${...}` values are auto-escaped** (`& < > " '`) — never
  call `escapeHtml()` on a value flowing into an `` html`` `` template, or it
  will double-escape. Static text in the template itself is not escaped.
- Nested `` html`` `` snippets and arrays of snippets interpolate without
  re-escaping — build lists with `items.map(x => html`<li>${x}</li>`)`
  (no `.join('')`).
- Trusted blobs that must not be escaped (inline JS, CSS, SVG markup, strings
  containing entities) are wrapped with `raw()`. Component exports are
  pre-wrapped.
- `escapeHtml()` is still used where HTML is hand-assembled as a plain string;
  wrap the finished string in `raw()`.

## Articles (optional Markdown feature)

If the site has a blog/writing section, keep articles as Markdown files in
`articles/` rather than hand-written HTML. Each file has frontmatter
(`slug`, `title`, `date`, optional `excerpt`) delimited by `---` lines,
followed by the Markdown body, and is rendered with `marked` (GFM). A
pre-commit hook can regenerate an `articles/index.js` (imports, frontmatter
parse, date-sorted) and an RSS `feed.xml` from the `.md` files so the index
and feed stay in sync without manual edits — drop in a `.md`, commit, done.

`pages/article.js` parses the body with `marked`, builds a table of contents
from the `##`–`####` headings, adds slug `id`s to headings for anchor links,
marks external links `rel="nofollow noopener noreferrer" target="_blank"`, and
emits `Article` + `BreadcrumbList` JSON-LD. You can extend `marked` with a
`code` renderer hook to support custom fenced block types for richer layouts.
If you add a feed, link it via `<link rel="alternate"
type="application/rss+xml">` in the layout head, and **do not edit `feed.xml`
by hand** — let the hook regenerate it.

## Editing gotchas

- Template literals in `pages/*.js` are indentation-sensitive — preserve
  surrounding whitespace when editing inline HTML/CSS blocks.
- Ensure every render function's template literal has its closing backtick.
  A missing backtick causes a silent build error ("Unexpected ':'") that
  prevents the site from updating.
- Don't introduce a build step of your own. The site is deliberately
  source-direct; the only build is Cloudflare running `npm install` +
  `wrangler deploy`.
- New external API? Update `connect-src` in `CSP`.

---

## Human setup steps

See `README.md`.

## Project specifics

See `NOTES.md`.
