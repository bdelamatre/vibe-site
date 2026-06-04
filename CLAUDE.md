# Personal Website — Cloudflare Workers + Static Assets

Minimal personal site deployed to Cloudflare Workers. The stack is
intentionally simple: a GitHub repo is the source of truth, Cloudflare
Workers serves the site, and every push to `main` deploys automatically.
No build step, no CI pipeline, no hosting fees.

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

- **Private** — no third-party analytics, tracking pixels, or ad scripts.
  External requests (fonts, APIs) should be minimised and explicitly
  whitelisted in the CSP.

- **Durable** — no build step, no framework churn, no dependencies to
  upgrade. The site should be readable and deployable years from now without
  any tooling changes.

- **Free to run** — Cloudflare Workers free tier is sufficient. Keep the
  architecture within those limits.

- **Perfect PageSpeed score** — every page should score 100 in Performance,
  Accessibility, Best Practices, and SEO in Google PageSpeed Insights. Treat
  any score below 100 as a bug. Use the audit results to guide fixes rather
  than working around them.

## Deployment

**Push to `main` → site is live. There is no separate deploy step.**

Cloudflare's Git integration auto-deploys on every push to `main`. Never run
`wrangler deploy` manually or suggest it. Never push to a branch other than
`main` without explicit permission.

## Architecture

Requests flow through three layers:

1. **Cloudflare edge** — WAF rules block bot scanners before the worker is
   invoked. Static files (favicon, robots.txt, etc.) are served directly from
   the asset layer without invoking the worker.
2. **`worker.js` (router)** — ~50 lines. Matches the incoming URL and calls
   the appropriate page module. No HTML lives here.
3. **`pages/*.js` (page modules)** — one file per server-rendered page, each
   exporting a single function that takes request data and returns a
   `Response`.

Static assets bypass the worker entirely and are served by Cloudflare's asset
layer. Only dynamic routes invoke the worker.

### Routing pattern

```
bare domain/*       → 301 www
/security.txt       → 301 /.well-known/security.txt
/your-page          → pages/your-page.js
*                   → env.ASSETS.fetch() → static file or pages/not-found.js
```

## Stack & files

- `worker.js` — router only. No HTML.
- `pages/` — one JS module per server-rendered page.
- `index.html` — single-file homepage: inline CSS, inline SVG, inline JS.
- `wrangler.jsonc` — Worker config: `main: worker.js`, `assets: .`,
  `nodejs_compat`, `workers_dev: false`.
- Static files at repo root served directly by the asset layer (no worker
  invocation): `favicon.svg`, `favicon.ico`, `robots.txt`, `sitemap.xml`,
  `llms.txt`, `.well-known/security.txt`.
- Data files imported by the worker as ES modules.

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
| Add external `fetch()` call | `CSP` (`connect-src`) in `worker.js` |
| New page uses external font | `CSP` (`font-src`, `style-src`) |
| Year rolls over | `.well-known/security.txt` (`Expires`) |
| Remove a feature or page | Delete its code, route, and any assets; remove from `sitemap.xml` and `llms.txt` |

## Cloudflare configuration

- `workers_dev: false` in `wrangler.jsonc` is essential — without it,
  wrangler re-enables the `*.workers.dev` subdomain on every deploy,
  overriding any manual dashboard setting.
- A WAF Custom Rule (managed challenge or block) in the Cloudflare dashboard
  suppresses bot scanner paths before the worker is invoked. Go to
  **Security → WAF → Custom rules** and create a rule with this expression
  (action: Managed Challenge):

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
  ```

  Optionally add a second rule (also Managed Challenge) targeting known scanner
  user-agents. Exclude bare `curl`/`python-requests`/`Go-http-client` so your
  own scripts and monitors aren't challenged:

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

## Security headers

`worker.js` applies security headers to every HTML response via a `CSP`
constant at the top of the file:

```js
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data:",
  "connect-src 'self'",   // add external API origins here
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ');
```

Also applied: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`.

**Adding a new external `fetch()` target requires updating `connect-src`.**

## Fonts

- **Home page** (`index.html`): async loading (`media="print" onload`) —
  FOUT acceptable for display fonts.
- **Worker-rendered pages** (`pages/*.js`): **synchronous**
  `<link rel="stylesheet">` — required when using monospace fonts to prevent
  fallback serif rendering before the font loads (very visible with monospace).

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

1. Create `pages/my-page.js` — export a default function that returns a
   `Response` with `Content-Type: text/html` and the `CSP`/security headers.
2. Add a route in `worker.js` that calls it.
3. Apply the full SEO and AI checklist above.
4. Add the URL to `sitemap.xml`.
5. Update `llms.txt`.

## 404 page

`pages/not-found.js` handles all unmatched routes (see routing pattern above).
It must always exist and must include a link back to the homepage (`/`). Keep
it simple: a short message and a "Go home" link styled to match the site.
Return a 404 status code — do not return 200 for missing pages.

## Editing gotchas

- Template literals in `pages/*.js` are indentation-sensitive — preserve
  surrounding whitespace when editing inline HTML/CSS blocks.
- Ensure every render function's template literal has its closing backtick.
  A missing backtick causes a silent build error ("Unexpected ':'") that
  prevents the site from updating.
- Don't introduce a build step. The site is deliberately source-direct.
- New external API? Update `connect-src` in `CSP`.

---

## Human setup steps

See `README.md`.

## Project specifics

See `NOTES.md`.
