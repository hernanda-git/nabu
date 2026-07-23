#!/usr/bin/env python3
"""
Test Patchright + channel="chrome" against X.com.
Uses user's installed Chrome (no binary download needed).
"""
import sys, time

sys.stdout.reconfigure(line_buffering=True)

print("[1] Importing patchright...", flush=True)
from patchright.sync_api import sync_playwright

print("[2] Launching with channel='chrome'...", flush=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=True,
        channel="chrome",
        args=["--disable-gpu"],
    )
    page = browser.new_page()
    
    print("[3] Loading X.com login...", flush=True)
    resp = page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=30000)
    print(f"  Status: {resp.status}", flush=True)
    time.sleep(4)
    print(f"  URL: {page.url}", flush=True)
    print(f"  Title: {page.title()[:80]}", flush=True)
    
    # Check for input fields
    username = page.evaluate("() => { const i = document.querySelector('input[name=username_or_email]'); return i ? 'OK' : 'MISSING'; }")
    print(f"  Username input: {username}", flush=True)
    
    # Check for ct0
    ct0 = page.evaluate("() => { const m = document.cookie.split('; ').find(c => c.startsWith('ct0=')); return m ? m.split('=')[1].substring(0,20) : 'NONE'; }")
    print(f"  ct0: {ct0}", flush=True)
    
    # Test fill
    print("[4] Filling email...", flush=True)
    page.fill("input[name='username_or_email']", "test@example.com")
    time.sleep(1)
    print("  Filled", flush=True)
    
    # Check for password field
    pw_visible = page.evaluate("() => { const p = document.querySelector('input[type=password]'); return p ? 'visible' : 'hidden'; }")
    print(f"  Password field: {pw_visible}", flush=True)
    
    # Navigate to a public profile
    print("[5] Loading DefiLlama profile...", flush=True)
    page.goto("https://x.com/DefiLlama", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    print(f"  URL: {page.url}", flush=True)
    print(f"  Title: {page.title()[:80]}", flush=True)
    
    # Check for tweet articles
    tweets = page.evaluate("() => { const t = document.querySelectorAll('article[data-testid=tweet]'); return t.length; }")
    print(f"  Tweet articles visible: {tweets}", flush=True)
    
    if tweets > 0:
        print("  ✅ X.com renders perfectly with Chrome!", flush=True)
    else:
        print("  ⚠️ No tweets visible, checking page state...", flush=True)
        body = page.evaluate("() => document.body.innerText.substring(0, 300)")
        print(f"  Body: {body}", flush=True)
    
    browser.close()
print("[6] DONE", flush=True)
