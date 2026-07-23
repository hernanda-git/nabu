#!/usr/bin/env python3
"""Debug X.com login page structure."""
import time, json
from cloakbrowser import launch

browser = launch(headless=False, humanize=True, args=["--disable-gpu"])
page = browser.new_page()
page.set_default_timeout(15000)

page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=30000)
time.sleep(6)

# Dump ALL interactive elements
result = page.evaluate("""
() => {
    const all = document.querySelectorAll('button, a, input, [role="button"], [tabindex]');
    const data = [];
    for (const el of all) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            data.push({
                tag: el.tagName,
                type: el.type || '',
                text: (el.innerText || el.value || '').substring(0, 60),
                id: el.id,
                'data-testid': el.getAttribute('data-testid'),
                name: el.getAttribute('name') || '',
                placeholder: el.getAttribute('placeholder') || '',
                class: (el.className || '').substring(0, 40),
                visible: rect.width > 0 && rect.height > 0,
                rect: `${Math.round(rect.x)},${Math.round(rect.y)} ${Math.round(rect.width)}x${Math.round(rect.height)}`
            });
        }
    }
    return data;
}
""")

for el in result:
    if el['text'] or el['data-testid'] or el['type'] == 'text' or el['type'] == 'password':
        print(f"  {el['tag']:6s} type={el['type']:10s} id={el['id']:30s} testid={str(el['data-testid']):30s} text=\"{el['text']}\"", flush=True)

browser.close()
print("Done!", flush=True)
