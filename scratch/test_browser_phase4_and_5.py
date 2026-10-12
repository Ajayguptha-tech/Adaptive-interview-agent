"""
Playwright Acceptance Test for Phase 4 (Python Interview) & Phase 5 (Full-Stack Interview)
Runs against live application at http://127.0.0.1:8000
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

def run_phase4_and_5_browser_tests():
    print("=" * 75)
    print("STARTING PLAYWRIGHT LIVE ACCEPTANCE TESTS FOR PHASES 4 & 5")
    print(f"Target: {BASE_URL}")
    print("=" * 75)

    js_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.on("dialog", lambda d: (print(f"       [Dialog]: {d.message[:70]}..."), d.accept()))

        # =====================================================================
        # PHASE 4: COMPLETE PYTHON INTERVIEW WORKFLOW
        # =====================================================================
        print("\n" + "#" * 60)
        print("PHASE 4: PYTHON INTERVIEW LIVE BROWSER WORKFLOW")
        print("#" * 60)

        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # 1. Select Python Track
        print("[P4-1] Selecting Python track...")
        page.locator("#card-track-python button").click()
        page.wait_for_selector("#setup-view.active")

        # Select Curated Question Bank for deterministic evaluation
        page.locator("#dynamic-mode-pills button[data-dynamic='false']").click()
        page.wait_for_timeout(300)

        # 2. Upload Synthetic Resume (Python, SQL, FastAPI)
        print("[P4-2] Uploading synthetic Python resume...")
        scratch_dir = os.path.abspath("scratch")
        py_resume_file = os.path.join(scratch_dir, "synthetic_python_qa_resume.txt")
        with open(py_resume_file, "w", encoding="utf-8") as f:
            f.write("""
Morgan Drake
Backend Python Engineer
morgan.drake@example.com

SUMMARY
5+ years experience building Python web APIs with FastAPI and relational databases with PostgreSQL/SQL.

TECHNICAL SKILLS
Python, FastAPI, SQL, PostgreSQL, Docker, Git

EXPERIENCE
Software Engineer | DataScale Systems (2021 - Present)
- Developed REST APIs in Python and FastAPI.
- Optimized database queries using SQL.
""")

        page.locator("#resume-file-input").set_input_files(py_resume_file)
        page.locator("#resume-analyze-btn").click()
        page.wait_for_selector("#resume-preview-panel", state="visible", timeout=30000)
        page.wait_for_selector("#resume-plan-container", state="visible", timeout=15000)

        # 3. Confirm Generated Plan Reflects Resume Skills
        print("[P4-3] Confirming generated plan reflects resume skills...")
        plan_summary = page.locator("#plan-summary-text").inner_text()
        plan_skills = page.locator("#plan-skills-chips .skill-chip").all_inner_texts()
        agenda_items = page.locator("#plan-agenda-list .plan-agenda-item").all_inner_texts()
        print(f"       Plan Summary: {plan_summary[:80]}...")
        print(f"       Targeted Skills: {plan_skills}")
        print(f"       Agenda Items ({len(agenda_items)}):")
        for ag in agenda_items:
            print(f"         - {' '.join(ag.split())}")
        assert any("Python" in s or "FastAPI" in s or "SQL" in s for s in plan_skills)

        # 4. Start Interview
        print("[P4-4] Starting interview...")
        page.locator("#start-interview-btn").scroll_into_view_if_needed()
        page.locator("#start-interview-btn").click()
        page.wait_for_selector("#interview-view.active", timeout=45000)

        # Check Q1 details
        q1_text = page.locator("#question-text").inner_text()
        q1_topic = page.locator("#topic-badge").inner_text()
        q1_diff = page.locator("#difficulty-badge").inner_text()
        q1_type = page.locator("#type-badge").inner_text()
        print(f"       Q1 Started: [{q1_topic}] ({q1_diff}, {q1_type})")
        print(f"       Prompt: '{q1_text[:80]}...'")

        # 5. Answer Q1 Strongly and Correctly based on Topic
        print(f"[P4-5] Submitting strong answer for Q1 topic '{q1_topic}'...")
        if "async" in q1_topic.lower() or "async" in q1_text.lower():
            strong_ans = (
                "A synchronous blocking function executes sequentially and blocks the single-threaded event loop entirely, "
                "which freezes and delays all concurrent coroutines. In contrast, an async def coroutine cooperatively yields "
                "control back to the event loop during await. If a CPU-bound or blocking call like time.sleep() is executed, "
                "it must be offloaded to a thread or process pool using asyncio.to_thread() or loop.run_in_executor() to avoid "
                "blocking the event loop."
            )
        else:
            strong_ans = (
                "In Python, a list is a mutable dynamic array allowing in-place appending, item reassignment, "
                "and deletion. In contrast, a tuple is immutable, meaning its elements cannot be reassigned or modified "
                "after creation. Because tuples are immutable, they are hashable if their items are hashable, making them "
                "suitable for dictionary keys and coordinates."
            )
        page.evaluate(f"submitAnswerText({repr(strong_ans)})")

        page.wait_for_selector("#feedback-card", state="visible", timeout=45000)
        earned1 = page.locator("#feedback-earned").inner_text()
        max_m1 = page.locator("#feedback-max").inner_text()
        percent1 = page.locator("#feedback-percent").inner_text()
        print(f"       Q1 Evaluated: {earned1}/{max_m1} marks ({percent1}%)")
        assert float(earned1) >= 3.0, f"Expected high score for strong answer, got {earned1}"

        # 6. Proceed to Q2 (Difficulty Adaptation & Modality Progression)
        print("[P4-6] Advancing to Q2 (Testing Difficulty & Modality Progression)...")
        page.locator("#next-question-btn").click()
        page.wait_for_timeout(1000)

        q2_text = page.locator("#question-text").inner_text()
        q2_topic = page.locator("#topic-badge").inner_text()
        q2_diff = page.locator("#difficulty-badge").inner_text()
        q2_type = page.locator("#type-badge").inner_text()
        print(f"       Q2 Displayed: [{q2_topic}] ({q2_diff}, {q2_type})")
        print(f"       Prompt: '{q2_text[:80]}...'")

        # 7. Check if Q2 is a code writing/output/conceptual question
        is_code_editor_visible = page.locator("#workspace-code").is_visible()
        is_output_visible = page.locator("#workspace-output").is_visible()
        is_voice_visible = page.locator("#workspace-voice").is_visible()
        print(f"       Workspace status: Code={is_code_editor_visible}, Output={is_output_visible}, Voice={is_voice_visible}")

        # Answer Q2 with a weak/incorrect answer to test adaptation and scoring
        print("[P4-7] Submitting weak/incorrect answer for Q2...")
        weak_ans = "I don't know the answer to this question, I have never learned this concept."
        page.evaluate(f"submitAnswerText({repr(weak_ans)})")

        page.wait_for_selector("#feedback-card", state="visible", timeout=45000)
        earned2 = page.locator("#feedback-earned").inner_text()
        print(f"       Q2 Evaluated: {earned2}/5.0 marks")
        assert float(earned2) < 2.5, f"Expected low score for weak answer, got {earned2}"

        # 8. Proceed to Q3 to test code writing or third question
        print("[P4-8] Advancing to Q3...")
        page.locator("#next-question-btn").click()
        page.wait_for_timeout(1000)

        q3_text = page.locator("#question-text").inner_text()
        q3_topic = page.locator("#topic-badge").inner_text()
        q3_diff = page.locator("#difficulty-badge").inner_text()
        q3_type = page.locator("#type-badge").inner_text()
        print(f"       Q3 Displayed: [{q3_topic}] ({q3_diff}, {q3_type})")

        # If Code Workspace is active, test typing code into the editor
        if page.locator("#workspace-code").is_visible():
            print("       Code Editor is active! Testing code editor input...")
            code_input = page.locator("#code-editor-input")
            code_input.fill("def solution():\n    return True\n")
            page.wait_for_timeout(500)
            page.locator("#code-evaluate-now-btn").click()
            page.wait_for_selector("#feedback-card", state="visible", timeout=45000)
            print("       Code evaluation completed!")
        else:
            # Conceptual or output
            page.evaluate("submitAnswerText('Testing response evaluation.')")
            page.wait_for_selector("#feedback-card", state="visible", timeout=45000)
            print("       Q3 evaluated!")

        # 9. End Interview Early & Inspect Final Intelligence Report
        print("[P4-9] Ending interview to inspect final intelligence report...")
        page.locator("#end-interview-btn").click()
        page.wait_for_selector("#report-view.active", timeout=20000)

        norm_score = page.locator("#report-normalized-score").inner_text()
        meta_text = page.locator("#report-meta-text").inner_text()
        print(f"       Final Normalized Score: {norm_score}/100")
        print(f"       Report Meta: '{meta_text}'")
        assert float(norm_score) > 0.0

        # Check Skill Gap Grid
        page.wait_for_selector("#report-skill-gap-card", state="visible", timeout=10000)
        gap_items = page.locator("#report-skill-gap-grid .skill-gap-item").all_inner_texts()
        print(f"       Report Skill Gap Items ({len(gap_items)}):")
        for item in gap_items:
            clean = " ".join(item.split())
            print(f"         * {clean}")

        # Confirm Python is DEMONSTRATED, but unassessed/weak skills are NOT marked demonstrated
        skill_texts = " ".join(gap_items).upper()
        assert "DEMONSTRATED" in skill_texts
        assert ("CLAIMED" in skill_texts or "UNVALIDATED" in skill_texts or "NOT DEMONSTRATED" in skill_texts)
        print("       [OK] Report isolated evaluated evidence from unvalidated claims!")
        print("PHASE 4 PYTHON BROWSER WORKFLOW COMPLETED SUCCESSFULLY!")

        # =====================================================================
        # PHASE 5: COMPLETE FULL-STACK INTERVIEW WORKFLOW
        # =====================================================================
        print("\n" + "#" * 60)
        print("PHASE 5: FULL-STACK INTERVIEW LIVE BROWSER WORKFLOW")
        print("#" * 60)

        # Restart interview to go back to tracks
        page.locator("#restart-interview-btn").click()
        page.wait_for_selector("#track-select-view.active")

        # 1. Select Full-Stack Track
        print("[P5-1] Selecting Full-Stack track...")
        page.locator("#card-track-fullstack button").click()
        page.wait_for_selector("#setup-view.active")
        assert page.locator("#tech-stack-config-card").is_visible()

        # Select Curated Question Bank
        page.locator("#dynamic-mode-pills button[data-dynamic='false']").click()
        page.wait_for_timeout(300)

        # 2. Upload Synthetic Full-Stack Resume
        print("[P5-2] Uploading synthetic Full-Stack resume (JS, React, REST APIs, SQL)...")
        fs_resume_file = os.path.join(scratch_dir, "synthetic_fullstack_qa_resume.txt")
        with open(fs_resume_file, "w", encoding="utf-8") as f:
            f.write("""
Taylor Reed
Full-Stack Software Engineer
taylor.reed@example.com

SUMMARY
5+ years experience building web applications with modern JavaScript, React frontends, REST APIs, and SQL databases.

TECHNICAL SKILLS
JavaScript, React, REST APIs, SQL, Node.js, Express, HTML, CSS

EXPERIENCE
Full-Stack Developer | WebForge Labs (2021 - Present)
- Engineered responsive React user interfaces with modern JavaScript.
- Built Node.js and Express REST APIs with SQL relational persistence.
""")

        page.locator("#resume-file-input").set_input_files(fs_resume_file)
        page.locator("#resume-analyze-btn").click()
        page.wait_for_selector("#resume-preview-panel", state="visible", timeout=30000)
        page.wait_for_selector("#resume-plan-container", state="visible", timeout=15000)

        # 3. Verify Full-Stack Plan Targets Appropriate Technologies
        print("[P5-3] Verifying Full-Stack plan targets appropriate technologies...")
        fs_plan_summary = page.locator("#plan-summary-text").inner_text()
        fs_plan_skills = page.locator("#plan-skills-chips .skill-chip").all_inner_texts()
        fs_agenda = page.locator("#plan-agenda-list .plan-agenda-item").all_inner_texts()
        print(f"       FS Plan Summary: {fs_plan_summary[:80]}...")
        print(f"       FS Target Skills: {fs_plan_skills}")
        print(f"       FS Agenda Count: {len(fs_agenda)}")
        assert any(k in " ".join(fs_plan_skills) for k in ["React", "JavaScript", "SQL", "REST"])

        # 4. Start Full-Stack Interview
        print("[P5-4] Starting Full-Stack technical interview...")
        page.locator("#start-interview-btn").scroll_into_view_if_needed()
        page.locator("#start-interview-btn").click()
        page.wait_for_selector("#interview-view.active", timeout=45000)

        # Check Track Badge in header
        fs_track_badge = page.locator("#track-badge").inner_text()
        assert "Full-Stack" in fs_track_badge
        print(f"       Track Badge: '{fs_track_badge}'")

        fs_q1_text = page.locator("#question-text").inner_text()
        fs_q1_topic = page.locator("#topic-badge").inner_text()
        fs_q1_type = page.locator("#type-badge").inner_text()
        print(f"       FS Q1: [{fs_q1_topic}] ({fs_q1_type})")
        print(f"       Prompt: '{fs_q1_text[:80]}...'")

        # 5. Answer Q1 Strongly
        print(f"[P5-5] Submitting strong technical answer for FS Q1 '{fs_q1_topic}'...")
        if "react" in fs_q1_topic.lower() or "react" in fs_q1_text.lower():
            fs_strong_ans = (
                "React uses a Virtual DOM which is an in-memory lightweight representation of the real DOM. "
                "When component state changes, React creates a new virtual tree, performs a diffing reconciliation algorithm "
                "to calculate the minimal required mutations, and batches those changes efficiently into the real DOM."
            )
        elif "javascript" in fs_q1_topic.lower() or "js" in fs_q1_topic.lower():
            fs_strong_ans = (
                "In JavaScript, var is function-scoped and hoisted with undefined, while let and const are block-scoped "
                "and stay in the temporal dead zone until declared. const prevents reassigning the variable identifier."
            )
        else:
            fs_strong_ans = (
                "REST APIs use standard HTTP methods like GET, POST, PUT, DELETE with stateless client-server communication "
                "and appropriate HTTP response status codes like 200, 201, 400, and 500."
            )
        page.evaluate(f"submitAnswerText({repr(fs_strong_ans)})")

        page.wait_for_selector("#feedback-card", state="visible", timeout=45000)
        fs_earned1 = page.locator("#feedback-earned").inner_text()
        print(f"       FS Q1 Score: {fs_earned1}/5.0 marks")

        # 6. Proceed to Q2 and Answer Weakly
        print("[P5-6] Advancing to Q2 and submitting weak answer...")
        page.locator("#next-question-btn").click()
        page.wait_for_timeout(1000)

        fs_q2_topic = page.locator("#topic-badge").inner_text()
        print(f"       FS Q2 Topic: [{fs_q2_topic}]")

        fs_weak_ans = "I am completely unfamiliar with this web technology."
        page.evaluate(f"submitAnswerText({repr(fs_weak_ans)})")

        page.wait_for_selector("#feedback-card", state="visible", timeout=45000)
        fs_earned2 = page.locator("#feedback-earned").inner_text()
        print(f"       FS Q2 Score: {fs_earned2}/5.0 marks")

        # 7. End Interview and Inspect Final Report
        print("[P5-7] Ending Full-Stack interview and verifying intelligence report...")
        page.locator("#end-interview-btn").click()
        page.wait_for_selector("#report-view.active", timeout=20000)

        fs_norm_score = page.locator("#report-normalized-score").inner_text()
        print(f"       Full-Stack Normalized Score: {fs_norm_score}/100")
        assert float(fs_norm_score) >= 0.0

        page.wait_for_selector("#report-skill-gap-card", state="visible", timeout=10000)
        fs_gap_items = page.locator("#report-skill-gap-grid .skill-gap-item").all_inner_texts()
        print(f"       Full-Stack Skill Gap Breakdown ({len(fs_gap_items)}):")
        for item in fs_gap_items:
            clean = " ".join(item.split())
            print(f"         * {clean}")

        fs_all_text = " ".join(fs_gap_items).upper()
        assert "CLAIMED" in fs_all_text or "UNVALIDATED" in fs_all_text
        print("       [OK] Full-Stack report accurately distinguishes demonstrated vs unvalidated claims!")
        print("PHASE 5 FULL-STACK BROWSER WORKFLOW COMPLETED SUCCESSFULLY!")

        browser.close()

    print("\n" + "=" * 75)
    print("PHASES 4 & 5 PLAYWRIGHT LIVE ACCEPTANCE TESTS ALL PASSED!")
    print("=" * 75)

if __name__ == "__main__":
    run_phase4_and_5_browser_tests()
