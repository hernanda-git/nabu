# 𒀭 Camoufox vs CloakBrowser — Comparison for X/Twitter Scraping

> **Date:** 2026-07-23
> **Purpose:** Side-by-side comparison of both anti-detect browsers for Nabu's Twitter/X scraper

---

## 1. Executive Summary

**Both tools are already installed as Python packages** on this machine. Neither requires any code to evaluate — their APIs are drop-in Playwright wrappers.

| Tool | Package Version | Binary Status | Launch Test |
|------|---------------|--------------|-------------|
| **CloakBrowser** | 0.5.1 | ✅ Downloaded (Chromium 146 free) | ✅ PASSED |
| **Camoufox** | 0.5.4 | ❌ Not fetched yet (~200MB download timed out) | ❌ Not tested |

---

## 2. Architecture Deep-Dive

### Camoufox 🦊 (Firefox Fork)

```
camoufox (Python package) → Playwright Firefox → Juggler Protocol → Camoufox Binary (C++ Firefox fork)
```

| Aspect | Detail |
|--------|--------|
| **Engine** | Firefox (currently v152) |
| **Protocol** | **Juggler** (custom, not CDP) |
| **Stars** | 10,383 ⭐ — very popular |
| **Dev Status** | ⚠️ "Under development" — had 1-year gap, degraded performance |
| **Last push** | 2026-07-19 (4 days ago) |
| **Python** | `camoufox` package v0.5.4 |
| **Fingerprint method** | **BrowserForge** — statistical distribution from real traffic |
| **Stealth via** | Juggler sandboxing + C++ patches in Firefox |
| **Humanize** | C++ mouse movement, per-character typing |
| **Presets** | Real fingerprint presets (312 fingerprints from real Firefox traffic) |
| **Addons** | uBlock Origin bundled, custom addon support |
| **Debloat** | Stripped Mozilla services, telemetry removed |
| **Headless** | Patched; also has virtual display fallback |
| **Proxy** | Auto-calc timezone/locale from proxy IP |
| **GeoIP** | `pip install camoufox[geoip]` |

**Key Differentiator:** Camoufox uses **Juggler** (Playwright for Firefox) which is a **custom automation protocol** built specifically for Firefox. Juggler is a distinct module, not part of Firefox core. Camoufox sandboxes it completely — Playwright's page agent code runs in an isolated scope that the page **cannot see**. This means:
- No `navigator.webdriver` leak (patched in C++)
- No CDP detection (Juggler != CDP)
- No Playwright injection traces visible to page JS
- All page automation is invisible

### CloakBrowser (Chromium Fork)

```
cloakbrowser (Python package) → Playwright Chromium → CDP → CloakBrowser Binary (71-patched Chromium)
```

| Aspect | Detail |
|--------|--------|
| **Engine** | Chromium (free: v146, Pro: v150) |
| **Protocol** | **CDP** (Chrome DevTools Protocol) |
| **Stars** | ~3K (growing fast) |
| **Dev Status** | ✅ Active — multiple releases per week |
| **Last push** | 2026-07-23 (today!) |
| **Python** | `cloakbrowser` package v0.5.1 |
| **Fingerprint method** | 71 C++ patches in Chromium source + per-seed hardware identity |
| **Stealth via** | C++ patches everywhere (canvas, WebGL, GPU, fonts, network, WebRTC, CDP signals) |
| **Humanize** | Bézier curves, per-character typing, realistic scroll |
| **Presets** | Per-seed consistent hardware identity (screen, GPU, RAM, CPU) |
| **Addons** | Chrome extension support via `extension_paths` |
| **Debloat** | Minimal — focused on stealth, not debloat |
| **Headless** | Patched; headless viewport now mirrors real screen |
| **Proxy** | SOCKS5, HTTP with inline auth, geoip auto-detect |
| **GeoIP** | `pip install cloakbrowser[geoip]` |
| **reCAPTCHA v3** | 0.9 (Pro) — server verified |
| **Turnstile** | PASS (Pro build) |
| **Test results** | 30+ detection sites tested, all pass |
| **Docker** | `cloakhq/cloakbrowser` (100K+ pulls) |

**Key Differentiator:** CloakBrowser patches Chromium at the **C++ source level** — 71 patches covering every known detection vector. It doesn't sandbox CDP (like Camoufox sandboxes Juggler), but instead patches the CDP signals themselves so CDP is invisible. The Pro build (v150) passes ALL detection tests including reCAPTCHA v3 scoring 0.9 (human level).

---

## 3. X/Twitter-Specific Analysis

### What X.com's Anti-Bot Checks

X.com uses a combination of:
1. **TLS fingerprint** — Checks ja3/ja4/akamai fingerprint of the connection
2. **Browser fingerprint** — Canvas, WebGL, Audio, Fonts, Screen, GPU
3. **Automation detection** — `navigator.webdriver`, CDP presence, Playwright traces
4. **Behavioral** — Mouse movement, typing patterns, scroll
5. **IP reputation** — Datacenter IPs get harder challenges
6. **Cookie/session** — Fresh sessions have lower trust

### Which Tool Has the Advantage?

| Detection Vector | Camoufox (Firefox) | CloakBrowser (Chromium) | Winner |
|-----------------|-------------------|------------------------|--------|
| **TLS fingerprint** | Firefox TLS (different from Chrome) | Chrome TLS (identical to real Chrome) | **CloakBrowser** — Chrome TLS matches what most X users have |
| **Canvas/WebGL** | Patched at C++ | Patched at C++ | **Tie** |
| **Automation detection** | Juggler sandboxed — Playwright invisible | CDP signals patched at C++ level | **Camoufox** — Juggler sandboxing is genuinely invisible |
| **reCAPTCHA v3** | Moderate (Firefox fingerprint) | 0.9 score (Pro build, human level) | **CloakBrowser** — verified score |
| **Turnstile** | Moderate | PASS (Pro) | **CloakBrowser** |
| **Headless detection** | Virtual display fallback | C++ patches remove headless leaks | **Tie** |
| **Humanize** | C++ mouse movement | Bézier curves + keyboard timing | **Tie** |
| **X.com optimization** | Firefox may trigger "browser not supported" | Chrome is X.com's primary target | **CloakBrowser** |
| **Session persistence** | Cookie isolation per profile | `launch_persistent_context()` | **Tie** |
| **Browser diversity** | Firefox less common = harder to fingerprint | Chrome more common = blends in better | **Camoufox** (for diversity) |

### The Juggler Advantage (Camoufox)

This is Camoufox's unique selling point: **Juggler is not CDP.**

X.com can detect CDP by checking for:
```javascript
// CDP detection — checks if Chrome's automation protocol is active
if (window.navigator.webdriver) { /* flagged */ }
// CDP leaves traces in the JS engine
if (someCDPOnlyFeature) { /* flagged */ }
```

Camoufox bypasses this entirely because:
1. Juggler is a **completely different protocol** — not CDP, not detectable via CDP checks
2. Juggler's page agent runs in an **isolated scope** — the page cannot see Playwright's code at all
3. Firefox doesn't have `window.chrome` object, so that detection vector is irrelevant

### The Chrome Compatibility Advantage (CloakBrowser)

CloakBrowser's advantage for X.com:
1. **X.com is built for Chrome** — all features tested on Chrome first
2. **Chrome has 65%+ browser share** — X.com's anti-bot expects Chrome fingerprints
3. **CloakBrowser's 71 patches** are comprehensive and actively maintained
4. **Proven results** — 30+ detection sites verified PASS, reCAPTCHA v3 at 0.9

---

## 4. Operational Comparison for Nabu

| Factor | Camoufox | CloakBrowser |
|--------|----------|-------------|
| **Already installed (package)** | ✅ v0.5.4 | ✅ v0.5.1 |
| **Binary already fetched** | ❌ Needs `camoufox fetch` (~200MB) | ✅ Already cached |
| **Launch tested** | ❌ Not yet | ✅ PASSED |
| **Current state** | Package ready, binary missing | ✅ Everything ready to use |
| **Free tier** | Firefox v152 (latest) | Chromium v146 (older) |
| **Pro needed for best results?** | No — latest Firefox is free | Yes — v150 Pro is better, v146 free works but older |
| **Docker support** | Build system only (not pre-built) | `cloakhq/cloakbrowser` (100K+ pulls) |
| **Maintenance** | Sporadic (year gap, now active) | Active (releases every few days) |
| **Windows support** | ✅ | ✅ (tested working) |
| **Python API** | Sync + Async | Sync + Async |
| **Complexity** | Moderate | Simple (drop-in Playwright) |

---

## 5. Recommendation

### For the Immediate Test (Today)

**Use CloakBrowser.** It's:
- Already downloaded and tested working on this machine
- Chromium-based (X.com's primary target)
- Simpler API (true drop-in Playwright replacement)
- No additional download needed

```
pip install cloakbrowser
# Already done. Binary already cached. Launch already tested.
```

### For Production Nabu Integration

**Use Camoufox** alongside CloakBrowser for **browser diversity**:

```python
# Strategy — rotate between two stealth browsers to avoid fingerprint correlation
# 1. Primary: CloakBrowser (Chrome) for compatibility
# 2. Secondary: Camoufox (Firefox) for diversity
# 3. Rotate IP + browser per session
```

Or keep it simple with **just CloakBrowser Pro** ($ for concurrent sessions, latest Chromium 150, proven 0.9 reCAPTCHA score).

### Decision Matrix

| Priority | Choice | Reason |
|----------|--------|--------|
| **Fastest to test today** | CloakBrowser | Already working, no download needed |
| **Best detection evasion** | CloakBrowser Pro | 71 patches, 0.9 reCAPTCHA, Turnstile PASS |
| **Best automation invisibility** | Camoufox | Juggler sandboxing is unique |
| **Best for production at scale** | Both (rotate) | Browser diversity prevents fingerprint correlation |
| **Best for Windows** | CloakBrowser | Tested working on this machine |

---

## 6. Next Steps

1. ✅ ~~Install/cloakbrowser~~ — already done, tested working
2. ⏳ Fetch Camoufox binary (ran but timed out; retry with longer timeout)
3. ⏳ Test CloakBrowser → X.com (can we load X.com without getting blocked?)
4. ⏳ Test Camoufox → X.com (Firefox variant)
5. ⏳ Extract bearer token + CSRF from X.com page
6. ⏳ Test GraphQL call to search for "airdrop"
7. ⏳ If GraphQL fails without login → test login flow
8. ⏳ Integrate into Nabu runtime
