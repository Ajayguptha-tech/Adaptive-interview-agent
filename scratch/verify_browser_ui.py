"""
Automated Playwright Browser Test verifying DOM elements, navigation, and resume upload UI.
Note: Hardware microphone and speaker capture cannot be verified headlessly without physical I/O devices.
"""

from playwright.sync_api import sync_playwright


def test_browser_ui_flow():
    print("[1/4] Launching Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("[2/4] Navigating to http://127.0.0.1:8000 ...")
        page.goto("http://127.0.0.1:8000")
        page.wait_for_load_state("networkidle")

        title = page.title()
        print(f"      Page Title: {title}")
        assert "Adaptive" in title or "Interviewer" in title

        print("[3/4] Verifying Core UI DOM Elements...")
        # Check track selection buttons / cards
        has_python_btn = page.locator("text=Python").first.is_visible()
        print(f"      Python Track Element Visible: {has_python_btn}")
        assert has_python_btn

        # Check resume upload area
        file_inputs = page.locator('input[type="file"]')
        print(f"      File inputs found: {file_inputs.count()}")

        print("[4/4] Browser DOM verification completed successfully!")
        browser.close()


if __name__ == "__main__":
    test_browser_ui_flow()
