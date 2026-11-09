"""Exercise the dashboard uploader with invented CSVs and an in-memory GitHub."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

import nasdaq_private_review as review
import nasdaq_single_source as engine
import nasdaq_web_upload as upload
from test_nasdaq_github_store import GitHub
from test_nasdaq_private_review import synthetic_inputs
from test_nasdaq_web_upload import upload_csv

PASSWORD = "synthetic-password"


def serve(port, folder):
    import requests
    from streamlit.web import cli

    data = folder / "data"
    data.mkdir()
    source, _, engine.BASELINE, engine.EXPANSION = synthetic_inputs(data)
    review.ROOT = folder
    upload.MIN_ROWS = 10
    (folder / "synthetic.csv").write_bytes(
        upload_csv(source, changes={0: {"Name": "Example\tHoldings, Inc."}})
    )
    secret = folder / "secrets.toml"
    secret.write_text(f'APP_PASSWORD = "{PASSWORD}"\nNASDAQ_GITHUB_TOKEN = "synthetic-github-token"\n')
    os.environ.update(NASDAQ_PRIVATE_REVIEW_ENABLED="1", NASDAQ_PRIVATE_REVIEW_CONTEXT=review.PUBLIC_CONTEXT)
    backend = GitHub()
    backend.reject_next_write = True
    requests.request = backend.request

    def reject_provider(*args, **kwargs):
        raise AssertionError("Unexpected provider request in Nasdaq browser regression")

    requests.sessions.Session.request = reject_provider
    sys.argv = ["streamlit", "run", str(ROOT / "app.py"), "--server.address=127.0.0.1",
                f"--server.port={port}", "--browser.gatherUsageStats=false",
                "--server.headless=true", f"--secrets.files={secret}"]
    cli.main()


def exercise(page, base, folder):
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") else route.abort())
    page.goto(base, wait_until="domcontentloaded")
    entry = page.get_by_text("NASDAQ CSV 업로드", exact=True)
    panel = page.get_by_test_id("stExpander").filter(has=entry)
    expect(entry).to_be_visible(timeout=60000)
    entry.click()
    password = panel.get_by_label("앱 비밀번호", exact=True)
    unlock = panel.get_by_role("button", name="업로드 잠금 해제")
    file = panel.locator('input[type="file"]')
    save = panel.get_by_role("button", name="공개 GitHub에 저장", exact=True)
    browse = panel.get_by_role("button", name="Upload", exact=True)
    expect(file).to_have_count(0)
    password.fill("wrong")
    unlock.click()
    expect(panel.get_by_text("비밀번호가 일치하지 않습니다.")).to_be_visible()
    expect(file).to_have_count(0)
    password.fill(PASSWORD)
    unlock.click()
    expect(panel.get_by_text("첫 업로드가 필요합니다.")).to_be_visible(timeout=60000)
    expect(panel.get_by_role("checkbox")).to_have_count(0)

    header = page.locator(".st-key-analysis_header")
    header.get_by_text("종목", exact=True).click()
    picks = page.locator('[class*=st-key-stocks_selected_symbol_pick_] button:visible')
    expect(picks).to_have_count(3, timeout=60000)
    symbol = picks.nth(1).inner_text().strip()
    picks.nth(1).click()
    chart = page.locator(".st-key-stocks_selected_chart .js-plotly-plot")
    page.wait_for_function("s => document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot')?.layout?.meta?.asset_symbol === s",
                           arg=symbol)
    period = page.locator(f".st-key-stocks_selected_period_{symbol}")
    period.get_by_text("일봉", exact=True).click()
    expect(period.get_by_role("radio", name="일봉", exact=True)).to_be_checked()

    def select_download_date():
        expect(panel.get_by_text("다운로드일을 선택하면 자동으로 검증합니다.", exact=True)).to_be_visible()
        panel.get_by_role("button", name="Choose date").click()
        day = str(datetime.now(timezone.utc).day)
        page.get_by_role("grid").get_by_text(day, exact=True).click()

    file.set_input_files({"name": "bad.csv", "mimeType": "text/csv", "buffer": b"bad input"})
    select_download_date()
    expect(panel.get_by_text(f"{upload.PUBLIC_ERROR} [invalid_structure]", exact=True)).to_be_visible()
    expect(save).to_have_count(0)
    panel.get_by_role("button", name="Remove bad.csv").click()
    expect(browse).to_be_visible()
    file.set_input_files(folder / "synthetic.csv")
    select_download_date()
    expect(panel.get_by_text("검증 통과", exact=False)).to_be_visible(timeout=30000)
    expect(panel.get_by_text("첫 업로드가 필요합니다.")).to_be_visible()
    save.click()
    expect(panel.get_by_text(upload.SAVE_ERROR, exact=True)).to_be_visible()
    expect(save).to_have_count(0)
    panel.get_by_role("button", name="저장본 다시 확인").click()
    expect(save).to_be_visible(timeout=30000)
    save.click()
    expect(panel.get_by_text("마지막 저장", exact=False)).to_be_visible(timeout=30000)
    expect(panel.get_by_text("이번 주 업로드 완료", exact=False)).to_be_visible()
    expect(save).to_have_count(0)
    panel.get_by_role("button", name="Remove synthetic.csv").click()
    expect(browse).to_be_visible()
    file.set_input_files({"name": "renamed.csv", "mimeType": "text/csv",
                          "buffer": (folder / "synthetic.csv").read_bytes()})
    expect(panel.get_by_text(upload.DUPLICATE_ERROR, exact=True)).to_be_visible()
    expect(save).to_have_count(0)
    expect(header.get_by_role("radio", name="종목", exact=True)).to_be_checked()
    expect(period.get_by_role("radio", name="일봉", exact=True)).to_be_checked()
    assert chart.evaluate("e => e.layout.meta.asset_symbol") == symbol

    page.reload(wait_until="domcontentloaded")
    expect(entry).to_be_visible(timeout=60000)
    if not password.is_visible():
        entry.click()
    expect(file).to_have_count(0)
    password.fill(PASSWORD)
    unlock.click()
    expect(panel.get_by_text("마지막 저장", exact=False)).to_be_visible(timeout=60000)
    expect(save).to_have_count(0)
    expect(page.get_by_test_id("stException")).to_have_count(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser")
    parser.add_argument("--serve", type=Path)
    parser.add_argument("--port", type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/nasdaq-upload"))
    args = parser.parse_args()
    if args.serve:
        serve(args.port, args.serve)
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory() as temp, (args.output_dir / "streamlit.log").open("w", encoding="utf-8") as log:
        folder = Path(temp)
        server = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve", temp, "--port", str(port)],
                                  cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(120):
                try:
                    with urlopen(base + "/_stcore/health", timeout=1):
                        break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError("Synthetic Streamlit server exited; see streamlit.log")
                    time.sleep(.25)
            else:
                raise RuntimeError("Synthetic Streamlit server did not start")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                try:
                    exercise(page, base, folder)
                    print("Nasdaq upload, approval, recovery and chart preservation passed")
                except Exception:
                    page.screenshot(path=str(args.output_dir / "failure.png"))
                    raise
                finally:
                    browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
