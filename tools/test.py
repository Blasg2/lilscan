# /// script
# dependencies = ["playwright", "pillow"]
# ///
"""Self-check: feeds Chromium a fake camera showing cover.png and checks the target is found and the video plays.
uv run tools/test.py [screenshot.png]"""
import functools, http.server, io, os, subprocess, sys, tempfile, threading
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CHROME = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright/chromium-1248/chrome-win64/chrome.exe"
shot = sys.argv[1] if len(sys.argv) > 1 else None

# A 640x480 "camera" of the cover on a grey table; Chromium loops the file.
cam = Path(tempfile.mkdtemp()) / "cam.y4m"
subprocess.run(["ffmpeg", "-v", "error", "-loop", "1", "-i", str(ROOT / "cover.png"), "-t", "2", "-r", "10",
                "-vf", "scale=-2:400,pad=640:480:(ow-iw)/2:(oh-ih)/2:gray,format=yuv420p", str(cam)], check=True)

server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
threading.Thread(target=server.serve_forever, daemon=True).start()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME if CHROME.exists() else None, args=[
        "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
        f"--use-file-for-fake-video-capture={cam}", "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"])
    page = browser.new_page(viewport={"width": 480, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("document.addEventListener('targetFound', () => window.found = true)")
    page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
    page.wait_for_function("window.found === true", timeout=60000)
    page.wait_for_function("document.getElementById('vid').currentTime > 0.5", timeout=15000)
    png = page.screenshot(path=shot)
    browser.close()
server.shutdown()

assert not errors, f"page errors: {errors}"
# The top edge of the screen shows the fake camera's grey padding, unless something covers the camera.
r, g, b = Image.open(io.BytesIO(png)).convert("RGB").getpixel((240, 10))
assert min(r, g, b) > 80, f"camera feed not visible (top pixel is {r},{g},{b})"
print("OK: camera visible, target found, video playing")
