"""Inspect/verify the existing hosted app, without owner credentials or KIS calls."""
import argparse
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import expect, sync_playwright, Error as BrowserError


APP_URL = "https://global-stage-radar-kmb524zemj5vawb3ipampm.streamlit.app/"


def public_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def app_surface(page):
    """Community Cloud embeds the app; local Streamlit is the main frame."""
    for frame in page.frames:
        try:
            if frame.locator('[data-testid="stAppViewContainer"]').count():
                return frame
        except BrowserError:
            # The hosting wrapper can replace its iframe during startup/reboot.
            continue
    return page.main_frame


def verify(page, expected, timeout, output, inspect_only=False):
    page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        surface = app_surface(page)
        try:
            marker = surface.evaluate("()=>document.documentElement.dataset.radarRelease||''")
            header = surface.locator(".st-key-analysis_header")
            main = surface.locator('[data-testid="stMain"]')
        except BrowserError:
            page.wait_for_timeout(1000)
            continue
        if inspect_only and (header.count() or (main.count() and len(main.inner_text()) > 30)):
            break
        if marker == expected and header.count():
            break
        # The documented Community Cloud sleep screen can be woken without login.
        wake = page.get_by_role("button", name=re.compile(r"Yes, get this app back up!?", re.I))
        if wake.count() and wake.first.is_visible():
            wake.first.click()
        if "share.streamlit.io" in page.url and "auth" in page.url:
            raise RuntimeError("Hosted application requires Streamlit sign-in; deployment not verified")
        page.wait_for_timeout(1000)
    else:
        raise RuntimeError("Hosted app was not available for inspection" if inspect_only else
                           "Hosted app did not serve the expected release within the verification window")

    result = {
        "url": public_url(page.url), "title": page.title(), "observed_release": marker,
        "expected_release": expected, "release_matches": marker == expected,
        "frames": [public_url(frame.url) for frame in page.frames],
        "source_links": [public_url(url) for frame in page.frames for url in frame.locator('a[href*="github.com/wonbosong-arch/global-stage-radar"]').evaluate_all("es=>es.map(e=>e.href)")],
        "tabs": header.locator("[role=radiogroup]").inner_text().splitlines() if header.count() else [],
        "headings": surface.locator("h1,h2,h3").all_text_contents()[:8],
    }
    if inspect_only:
        result["state"] = "inspected_only"
        page.screenshot(path=str(output / "hosted-baseline.png"))
        return result

    def progress(step):
        result['step'] = step
        (output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))

    progress('keyboard_bookmark')
    expect(header.get_by_role("radio", name="☆ 관심 목록", exact=True)).to_have_count(1)
    header.get_by_text("종목", exact=True).click()
    star = surface.locator(".st-key-stocks_favorite button:visible")
    expect(star).to_have_count(1, timeout=30000)
    star.focus()
    star.press("Space")
    surface.wait_for_function("()=>JSON.parse(sessionStorage.getItem('global-stage-radar:favorites:v2')||'[]').length>0")
    header.get_by_text("☆ 관심 목록", exact=True).click()
    expect(surface.locator(".st-key-favorites_selected_chart_asset_card")).to_be_visible(timeout=30000)
    progress('select_grid')
    surface.locator(".st-key-favorites_view_mode").get_by_text("3×3 차트", exact=True).click()
    surface.wait_for_function("()=>{try{return JSON.parse(new URL(location.href).searchParams.get('radar')).favorites.mode==='3×3 차트';}catch{return false;}}")
    surface.wait_for_function("()=>{try{return JSON.parse(sessionStorage.getItem('global-stage-radar:preferences:v1')).favorites.mode==='3×3 차트';}catch{return false;}}")
    progress('reload_hosting_frame')
    page.reload(wait_until="domcontentloaded")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        surface = app_surface(page)
        if surface.locator(".st-key-favorites_grid_canvas button:visible").filter(has_text="★ 관심 해제").count() == 1:
            break
        page.wait_for_timeout(500)
    expect(surface.locator(".st-key-favorites_grid_canvas button:visible").filter(has_text="★ 관심 해제")).to_have_count(1, timeout=30000)
    expect(surface.locator("[data-testid=stException]")).to_have_count(0)
    progress('mobile_layout')
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 1000})
        page.wait_for_timeout(400)
        assert surface.locator("[data-testid=stMain]").evaluate("e=>e.scrollWidth") <= width + 1
        page.screenshot(path=str(output / f"hosted-{width}.png"))
    result.update(state="verified", demo_navigation=True, keyboard_bookmark=True,
                  bookmark_reload=True, mobile_layout=True, live_provider_calls=False)
    result.pop('step', None)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--expected-release")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--browser")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/hosted-dashboard"))
    args = parser.parse_args()
    expected = args.expected_release or json.loads((Path(__file__).resolve().parents[1] / "release_info.json").read_text())["version"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result, code = {}, 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            result = verify(page, expected, args.timeout, args.output_dir, args.inspect)
        except Exception as exc:
            progress_file = args.output_dir / 'result.json'
            if progress_file.exists():
                result = json.loads(progress_file.read_text())
            result.update({"state": "not_verified", "expected_release": expected,
                      "url": public_url(page.url), "error_type": type(exc).__name__,
                      "reason": str(exc).splitlines()[0][:250]})
            page.screenshot(path=str(args.output_dir / "hosted-not-verified.png"))
            code = 0 if args.inspect else 1
        finally:
            browser.close()
    (args.output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
