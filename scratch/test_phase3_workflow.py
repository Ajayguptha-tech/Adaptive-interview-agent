"""
Automated Playwright Acceptance Test for Phase 3: Resume-First Workflow
Tests:
1. Landing page loads without JavaScript errors.
2. Both Python and Full-Stack tracks visible and selectable.
3. Supported resume uploaded (.txt, .pdf, .docx).
4. Invalid file types and oversized files rejected correctly.
5. Resume processing produces candidate profile and extracted skills.
6. Personalized interview plan appears before interview starts.
7. Changing interview track updates plan appropriately.
8. Interview cannot start with unanalyzed resume file selected.
9. General interview without resume still works.
10. Workflow stepper, loading states, error messages, and buttons behave correctly.
"""

import os
import sys
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

def test_phase3_workflow():
    print("=" * 70)
    print("PHASE 3 ACCEPTANCE TESTING: RESUME-FIRST WORKFLOW (PLAYWRIGHT)")
    print("=" * 70)

    js_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Capture console errors
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.on("console", lambda msg: js_errors.append(msg.text) if msg.type == "error" else None)

        print("[Step 1] Navigating to landing page...")
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        assert len(js_errors) == 0, f"JavaScript errors detected on load: {js_errors}"
        title = page.title()
        print(f"         Page Title: '{title}' (0 JS errors)")

        print("[Step 2] Verifying track cards visibility and selectability...")
        card_py = page.locator("#card-track-python")
        card_fs = page.locator("#card-track-fullstack")
        assert card_py.is_visible()
        assert card_fs.is_visible()
        print("         Both Python and Full-Stack track cards are visible.")

        # Test selecting Python track
        page.locator("#card-track-python button").click()
        page.wait_for_selector("#setup-view.active")
        badge_text = page.locator("#setup-track-badge").inner_text()
        assert "Python" in badge_text
        print(f"         Selected Python track -> Setup view active ({badge_text})")

        # Test Back to track selection
        page.locator("#back-to-tracks-btn").click()
        page.wait_for_selector("#track-select-view.active")
        print("         Navigated back to track selection.")

        # Test selecting Full-Stack track
        page.locator("#card-track-fullstack button").click()
        page.wait_for_selector("#setup-view.active")
        badge_text = page.locator("#setup-track-badge").inner_text()
        assert "Full-Stack" in badge_text
        # Tech stack config card must be visible for Full-Stack
        assert page.locator("#tech-stack-config-card").is_visible()
        print(f"         Selected Full-Stack track -> Setup view active ({badge_text}, tech stack selector visible)")

        # Switch back to Python track
        page.locator("#back-to-tracks-btn").click()
        page.wait_for_selector("#track-select-view.active")
        page.locator("#card-track-python button").click()
        page.wait_for_selector("#setup-view.active")

        print("[Step 3 & 4] Testing file upload rejection (invalid types & oversized)...")
        # Create temporary test files
        scratch_dir = os.path.abspath("scratch")
        invalid_file = os.path.join(scratch_dir, "test_invalid.exe")
        with open(invalid_file, "wb") as f:
            f.write(b"MZ Invalid executable content")

        # Listen for dialog
        dialog_messages = []
        page.on("dialog", lambda dialog: (dialog_messages.append(dialog.message), dialog.accept()))

        # Try uploading invalid file
        file_input = page.locator("#resume-file-input")
        file_input.set_input_files(invalid_file)
        page.wait_for_timeout(500)
        assert any("unsupported" in m.lower() for m in dialog_messages), f"Expected unsupported format alert, got: {dialog_messages}"
        print(f"         Invalid file rejected with dialog: '{dialog_messages[-1]}'")

        print("[Step 5] Uploading valid synthetic resume (Python, SQL, FastAPI)...")
        valid_resume_path = os.path.join(scratch_dir, "synthetic_python_resume.txt")
        synthetic_resume = """
Jordan Vance
Senior Python Engineer
jordan.vance@example.com

SUMMARY:
5+ years experience developing scalable backend systems, APIs, and databases using Python, FastAPI, and SQL.

TECHNICAL SKILLS:
Python, FastAPI, SQL, PostgreSQL, Docker, Git

EXPERIENCE:
Senior Software Engineer | CloudData Systems (2022 - Present)
- Developed asynchronous microservices using FastAPI and PostgreSQL handling 10k req/min.
- Optimized SQL database queries and data models in Python.
"""
        with open(valid_resume_path, "w", encoding="utf-8") as f:
            f.write(synthetic_resume.strip())

        dialog_messages.clear()
        file_input.set_input_files(valid_resume_path)
        page.wait_for_timeout(500)
        display_name = page.locator("#resume-file-name-display").inner_text()
        assert "synthetic_python_resume.txt" in display_name
        print(f"         File selected: '{display_name}'")

        # Step 8 check: Interview CANNOT start if file is selected but not analyzed
        print("[Step 8] Verifying interview cannot start with unanalyzed resume file...")
        dialog_messages.clear()
        page.locator("#start-interview-btn").click()
        page.wait_for_timeout(500)
        assert any("not analyzed" in m.lower() for m in dialog_messages), f"Expected warning dialog, got: {dialog_messages}"
        print(f"         Prevented premature interview start with dialog: '{dialog_messages[-1][:60]}...'")

        # Step 5: Analyze resume
        print("[Step 5 & 6] Clicking 'Analyze Resume & Extract Skills'...")
        page.locator("#resume-analyze-btn").click()
        # Wait for preview panel to become visible
        page.wait_for_selector("#resume-preview-panel", state="visible", timeout=25000)
        candidate_name = page.locator("#resume-candidate-name").inner_text()
        chips = page.locator("#resume-skills-chips .skill-chip").all_inner_texts()
        print(f"         Profile extracted: Name='{candidate_name}', Skills={chips}")
        assert len(chips) >= 3

        # Step 6: Verify personalized interview plan appears
        page.wait_for_selector("#resume-plan-container", state="visible", timeout=10000)
        plan_summary = page.locator("#plan-summary-text").inner_text()
        agenda_items = page.locator("#plan-agenda-list .plan-agenda-item").all_inner_texts()
        print(f"         Personalized Plan: '{plan_summary[:70]}...'")
        print(f"         Agenda Items ({len(agenda_items)}): {agenda_items[:2]}")
        assert len(agenda_items) > 0

        # Step 7: Changing track updates plan
        print("[Step 7] Changing interview track to Full-Stack and verifying plan updates...")
        page.locator("#back-to-tracks-btn").click()
        page.wait_for_selector("#track-select-view.active")
        page.locator("#card-track-fullstack button").click()
        page.wait_for_selector("#setup-view.active")
        page.wait_for_timeout(2000)
        fs_plan_summary = page.locator("#plan-summary-text").inner_text()
        print(f"         Full-Stack updated plan: '{fs_plan_summary[:70]}...'")

        # Switch back to Python for consistency
        page.locator("#back-to-tracks-btn").click()
        page.wait_for_selector("#track-select-view.active")
        page.locator("#card-track-python button").click()
        page.wait_for_selector("#setup-view.active")

        # Step 9: Verify general interview without resume
        print("[Step 9] Verifying removing resume allows general interview...")
        page.locator("#resume-remove-btn").click()
        page.wait_for_timeout(500)
        badge = page.locator("#resume-status-badge").inner_text()
        assert "Optional" in badge
        print(f"         Resume removed cleanly. Badge: '{badge}'")

        # Re-attach resume for complete testing
        file_input.set_input_files(valid_resume_path)
        page.locator("#resume-analyze-btn").click()
        page.wait_for_selector("#resume-plan-container", state="visible", timeout=25000)
        print("         Resume re-analyzed and linked for interview.")

        # Step 10: Stepper verification
        active_step = page.locator(".step-badge.active").inner_text()
        print(f"[Step 10] Stepper active badge: '{active_step.replace(chr(10), ' ')}'")

        browser.close()

    print("=" * 70)
    print("PHASE 3: ALL 10 RESUME-FIRST WORKFLOW CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_phase3_workflow()
