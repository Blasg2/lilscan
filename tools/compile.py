# /// script
# dependencies = ["playwright"]
# ///
"""Rebuilds targets.mind from cover.png. Run from anywhere: uv run tools/compile.py"""
import base64, functools, http.server, os, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CHROME = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright/chromium-1248/chrome-win64/chrome.exe"

server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
threading.Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME if CHROME.exists() else None)
    page = browser.new_page()
    page.on("console", lambda m: print("page:", m.text))
    page.goto(f"http://127.0.0.1:{server.server_port}/tools/compile.html")
    data = base64.b64decode(page.evaluate("compileCover()", ))
    browser.close()
server.shutdown()

assert len(data) > 1000, "compiler returned almost nothing"
(ROOT / "targets.mind").write_bytes(data)
print(f"targets.mind written, {len(data)} bytes")
