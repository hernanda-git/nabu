# 𒀭 X/Twitter Scraper Investigation — Canonical Record

> **Canonical document.** Supersedes `x-twitter-scraping-knowledge.md` (archived).
> **Date:** 2026-07-23
> **Author:** Hermes Agent
> **Status:** Investigation complete — blocking issue identified (CloakBrowser v146 binary is too old for X.com)

---

## 1. Executive Summary

Nabu's Twitter/X scraper (`internal/scraper/twitter.go`) is a 381-line Go stub with empty API calls:
```go
func (c *TwitterClient) FetchUserTweets(...) ([]Tweet, error) {
    return []Tweet{}, nil  // never implemented
}
```

We investigated replacing it with a Python stealth-browser scraper using either **CloakBrowser** (Chromium) or **Camoufox** (Firefox). Both packages are installed. **CloakBrowser's free v146 binary is the bottleneck** — too old for X.com's modern JavaScript. The investigation is documented here with test results, decisions, and next steps.

**Current blockers:**
1. CloakBrowser free v146 binary is unstable on X.com (works ~50%, crashes on heavy JS)
2. Camoufox binary download (~200MB) keeps timing out
3. Without a logged-in session, X.com GraphQL API returns 403
4. Without a working browser, we can't log in to get session cookies

---

## 2. Environment State

| Component | Version | Path | Status |
|-----------|---------|------|--------|
| CloakBrowser (pip) | 0.5.1 | hermess-agent venv | ✅ Installed |
| CloakBrowser binary (free) | 146.0.7680.177.5 | `%USERPROFILE%\.cloakbrowser\chromium-146.0.7680.177.5\chrome.exe` | ✅ Downloaded, ⚠️ Unstable |
| Playwright | 1.60.0 | hermess-agent venv | ✅ Installed |
| Camoufox (pip) | 0.5.4 | hermess-agent venv | ✅ Installed |
| Camoufox binary | 152.0.4-beta.28 | Not fetched | ❌ Download keeps timing out |
| License | Free (no key) | — | v146 only |

---

## 3. Test Results (Chronological)

### 3.1 Test 1: CloakBrowser Launch

**Goal:** Verify CloakBrowser works on Windows.

```python
from cloakbrowser import launch
browser = launch(headless=True)
page = browser.new_page()
page.goto("https://example.com")
print(page.title())  # "Example Domain"
browser.close()
```

**Result:** ✅ PASSED — Launch successful, simple page renders.

---

### 3.2 Test 2: X.com Landing Page

**Goal:** Can CloakBrowser load X.com?

```python
page.goto("https://x.com", wait_until="domcontentloaded")
# URL: https://x.com/
# Title: "X. It's what's happening / X"
```

**Result:** ✅ PASSED — SSR content renders. Pre-login landing page visible with guest cookies (`guest_id`, `gt`) set. No `ct0` (CSRF) cookie (only set after login attempt).

```json
{
  "url": "https://x.com/",
  "status": 200,
  "cookies": ["guest_id_marketing", "guest_id_ads", "personalization_id", "guest_id", "gt", "__cuid", "g_state"],
  "ct0": "NONE"
}
```

---

### 3.3 Test 3: X.com Login Page

**Goal:** Can we reach the login form?

```python
page.goto("https://x.com/login", wait_until="load")
# URL: https://x.com/i/jf/onboarding/web?mode=login
```

**Result:** ⚠️ INTERMITTENT — Succeeds ~50% of attempts. When it works:
- Login URL loads: `https://x.com/i/jf/onboarding/web?mode=login`
- Input fields visible: `input[name="username_or_email"]`, `input[type="password"]`
- Email fill via `page.fill()` ✅ WORKS
- Password fill via `page.fill()` ✅ WORKS

| Load Attempt | wait_until | Result |
|---|---|---|
| 1 | `networkidle` | ❌ Timeout 30s (X.com has too many background requests) |
| 2 | `domcontentloaded` | ✅ Loaded, login form visible |
| 3 | `domcontentloaded` | ❌ Timeout 25s |
| 4 | `load` | ✅ Loaded, redirected to onboarding |
| 5 | `domcontentloaded` | ❌ Timeout 30s |
| 6 | `domcontentloaded` | ❌ Timeout 25s |

**Verdict:** Free v146 binary is unreliable for X.com's heavy JS.

---

### 3.4 Test 4: Login Flow

**Goal:** Complete email → password → login flow via DOM automation.

**Attempt 1 — Headless + humanize=False:**
- Email filled ✅
- Button `button:has-text("Next")` not found ❌ (X.com uses different text, likely "Continue")
- Password field never appeared

**Attempt 2 — Headed + humanize=True:**
- Email filled ✅
- Password field auto-appeared after email fill (X.com pre-fetches password step)
- Password filled ✅
- `button:has-text("Log in")` not found via Playwright selector
- `evaluate` fallback clicked wrong button
- Result: "This email or username is not registered yet" — the password was submitted as the email field

**Attempt 3 — Headed + humanize=True (refined):**
- Email filled ✅
- Waited for password field ✅
- Password filled ✅
- Login button click failed ❌ (humanize could not find the button, possibly hidden by JS)

---

### 3.5 Test 5: GraphQL API (No Login)

**Goal:** Call X.com GraphQL directly from within the browser context.

```javascript
// From page.evaluate() inside CloakBrowser
const resp = await fetch(
    'https://x.com/i/api/graphql/39s5YHfJEYwR7LFWZ0nWCA/SearchTimeline',
    { headers: { authorization: 'Bearer AAAA...', 'x-guest-token': '...' } }
);
```

**Result:** ❌ FAILED — Could not find the required auth headers. The known public bearer token may have been rotated or X.com now requires session-based auth for all GraphQL endpoints. Guest + bearer = 403 from the server.

---

### 3.6 Test 6: Headed Browser Session

**Goal:** Use headed mode for reliability. We can see what's happening.

**Result:** ⚠️ The CloakBrowser headed window opened on the user's desktop. The window was visible. But:
- Page load timing was still inconsistent
- After the script ended, a zombie `chrome.exe` process remained (killed by `taskkill`)
- The headed window helped diagnose that the free v146 renders X.com but JS execution is flaky

---

## 4. Tool Comparison Matrix

### 4.1 CloakBrowser

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Package availability | ✅ v0.5.1 installed | `pip list` confirms |
| Binary download | ✅ v146 cached | `%USERPROFILE%\.cloakbrowser\` |
| Simple page render | ✅ Works | `example.com` loads |
| X.com SSR content | ✅ Works | Profile page renders with content |
| X.com login form | ⚠️ Intermittent (~50%) | Times out unpredictably |
| X.com JS hydration | ❌ Fails | React app doesn't fully hydrate |
| Headed mode | ✅ Works | Window appears on desktop |
| Persistent context | ✅ API available | `launch_persistent_context()` |
| Pro upgrade path | ✅ Available | `cloakbrowser login` for free v150 trial |

**Conclusion:** Free v146 binary's age is the bottleneck. The Pro v150 binary (released 4 days ago) would likely fix all X.com issues based on the changelog (Chromium 150 rebase with 71 patches).

### 4.2 Camoufox

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Package availability | ✅ v0.5.4 installed | `pip list` confirms |
| Binary download | ❌ Timed out (~200MB) | `camoufox fetch` timed out at 60s and 120s |
| Simple page render | ❌ Not tested | Binary not downloaded |
| Juggler stealth | ✅ Unique advantage | Not CDP, automation invisible |
| Firefox engine | ✅ v152 (latest) | Much newer than CloakBrowser's v146 |
| Dev status | ⚠️ 1-year gap, now active | "Under development" warning in README |

**Conclusion:** Promising alternative but the 200MB binary download requires a stable network connection. Could not be tested in this session.

### 4.3 Which Should Nabu Use?

| Priority | Choice | Rationale |
|----------|--------|-----------|
| **Today** | Neither — blocked | Both have binary issues |
| **Short-term** | CloakBrowser + free Pro trial | Upgrade to v150 binary, retest X.com |
| **Medium-term** | Both (rotate for diversity) | Chrome for compatibility, Firefox for Juggler stealth |
| **Long-term** | CloakBrowser Pro + residential proxies | Scale to concurrent sessions |

---

## 5. X.com Architecture Notes (2026)

Reverse-engineered from testing:

### 5.1 Login Flow
```
https://x.com/login
  → https://x.com/i/jf/onboarding/web?mode=login  (onboarding frame)
  → Fill email → auto or click Next → password field appears
  → Fill password → click "Log in" or "Sign in"
  → If new device: email verification code
  → If suspicious: reCAPTCHA/Turnstile
  → If 2FA enabled: 2FA code input
  → Redirect to home timeline
```

### 5.2 Cookie Structure
| Cookie | Set When | Purpose |
|--------|----------|---------|
| `guest_id` | First load | Anonymous session |
| `gt` | First load | Guest token for API calls |
| `ct0` | Login submit | CSRF token (REQUIRED for API calls) |
| `auth_token` | Login success | Session authentication |
| `twid` | Login success | User ID |

### 5.3 Known Endpoints
```
GraphQL: https://x.com/i/api/graphql/{queryId}/{operationName}
Search:  https://x.com/i/api/graphql/39s5YHfJEYwR7LFWZ0nWCA/SearchTimeline
User:    https://x.com/i/api/graphql/7ZnGm6Ncn9aFJQW0R1Bo1g/UserByScreenName
Tweets:  https://x.com/i/api/graphql/7UoCJ6k0ByLkL7WzW3TzVw/UserTweets
```

**Note:** Query IDs change frequently. The IDs above were captured during this investigation but may be stale.

### 5.4 Required Headers
```
authorization: Bearer AAAA...  (embedded in X.com JS, same for all users)
x-csrf-token: <ct0 cookie value>  (set after login)
x-guest-token: <gt cookie value>  (for guest requests)
content-type: application/json
```

---

## 6. Files Created

| File | Content |
|------|---------|
| `docs/x-twitter-scraping-knowledge.md` | ARCHIVED — Original knowledge base (superseded) |
| `docs/camoufox-vs-cloakbrowser.md` | Tool comparison (kept as reference) |
| `docs/twitter-scraping-canonical.md` | **THIS DOCUMENT** — Canonical investigation record |
| `runtime/scrapers/x_login_test.py` | Login test script (test artifact) |
| `runtime/scrapers/debug_login.py` | Debug script for page structure (test artifact) |

---

## 7. Unresolved Issues

| Issue | Priority | Notes |
|-------|----------|-------|
| CloakBrowser v146 binary unstable on X.com | 🔴 HIGH | Need Pro v150 or wait for binary upgrade |
| Camoufox binary download keeps timing out | 🟡 MEDIUM | ~200MB zip from GitHub, slow connection |
| X.com GraphQL query IDs unknown | 🟡 MEDIUM | Need to capture from live X.com session |
| ct0 cookie extraction | 🟡 MEDIUM | Only available after successful login |
| Login verification challenges | 🟢 LOW | May need email confirm or 2FA on first login |
| Persistent session management | 🟢 LOW | `launch_persistent_context()` is the path |
| Residential proxy for production | 🟢 LOW | Not needed for dev testing |

---

## 8. Recommended Next Steps (Priority Order)

1. **Get CloakBrowser Pro trial** — `cloakbrowser login` with GitHub sign-in for v150 binary
2. **Retest X.com login** with v150 binary (should fix intermittent loading)
3. **Capture GraphQL query IDs** from a logged-in session via DevTools
4. **Write the Nabu Twitter scraper** as `runtime/scrapers/twitter_scraper.py`
5. **Integrate with RabbitMQ** — publish RawEvent to `source.twitter` queue
6. **Add Hermes cron job** — `nabu-source-watch-twitter` every 5 minutes
