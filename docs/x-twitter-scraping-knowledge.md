# 𒀭 X/Twitter Scraping for Nabu — Knowledge Base (ARCHIVED)

> **⚠️ ARCHIVED — This document is superseded by `twitter-scraping-canonical.md`.**
> **See canonical document for the complete investigation record, test results, and decisions.**

---

## 1. The Problem

Twitter/X API v2 is prohibitively expensive for real-time scraping. Nabu needs to monitor 20+ accounts + keywords every 5 minutes. Even Basic tier ($100/mo, 10K posts) would exhaust within hours.

### Rate Limits vs Nabu's Needs

| Source | Polls/Hour | Posts/Check | Daily Total | API Tier Needed |
|--------|-----------|-------------|-------------|----------------|
| 20 accounts | 12 (5min) | 20 each | 4,800 | Basic ($100/mo) |
| 10 keywords | 12 (5min) | 50 each | 6,000 | Basic ($100/mo) |
| **Total** | | | **10,800/day** | **Pro ($5K/mo)** |

This makes API-based scraping economically unviable.

---

## 2. Tools

### CloakBrowser (Chosen for V1)
- **Engine:** Chromium fork
- **Stealth:** 71 C++ source-level patches
- **Python:** `pip install cloakbrowser`
- **API:** Drop-in Playwright replacement
- **Binary:** Free v146 / Pro v150
- **License:** Free (1 session) or Pro (5-2000+ sessions)
- **Docker:** `cloakhq/cloakbrowser`
- **GitHub:** https://github.com/CloakHQ/cloakbrowser

### Camoufox (Alternative)
- **Engine:** Firefox fork (v152)
- **Stealth:** Juggler protocol sandboxing + C++ patches
- **Python:** `pip install camoufox` or `pip install cloverlabs-camoufox`
- **Key advantage:** Juggler (not CDP) makes automation genuinely invisible
- **Key risk:** "Under development" — had 1-year gap
- **GitHub:** https://github.com/daijro/camoufox (10,383 ⭐)

### stealth-x (Abandoned)
- **Description:** X/Twitter CLI built on Camoufox (2 ⭐, unmaintained)
- **GitHub:** https://github.com/Youhai020616/stealth-x

### Nitter (Not Used)
- **Description:** Self-hosted Twitter front-end proxy
- **Problem:** Instances get blocked by Twitter, unreliable

---

## 3. Architecture: Browser-Internal GraphQL

### How It Works

X.com's own webapp uses internal GraphQL API endpoints. From within a CloakBrowser context, `page.evaluate()` can call `fetch()` using the browser's real TLS fingerprint, bypassing Twitter's API rate limits.

```
Nabu Python Scraper → CloakBrowser (stealth Chromium)
  → page.evaluate("fetch(url, options)")
     → X.com GraphQL API (real Chrome TLS fingerprint)
        → JSON response with tweets
```

### Why Not the Official API?

| Factor | API v2 | Browser GraphQL |
|--------|--------|-----------------|
| Cost | $100-$5,000/mo | Free |
| Rate limits | 15-300 req/15min | Browser-level (much higher) |
| Auth | Bearer token | Guest session + cookies |
| Data format | REST JSON | GraphQL JSON |
| Reliability | High (contract) | Medium (breaks on update) |

---

## 4. CloakBrowser Installation Status

| Component | Status |
|-----------|--------|
| Package | ✅ v0.5.1 installed |
| Binary (free v146) | ✅ Cached at `%USERPROFILE%\.cloakbrowser\chromium-146...` |
| License | 🔵 Free (no key) — upgrade: `cloakbrowser login` |
| GeoIP | ❌ Not installed (`pip install cloakbrowser[geoip]`) |

### Upgrade to v150 Pro Trial
```bash
cloakbrowser login  # Interactive GitHub sign-in → free trial key
```

---

## 5. X.com Session Management

### Login Flow (Planned)
```python
from cloakbrowser import launch_persistent_context

# One-time: log in with headed browser (you handle verification)
ctx = launch_persistent_context("./x-profile", headless=False, humanize=True)
page = ctx.new_page()
page.goto("https://x.com/login")
page.fill("input[name='username_or_email']", "your@email.com")
page.fill("input[type='password']", "yourpass")
page.click("button[type='submit']")
# Handle any verification manually
ctx.close()  # Session saved to disk permanently

# Subsequent runs: no login needed
ctx = launch_persistent_context("./x-profile", headless=True)
page = ctx.new_page()
page.goto("https://x.com")
# Already logged in — cookies restored
```

### Session Storage
```
./x-profile/          ← Persistent user data directory
├── Default/
│   ├── Cookies       ← Login cookies (auth_token, ct0, twid)
│   ├── Local Storage ← X.com state
│   └── Cache/        ← Browser cache (avoids re-downloading JS)
└── state.json        ← Playwright storage state export
```

---

## 6. GraphQL Endpoints

### Known Query IDs (May Be Stale)
```
SearchTimeline:  39s5YHfJEYwR7LFWZ0nWCA
UserByScreenName: 7ZnGm6Ncn9aFJQW0R1Bo1g
UserTweets:      7UoCJ6k0ByLkL7WzW3TzVw
TweetDetail:     0hWvD7eG5jLl8SxQ9rRzZw
```

### Example: Search Twitter
```javascript
const resp = await fetch(
    'https://x.com/i/api/graphql/' + queryId + '/SearchTimeline?' +
    new URLSearchParams({
        variables: JSON.stringify({
            rawQuery: "airdrop",
            count: 20,
            product: "Top",
            includePromotedContent: false
        })
    }).toString(),
    {
        headers: {
            'authorization': 'Bearer AAAA...',
            'x-csrf-token': csrfToken,
            'content-type': 'application/json'
        }
    }
);
```

---

## 7. Additional Notes

- **Headless mode** may still be detectable by X.com even with CloakBrowser. Use `headless=False` for critical operations (login), then switch to `headless=True` for routine scraping.
- **Humanize** (`humanize=True`) is essential for login — provides Bézier mouse curves, variable typing speed, and realistic scroll patterns.
- **Residential proxies** improve reliability significantly. Datacenter IPs are often blocked.
- **GraphQL query IDs** change when X.com updates their frontend. Build auto-discovery by scanning `main.*.js` bundles for the known token pattern.
- For alternative sources (no login needed), see the RSS scraper in Phase 1 of the implementation plan.
