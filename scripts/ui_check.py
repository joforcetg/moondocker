#!/usr/bin/env python3
"""UI smoke check for moondocker — optimized for a tight edit/re-run loop.

Boots the app once (or attaches to a running one via --url), drives a headless
Chromium across phone→desktop widths, and asserts the four things the redesign
was about: responsive layout, scroll-to-loaded-myth, font rendering, theme.

    .venv/bin/python scripts/ui_check.py                       # boot + check
    .venv/bin/python scripts/ui_check.py --url http://127.0.0.1:7432   # reuse a
                                                                 # running server

Screenshots land in ./ui-shots/. Exit code is 0 only if every check passes.

# ponytail: one file, stdlib + the playwright already in the venv. No
# pytest-playwright, no fixtures, no baseline images — eyeball the shots.
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "ui-shots"
PORT = 7432
VIEWPORTS = [
    ("phone-360", 360, 780),
    ("phone-390", 390, 844),
    ("phone-480", 480, 900),
    ("tablet-768", 768, 1024),
    ("desktop-1280", 1280, 900),
]

results = []  # (ok: bool, label: str)


def check(ok, label):
    results.append((bool(ok), label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")


def wait_health(url, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + "/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def boot_server():
    env = dict(os.environ)
    env["SKYFIELD_DATA"] = str(ROOT / "skyfield-data")
    env["LAT"] = "38.7223"   # Lisbon — deterministic fallback, no geolocation prompt
    env["LON"] = "-9.1393"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return proc


def run_checks(url):
    SHOTS.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        # deny geolocation -> app falls back to LAT/LON env (window.__FALLBACK__)
        ctx = browser.new_context(permissions=[])
        page = ctx.new_page()

        # --- responsive layout across widths ---
        for label, w, h in VIEWPORTS:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(url, wait_until="networkidle")
            page.wait_for_selector(".const-card", timeout=20000)
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(SHOTS / f"{label}.png"), full_page=True)

            overflow = page.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            check(overflow <= 1, f"{label}: no horizontal overflow ({overflow}px)")

            cols = page.evaluate(
                "getComputedStyle(document.getElementById('panels')).gridTemplateColumns"
            )
            n = len([c for c in cols.split() if c])
            want = 2 if w >= 900 else 1
            check(n == want, f"{label}: panels grid {n} col (want {want})")

        # --- fonts: Cinzel resolved + smoothing applied ---
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector(".const-card", timeout=20000)
        page.evaluate("document.fonts.ready")
        cinzel = page.evaluate("document.fonts.check('700 1rem \"Grimoire Title\"')")
        check(cinzel, "Cinzel title font loaded")
        body_font = page.evaluate("document.fonts.check('1rem \"Grimoire Body\"')")
        check(body_font, "EB Garamond body font loaded")
        smoothing = page.evaluate(
            "getComputedStyle(document.body).webkitFontSmoothing"
        )
        check(smoothing == "antialiased", f"font-smoothing antialiased ({smoothing})")
        # readability: the wordmark must resolve to Cinzel, not the old blackletter
        # or a serif fallback
        wm_font = page.evaluate(
            "getComputedStyle(document.querySelector('.wordmark')).fontFamily"
        )
        check("Grimoire Title" in wm_font and "UnifrakturCook" not in wm_font,
              f"wordmark uses Cinzel, blackletter gone ({wm_font.split(',')[0]})")

        # --- theme richness ---
        blood = page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--blood').trim()"
        )
        check(bool(blood), f"--blood accent set ({blood})")
        overlay = page.evaluate(
            "getComputedStyle(document.body, '::after').backgroundImage"
        )
        check("linear-gradient" in overlay and "svg" in overlay,
              "scanline + grain overlay present")
        panel_bg = page.evaluate(
            "getComputedStyle(document.querySelector('.panel')).backgroundImage"
        )
        check("gradient" in panel_bg, "panel has textured background")
        panel_border = page.evaluate(
            "getComputedStyle(document.querySelector('.panel')).borderTopWidth"
        )
        check(panel_border not in ("0px", ""), f"panels have a frame ({panel_border})")
        # candle flicker keeps the page alive instead of static
        flicker = page.evaluate(
            "getComputedStyle(document.body, '::before').animationName"
        )
        check(flicker and flicker != "none", f"candle-flicker animation on ({flicker})")
        # corner rune sigil actually renders content
        sigil = page.evaluate(
            "getComputedStyle(document.querySelector('.panel'), '::before').content"
        )
        check(sigil not in ("none", "normal", ""), f"panel corner sigil present ({sigil})")

        # --- scroll: click a constellation, land on the loaded myth text ---
        # Phone width: single column, legend is last, so there's room to scroll
        # it to the top — this is the case the user actually hit.
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector(".const-card", timeout=20000)
        card = page.query_selector('.const-card[role="button"]')
        if not card:
            check(False, "a constellation with a myth is available to click")
        else:
            card.scroll_into_view_if_needed()
            page.evaluate("window.scrollTo({ top: 0, behavior: 'auto' })")
            page.wait_for_timeout(300)
            y_before = page.evaluate("window.scrollY")
            card.click()
            page.wait_for_selector(".myth-text", timeout=20000)
            # Poll until the smooth scroll settles the legend header near the top.
            try:
                page.wait_for_function(
                    """() => {
                        const t = document.getElementById('legend-hdr').getBoundingClientRect();
                        return t.top >= -2 && t.top < window.innerHeight * 0.6;
                    }""",
                    timeout=5000,
                )
                in_view = True
            except Exception:
                in_view = False
            check(in_view, "legend scrolled into view after myth loaded")
            y_after = page.evaluate("window.scrollY")
            check(y_after > y_before + 50,
                  f"page actually scrolled down to the myth ({y_before}->{y_after})")
            active = page.evaluate(
                "!!document.querySelector('.const-card.active')"
            )
            check(active, "clicked card marked active")
            # readability: loaded myth text is bright (bone), not the old dim grey
            myth_color = page.evaluate(
                "getComputedStyle(document.querySelector('.myth-text')).color"
            )
            check(myth_color == "rgb(202, 202, 206)",
                  f"myth text high contrast / bone ({myth_color})")
            # drop cap renders large and blood-coloured
            dc = page.evaluate(
                """() => {
                    const s = getComputedStyle(document.querySelector('.myth-text'), '::first-letter');
                    return { size: parseFloat(s.fontSize), color: s.color };
                }"""
            )
            check(dc["size"] >= 40 and dc["color"] == "rgb(138, 28, 28)",
                  f"blood drop-cap on myth ({dc['size']}px {dc['color']})")
            page.screenshot(path=str(SHOTS / "myth-selected.png"), full_page=True)

        ctx.close()
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="attach to a running server instead of booting one")
    args = ap.parse_args()

    proc = None
    url = args.url
    if not url:
        url = f"http://127.0.0.1:{PORT}"
        proc = boot_server()

    try:
        if not wait_health(url):
            print(f"server not healthy at {url}", file=sys.stderr)
            return 2
        print(f"checking {url}\n")
        run_checks(url)
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} checks passed  ·  shots in {SHOTS}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
