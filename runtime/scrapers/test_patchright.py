#!/usr/bin/env python3
"""Test Patchright against X.com login."""
import sys, time

print("[1] Importing patchright...", flush=True)
from patchright.sync_api import sync_playwright
print("[2] Import OK", flush=True)

with sync_playwright() as pw:
    print("[3] Launching Chromium...", flush=True)
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("[4] Loading X.com login...", flush=True)
    resp = page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=30000)
    print(f"  Status: {resp.status}", flush=True)
    time.sleep(5)
    print(f"  URL: {page.url}", flush=True)
    print(f"  Title: {page.title()[:80]}", flush=True)
    
    # Check for input fields
    username = page.evaluate("() => { const i = document.querySelector('input[name=username_or_email]'); return i ? 'OK' : 'MISSING'; }")
    print(f"  Username input: {username}", flush=True)
    
    ct0 = page.evaluate("() => { const m = document.cookie.split('; ').find(c => c.startsWith('ct0=')); return m ? m.split('=')[1][:20] : 'NONE'; }")
    print(f"  ct0: {ct0}", flush=True)
    
    browser.close()
print("[5] DONE", flush=True)
