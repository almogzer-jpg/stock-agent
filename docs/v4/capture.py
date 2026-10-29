# -*- coding: utf-8 -*-
"""Reproducible screenshots of the running app (headless Chrome via DevTools).

Used for the V4 audit (before) and release review (after). Requires a local
app on :8501 and Chrome. No extra packages: talks CDP over `websockets`.

    python docs/v4/capture.py audit          → docs/v4/audit/*.png
"""
import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333
BASE = "http://localhost:8501"
HERE = os.path.dirname(os.path.abspath(__file__))

DESKTOP = {"width": 1280, "height": 2200, "mobile": False, "scale": 1}
PHONE = {"width": 375, "height": 2400, "mobile": True, "scale": 2}

# (file name, url query, viewport, nav label to click or None[, text typed into the search box])
SHOTS = [
    # Professional view — desktop
    ("pro-desktop-01-home", "?m=0&mode=pro", DESKTOP, None),
    ("pro-desktop-02-company-analysis", "?m=0&mode=pro", DESKTOP, "ניתוח חברה"),
    ("pro-desktop-03-watchlist", "?m=0&mode=pro", DESKTOP, "המעקב שלי"),
    ("pro-desktop-04-opportunities", "?m=0&mode=pro", DESKTOP, "הזדמנויות"),
    ("pro-desktop-05-sectors", "?m=0&mode=pro", DESKTOP, "סקטורים"),
    ("pro-desktop-06-alerts", "?m=0&mode=pro", DESKTOP, "התראות"),
    ("pro-desktop-07-market-intelligence", "?m=0&mode=pro", DESKTOP, "אינטליגנציית שוק"),
    ("pro-desktop-08-settings", "?m=0&mode=pro", DESKTOP, "הגדרות"),
    ("pro-desktop-09-diagnostics", "?m=0&mode=pro&diag=1", DESKTOP, None),
    # Professional view — phone
    ("pro-phone-01-home", "?m=1&mode=pro", PHONE, None),
    ("pro-phone-02-analysis", "?m=1&mode=pro", PHONE, "ניתוח"),
    ("pro-phone-03-opportunities", "?m=1&mode=pro", PHONE, "הזדמנויות"),
    ("pro-phone-04-sectors", "?m=1&mode=pro", PHONE, "סקטורים"),
    ("pro-phone-05-alerts", "?m=1&mode=pro", PHONE, "התראות"),
    # Simple view — desktop
    ("simple-desktop-01-today", "?m=0", DESKTOP, None),
    ("simple-desktop-02-check-empty", "?m=0", DESKTOP, "בדיקת מניה"),
    ("simple-desktop-02b-check-aapl", "?m=0", DESKTOP, "בדיקת מניה", "אפל"),
    ("simple-desktop-03-ideas", "?m=0", DESKTOP, "רעיונות"),
    ("simple-desktop-04-my-stocks", "?m=0", DESKTOP, "המניות שלי"),
    ("simple-desktop-05-glossary", "?m=0", DESKTOP, "מילון"),
    # Simple view — phone
    ("simple-phone-01-today", "?m=1", PHONE, None),
    ("simple-phone-02-check-empty", "?m=1", PHONE, "בדיקת מניה"),
    ("simple-phone-02b-check-lly", "?m=1", PHONE, "בדיקת מניה", "lilly"),
    ("simple-phone-03-ideas", "?m=1", PHONE, "רעיונות"),
    ("simple-phone-04-glossary", "?m=1", PHONE, "מילון"),
]

CLICK_JS = """
(() => {
  const want = %s;
  const labels = [...document.querySelectorAll('label, button')];
  const el = labels.find(l => (l.innerText || '').trim().replace(/^\\S+\\s/, '') === want
                           || (l.innerText || '').trim().endsWith(want));
  if (!el) return 'not-found';
  el.click(); return 'clicked';
})()
"""


async def _cdp(ws, _id=[0]):
    async def call(method, params=None):
        _id[0] += 1
        mid = _id[0]
        await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == mid:
                return msg.get("result", {})
    return call


async def _wait_ready(call, timeout=40):
    """Ready = Streamlit finished running (no status widget) and main has content."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = await call("Runtime.evaluate", {"expression":
            "(() => { const m = document.querySelector('[data-testid=\"stMain\"]');"
            " const running = !!document.querySelector('[data-testid=\"stStatusWidget\"] svg');"
            " return (m && m.innerText.length > 200 && !running) ? 'ok' : 'wait'; })()",
            "returnByValue": True})
        if r.get("result", {}).get("value") == "ok":
            await asyncio.sleep(1.5)
            return time.time() - t0
        await asyncio.sleep(0.5)
    return None


async def shoot(name, query, vp, nav, outdir, typed=None):
    tgt = json.loads(urllib.request.urlopen(
        urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?about:blank", method="PUT")).read())
    async with websockets.connect(tgt["webSocketDebuggerUrl"], max_size=50_000_000) as ws:
        call = await _cdp(ws)
        await call("Page.enable")
        await call("Emulation.setDeviceMetricsOverride", {
            "width": vp["width"], "height": vp["height"], "deviceScaleFactor": vp["scale"],
            "mobile": vp["mobile"]})
        if vp["mobile"]:
            await call("Emulation.setTouchEmulationEnabled", {"enabled": True})
        t0 = time.time()
        await call("Page.navigate", {"url": BASE + "/" + query})
        load = await _wait_ready(call)
        if nav:
            await call("Runtime.evaluate", {"expression": CLICK_JS % json.dumps(nav), "returnByValue": True})
            await asyncio.sleep(1.0)
            await _wait_ready(call)
        if typed:
            await call("Runtime.evaluate", {"expression":
                "document.querySelector('[data-testid=\"stMain\"] input[type=text]').focus()"})
            await call("Input.insertText", {"text": typed})
            await call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter",
                                                  "windowsVirtualKeyCode": 13, "text": chr(13)})
            await call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter",
                                                  "windowsVirtualKeyCode": 13})
            await asyncio.sleep(2.0)
            await _wait_ready(call, timeout=60)
            await asyncio.sleep(3.0)
        shot = await call("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(outdir, name + ".png"), "wb") as fh:
            fh.write(base64.b64decode(shot["data"]))
    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/close/{tgt['id']}")
    return {"name": name, "first_render_s": round(load, 1) if load else None,
            "total_s": round(time.time() - t0, 1)}


async def main(kind):
    outdir = os.path.join(HERE, kind)
    os.makedirs(outdir, exist_ok=True)
    prof = tempfile.mkdtemp(prefix="sa-chrome-")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
                             f"--user-data-dir={prof}", "--no-first-run", "--hide-scrollbars",
                             "--lang=he-IL", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")
                break
            except Exception:
                time.sleep(0.3)
        only = set(sys.argv[2:])
        results = []
        for spec in SHOTS:
            name, q, vp, nav = spec[:4]
            if only and name not in only:
                continue
            r = await shoot(name, q, vp, nav, outdir, spec[4] if len(spec) > 4 else None)
            print(r, flush=True)
            results.append(r)
        with open(os.path.join(outdir, "timings.json"), "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=1)
    finally:
        proc.terminate()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "audit"))
