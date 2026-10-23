"""
Browser End-to-End Acceptance Test for Resume-Driven, Voice-First Adaptive Interview Workflow.
Runs using Playwright against live server at http://127.0.0.1:8000.
"""

import os
import sys
import time
import tempfile
import pytest
from playwright.sync_api import sync_playwright, expect


SAMPLE_RESUME_TEXT = """
Alex Mercer
Email: alex.mercer@example.com | Phone: +1-555-0199 | Location: Seattle, WA

SUMMARY
Backend Software Engineer with 4 years of experience building high-throughput REST APIs,
microservices, and data pipelines using Python, FastAPI, PostgreSQL, and Redis.

TECHNICAL SKILLS
- Programming Languages: Python, SQL
- Frameworks & Libraries: FastAPI, Flask, Pydantic, SQLAlchemy, PyTest
- Databases & Caching: PostgreSQL, Redis
- Infrastructure & Tools: Docker, Git, CI/CD, Linux

EXPERIENCE
Software Engineer | CloudScale Systems (2022 - Present)
- Designed and maintained 15+ microservices in Python with FastAPI handling 25,000 requests/sec.
- Optimized PostgreSQL queries and implemented Redis caching, reducing p99 latency by 45%.
- Implemented robust unit and integration testing pipelines achieving 92% code coverage.

PROJECTS
Adaptive Task Processing Engine (Python, FastAPI, Redis)
- Distributed asynchronous task queue with retry logic and dead-letter queues.
"""


def test_browser_e2e_full_workflow():
    """
    Complete candidate end-to-end journey:
    1. Fresh visitor sees ONLY resume upload and target role.
    2. Uploads resume and enters target role -> triggers automatic analysis.
    3. Profile and interview settings shown (no internal agent selectors).
    4. Starts interview -> Question-driven workspace loads.
    5. Conceptual question presents voice-first workspace without code editor.
    6. Answer submitted -> Evaluated accurately with rubrics and score.
    7. Early or normal termination produces comprehensive evidence report.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_RESUME_TEXT)
        resume_file_path = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Collect any uncaught console errors and dialog messages
            console_errors = []
            dialog_messages = []
            page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}"))
            page.on("dialog", lambda dialog: (dialog_messages.append(f"[{dialog.type}] {dialog.message}"), dialog.accept()))

            # Step 1: Open Application
            page.goto("http://127.0.0.1:8000/")
            page.wait_for_load_state("networkidle")

            # 1.1 Verify Landing Page is the first screen of the application
            assert page.is_visible("#landing-view"), "Landing page must be visible on initial load"
            assert page.is_visible("#start-your-interview-btn"), "Start Your Interview button must be visible on landing page"
            assert not page.is_visible("#upload-view"), "Upload view must be hidden before candidate initiates interview"
            assert not page.is_visible("#settings-view"), "Settings view must be hidden initially"
            assert not page.is_visible("#interview-view"), "Interview view must be hidden initially"
            assert not page.is_visible("#report-view"), "Report view must be hidden initially"

            # 1.2 Navigate from Landing Page to Resume Upload
            page.click("#start-your-interview-btn")
            page.wait_for_selector("#upload-view", state="visible")
            assert not page.is_visible("#landing-view"), "Landing view should be hidden after clicking Start Your Interview"

            # 1.3 Verify required upload controls exist
            assert page.is_visible("#initial-target-role"), "Target role input must be visible"
            assert page.is_visible("#initial-drop-zone"), "Drop zone must be visible"
            assert page.is_visible("#analyze-resume-btn"), "Analyze button must be visible"
            assert page.is_disabled("#analyze-resume-btn"), "Analyze button must be disabled until inputs provided"

            # 1.4 Verify NO internal agent selectors or track cards exist in DOM
            page_content = page.content()
            assert "card-track-python" not in page_content, "Python track card must NOT exist in candidate DOM"
            assert "card-track-fullstack" not in page_content, "FullStack track card must NOT exist in candidate DOM"
            assert "type-answer-btn" not in page_content, "Manual answer type selector must NOT exist in candidate DOM"

            # Step 2: Fill Target Role & Select Resume File
            page.fill("#initial-target-role", "Senior Python Engineer")
            page.set_input_files("#initial-resume-file", resume_file_path)

            # Verify file badge appears and analyze button becomes enabled
            page.wait_for_selector("#file-selected-badge", state="visible")
            page.wait_for_function("!document.getElementById('analyze-resume-btn').disabled")
            assert not page.is_disabled("#analyze-resume-btn"), "Analyze button must be enabled now"

            # Step 3: Click Analyze Resume
            page.click("#analyze-resume-btn")

            # Wait for settings view to become visible
            page.wait_for_selector("#settings-view", state="visible", timeout=30000)
            assert not page.is_visible("#upload-view"), "Upload view should now be hidden"

            # 3.1 Verify Candidate Profile rendered accurately
            candidate_name = page.inner_text("#profile-candidate-name")
            assert "Alex" in candidate_name, f"Expected candidate name 'Alex', got '{candidate_name}'"
            target_role = page.inner_text("#profile-target-role")
            assert "Senior Python Engineer" in target_role

            # 3.2 Verify routed track card is HIDDEN from candidates
            assert not page.is_visible("#profile-routed-track"), "Internal routed track must be HIDDEN from candidates"

            # 3.3 Verify no internal agent names exposed
            settings_text = page.inner_text("#settings-view")
            assert "Python Interviewer Agent" not in settings_text
            assert "Full-Stack Interviewer Agent" not in settings_text
            assert "qwen2.5:7b" not in settings_text

            # 3.4 Verify candidate-friendly Interview Mode labels (Mock Interview & Adaptive Interview)
            mock_btn = page.locator("#mode-pills button[data-mode='predefined']")
            assert "Mock Interview" in mock_btn.inner_text(), f"Expected 'Mock Interview' label, got '{mock_btn.inner_text()}'"
            adaptive_btn = page.locator("#mode-pills button[data-mode='adaptive']")
            assert "Adaptive Interview" in adaptive_btn.inner_text(), f"Expected 'Adaptive Interview' label, got '{adaptive_btn.inner_text()}'"

            # Step 4: Configure Settings & Prepare Questions
            # Select 5 questions length (standard calibrated minimum)
            page.click("#length-pills button[data-count='5']")

            # Select Mock Interview mode
            mock_btn.click()

            # Verify Question Prep indicators
            page.wait_for_selector("#prep-indicator-card", state="visible")

            # Step 5: Start Interview
            start_btn = page.locator("#start-interview-btn")
            assert not start_btn.is_disabled()
            page.click("#start-interview-btn")

            # Wait for interview view to become visible (allow up to 90s for CPU inference/prewarm completion)
            page.wait_for_selector("#interview-view", state="visible", timeout=90000)
            assert not page.is_visible("#settings-view"), "Settings view should now be hidden"

            # 5.1 Verify Question is loaded
            page.wait_for_selector("#question-text", state="visible")
            q_text = page.inner_text("#question-text")
            assert len(q_text) > 10, f"Expected non-empty question text, got '{q_text}'"

            # 5.2 Verify Voice-First Workspace is visible, Code Editor and manual textbox are hidden for verbal question
            assert page.is_visible("#workspace-voice"), "Voice workspace must be visible for conceptual question"
            assert not page.is_visible("#workspace-code-editor"), "Code editor must be HIDDEN for conceptual question"
            assert not page.is_visible("#transcript-input"), "Typing textarea must be HIDDEN by default for verbal question"
            assert page.is_visible("#finish-answer-btn"), "Finish Answer button must be visible for voice answers"

            # 5.3 Verify NO manual answer-type selector exists
            assert not page.is_visible("#answer-type-selector"), "Manual answer type selector must not appear"

            # Step 6: Submit Spoken/Verbal Answer
            # Fill candidate answer via recognized transcript
            page.evaluate("""() => {
                const el = document.getElementById('transcript-input');
                el.value = 'In Python, lists are mutable variable-length arrays storing pointers to objects. Tuples are immutable fixed-length sequences whose elements cannot be altered or appended after creation. Tuples can also serve as dictionary keys if all their items are hashable.';
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }""")

            # Submit using Finish Answer
            page.click("#finish-answer-btn")

            # Wait for evaluation feedback to appear (CPU Ollama evaluation takes 45-70s)
            page.wait_for_selector("#feedback-card", state="visible", timeout=120000)

            # 6.1 Verify Score and Rubric Evaluation
            feedback_earned = page.inner_text("#feedback-earned")
            feedback_summary = page.inner_text("#feedback-summary")
            assert float(feedback_earned) > 0, f"Expected positive score awarded, got {feedback_earned}"
            assert len(feedback_summary) > 10, "Expected non-empty feedback summary"

            # Step 7: End Interview Early to Inspect Intelligence Report
            page.click("#end-interview-btn")

            # Wait for report view to become visible
            try:
                page.wait_for_selector("#report-view", state="visible", timeout=15000)
            except Exception as e:
                print("DEBUG DIALOGS:", dialog_messages)
                print("DEBUG CONSOLE:", console_errors)
                raise e
            assert not page.is_visible("#interview-view"), "Interview view should be hidden"

            # 7.1 Verify Intelligence Report contents
            normalized_score = page.inner_text("#report-normalized-score")
            assert int(normalized_score) > 0, f"Expected normalized score > 0, got {normalized_score}"

            # 7.2 Verify No internal agent or model names in Report
            report_text = page.inner_text("#report-view")
            assert "Python Interviewer Agent" not in report_text
            assert "Full-Stack Interviewer Agent" not in report_text
            assert "qwen2.5:7b" not in report_text

            browser.close()

            # Ensure zero uncaught JavaScript errors
            critical_errors = [e for e in console_errors if e.startswith("[error]") and "favicon" not in e and "404" not in e]
            assert len(critical_errors) == 0, f"Uncaught JavaScript console errors: {critical_errors}"

    finally:
        if os.path.exists(resume_file_path):
            os.remove(resume_file_path)
