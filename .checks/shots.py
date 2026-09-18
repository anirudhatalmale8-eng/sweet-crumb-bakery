"""Screenshot + console/layout checks for the Sweet Crumb site."""
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8760/"
OUT = "/var/lib/freelancer/projects/60/.checks"

problems = []

with sync_playwright() as p:
    browser = p.chromium.launch()

    for name, w, h in [("desktop", 1440, 900), ("mobile", 390, 844)]:
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
        page = ctx.new_page()
        msgs, failed = [], []
        page.on("console", lambda m: msgs.append((m.type, m.text)))
        page.on("pageerror", lambda e: msgs.append(("pageerror", str(e))))
        page.on("requestfailed", lambda r: failed.append(r.url))

        page.goto(URL, wait_until="load")
        page.wait_for_timeout(500)
        # trigger every reveal
        page.evaluate("""() => new Promise(res => {
            let y = 0;
            const step = () => {
                y += window.innerHeight * 0.4;
                window.scrollTo({top: y, behavior: 'instant'});
                if (y < document.body.scrollHeight) setTimeout(step, 120);
                else { window.scrollTo({top: 0, behavior: 'instant'}); setTimeout(res, 500); }
            };
            step();
        })""")
        page.wait_for_timeout(1400)
        # let every lazy image finish before we screenshot or assert
        page.evaluate("""() => Promise.all([...document.images]
            .map(i => i.complete ? null : i.decode().catch(() => null)))""")
        page.wait_for_timeout(400)

        page.screenshot(path=f"{OUT}/{name}-full.png", full_page=True)
        page.screenshot(path=f"{OUT}/{name}-hero.png")

        # horizontal overflow?
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        if overflow > 1:
            problems.append(f"{name}: horizontal overflow of {overflow}px")

        # any element hidden by a stuck reveal?
        stuck = page.evaluate("() => document.querySelectorAll('.r:not(.in)').length")
        if stuck:
            problems.append(f"{name}: {stuck} reveal element(s) never became visible")

        # fonts actually loaded?
        fam = page.evaluate("""() => {
            const h1 = getComputedStyle(document.querySelector('.hero__h1')).fontFamily;
            const ok = document.fonts.check('600 16px Fraunces') && document.fonts.check('400 16px Karla');
            return {h1, ok};
        }""")
        if not fam["ok"]:
            problems.append(f"{name}: webfonts not loaded ({fam['h1']})")

        # images resolved?
        broken = page.evaluate(
            "() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.currentSrc || i.src)")
        if broken:
            problems.append(f"{name}: broken images {broken}")

        # open-now chip rendered something sensible
        chip = page.text_content("#openLabel")
        if chip not in ("Open now", "Closed now"):
            problems.append(f"{name}: open chip says {chip!r}")

        today = page.evaluate("() => document.querySelectorAll('#hours tr.is-today').length")
        if today != 1:
            problems.append(f"{name}: {today} rows marked as today (expected 1)")

        # WCAG AA contrast on every visible run of text
        low = page.evaluate("""() => {
            const px = s => parseFloat(s) || 0;
            const parse = c => {
                const m = c.match(/[\\d.]+/g).map(Number);
                return m.length === 3 ? [...m, 1] : m;
            };
            const over = (fg, bg) => fg[3] >= 1 ? fg
                : [0,1,2].map(i => fg[i] * fg[3] + bg[i] * (1 - fg[3])).concat(1);
            const lum = c => {
                const f = c.slice(0,3).map(v => {
                    v /= 255;
                    return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4);
                });
                return 0.2126*f[0] + 0.7152*f[1] + 0.0722*f[2];
            };
            const ratio = (a, b) => {
                const [hi, lo] = [lum(a), lum(b)].sort((x,y) => y-x);
                return (hi + 0.05) / (lo + 0.05);
            };
            const bgOf = el => {
                for (let n = el; n; n = n.parentElement) {
                    const c = parse(getComputedStyle(n).backgroundColor);
                    if (c[3] > 0.95) return c;
                }
                return [255,255,255,1];
            };
            const out = [];
            document.querySelectorAll('body *').forEach(el => {
                const hasText = [...el.childNodes].some(
                    n => n.nodeType === 3 && n.textContent.trim().length > 1);
                if (!hasText) return;
                const cs = getComputedStyle(el);
                if (cs.visibility === 'hidden' || cs.display === 'none') return;
                if (px(cs.opacity) < 0.95) return;          // mid-animation
                const r = el.getBoundingClientRect();
                if (!r.width || !r.height) return;
                const bg = bgOf(el);
                const fg = over(parse(cs.color), bg);
                const size = px(cs.fontSize), weight = parseInt(cs.fontWeight) || 400;
                const large = size >= 24 || (size >= 18.66 && weight >= 700);
                const need = large ? 3 : 4.5;
                const got = ratio(fg, bg);
                if (got < need) out.push({
                    sel: el.className || el.tagName,
                    text: el.textContent.trim().slice(0, 32),
                    size: Math.round(size), weight,
                    got: +got.toFixed(2), need
                });
            });
            return out;
        }""")
        if low:
            problems.append(f"{name}: low contrast on {low}")

        # tap-target check on mobile
        if name == "mobile":
            small = page.evaluate("""() => [...document.querySelectorAll('a.btn, .nav a, .fab')]
                .filter(el => el.offsetParent !== null)
                .map(el => { const r = el.getBoundingClientRect(); return {t: el.textContent.trim().slice(0,22), h: Math.round(r.height)}; })
                .filter(x => x.h < 40)""")
            if small:
                problems.append(f"mobile: small tap targets {small}")
            # mobile nav opens
            page.click("#burger")
            page.wait_for_timeout(450)
            if not page.is_visible(".nav.is-open a[href='#menu']"):
                problems.append("mobile: nav did not open")
            page.screenshot(path=f"{OUT}/mobile-nav.png")

        errs = [m for m in msgs if m[0] in ("error", "pageerror")]
        if errs:
            problems.append(f"{name}: console {errs}")
        bad = [u for u in failed if "fonts.g" not in u]
        if bad:
            problems.append(f"{name}: failed requests {bad}")

        print(f"{name}: shot ok, chip={chip!r}, h1 font={fam['h1'].split(',')[0]}")
        ctx.close()

    # section shots at desktop width for review
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()
    page.goto(URL, wait_until="load")
    page.evaluate("() => document.querySelectorAll('.r').forEach(e => e.classList.add('in'))")
    page.wait_for_timeout(900)
    for sel, out in [("#bakery", "sec-bakery"), ("#menu", "sec-menu"), (".oven", "sec-oven"), ("#visit", "sec-visit"), (".foot", "sec-foot")]:
        page.locator(sel).screenshot(path=f"{OUT}/{out}.png")
    ctx.close()
    browser.close()

print("\n--- RESULT ---")
if problems:
    for pr in problems:
        print("FAIL:", pr)
    sys.exit(1)
print("all checks passed")
