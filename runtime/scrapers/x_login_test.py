#!/usr/bin/env python3
"""
CloakBrowser X.com Login Test
Logs in once, saves cookies for reuse.
"""
import time, json, os, sys
from cloakbrowser import launch

EMAIL = "balatosai@gmail.com"
PASS  = "h3rNaNd415272195%"
PROFILE = "C:/Users/it26/.cloakbrowser/x-profile"
os.makedirs(PROFILE, exist_ok=True)

step = 1
def log(msg):
    global step
    print(f"[{step}] {msg}", flush=True)
    step += 1

log("Launching CloakBrowser (headed, humanize)")
browser = launch(
    headless=False,
    humanize=True,
    human_preset="careful",
    args=["--disable-gpu", "--no-sandbox"],
)
page = browser.new_page()
page.set_default_timeout(20000)

log("Loading X.com login")
page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=30000)
time.sleep(4)
log(f"URL: {page.url}")

log("Filling email")
page.fill("input[name='username_or_email']", EMAIL)
time.sleep(2)

log("Waiting for password field")
try:
    page.wait_for_selector("input[type='password']", timeout=10000)
    log("Password field appeared — email accepted")
except:
    log("Password field did not appear, checking page state")
    body = page.evaluate("() => document.body.innerText.substring(0, 300)")
    log(f"Body: {body}")
    # Try clicking any "Next"/"Continue" button if password didn't auto-appear
    try:
        page.locator("button:has-text('Next'), button:has-text('Continue')").first.click(timeout=3000)
        time.sleep(3)
    except:
        pass

log("Filling password")
page.fill("input[type='password']", PASS)
time.sleep(2)

log("Clicking Log in")
try:
    # Try clicking login button
    page.locator("button:has-text('Log in'), button[data-testid*='Login']").first.click(timeout=5000)
except:
    log("Button click failed, trying evaluate fallback")
    page.evaluate("() => { document.querySelector('button[type=submit]')?.click() }")

time.sleep(5)
log(f"Final URL: {page.url}")

# Check login result
ct0 = page.evaluate("""
    () => {
        const m = document.cookie.split('; ').find(c => c.startsWith('ct0='));
        return m ? m.split('=')[1].substring(0, 30) : 'NONE';
    }
""")
log(f"ct0: {ct0}")

if ct0 != "NONE":
    log("✅ LOGIN SUCCESSFUL!")
    # Save storage state
    state_path = os.path.join(PROFILE, "state.json")
    page.context.storage_state(path=state_path)
    log(f"State saved to {state_path}")
    
    # Try GraphQL search
    log("Testing GraphQL search...")
    result = page.evaluate("""
        async () => {
            const resp = await fetch('https://x.com/i/api/graphql/39s5YHfJEYwR7LFWZ0nWCA/SearchTimeline?variables=' + 
                encodeURIComponent(JSON.stringify({rawQuery: 'airdrop', count: 5, product: 'Top'})),
                {headers: {'content-type': 'application/json'}}
            );
            return {status: resp.status, ok: resp.ok};
        }
    """)
    log(f"GraphQL test: {result}")
else:
    body = page.evaluate("() => document.body.innerText.substring(0, 500)")
    log(f"Login failed. Body: {body}")
    log("Check the headed browser window for verification challenges")

time.sleep(5)
browser.close()
log("Done")
