"""Record a short walkthrough of the site: desktop scroll, then the phone layout."""
import os
import shutil
from playwright.sync_api import sync_playwright

URL = "http://localhost:8760/"
OUT = "/var/lib/freelancer/projects/60/.checks"
TMP = f"{OUT}/_vid"
os.makedirs(TMP, exist_ok=True)


def smooth_scroll(page, seconds=9.0):
    """Ease down the page and back to the top, at a watchable speed."""
    page.evaluate(
        """(secs) => new Promise(res => {
            const max = document.body.scrollHeight - window.innerHeight;
            const t0 = performance.now();
            const dur = secs * 1000;
            const ease = t => t < .5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2) / 2;
            const step = now => {
                const t = Math.min(1, (now - t0) / dur);
                window.scrollTo({top: max * ease(t), behavior: 'instant'});
                if (t < 1) requestAnimationFrame(step); else res();
            };
            requestAnimationFrame(step);
        })""",
        seconds,
    )


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ── desktop pass ────────────────────────────────────────
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 768},
        record_video_dir=TMP,
        record_video_size={"width": 1366, "height": 768},
    )
    page = ctx.new_page()
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(2200)          # let the hero animate in
    smooth_scroll(page, 11.0)
    page.wait_for_timeout(700)
    page.hover(".card")                  # show a menu card lift
    page.wait_for_timeout(900)
    page.evaluate("() => window.scrollTo({top: 0, behavior: 'instant'})")
    page.wait_for_timeout(800)
    ctx.close()
    desktop_vid = page.video.path()

    # ── phone pass ──────────────────────────────────────────
    ctx2 = browser.new_context(
        viewport={"width": 390, "height": 844},
        record_video_dir=TMP,
        record_video_size={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
    )
    page2 = ctx2.new_page()
    page2.goto(URL, wait_until="load")
    page2.wait_for_timeout(1800)
    page2.click("#burger")               # open the mobile menu
    page2.wait_for_timeout(1400)
    page2.click("#burger")
    page2.wait_for_timeout(600)
    smooth_scroll(page2, 9.0)
    page2.wait_for_timeout(800)
    ctx2.close()
    mobile_vid = page2.video.path()

    browser.close()

shutil.move(desktop_vid, f"{OUT}/walkthrough-desktop.webm")
shutil.move(mobile_vid, f"{OUT}/walkthrough-mobile.webm")
print("desktop:", os.path.getsize(f"{OUT}/walkthrough-desktop.webm"), "bytes")
print("mobile: ", os.path.getsize(f"{OUT}/walkthrough-mobile.webm"), "bytes")
