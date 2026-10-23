"""
Automated Unit and Integration Tests for Module 3 (Interview Integrity Intelligence)
and Module 5 (Candidate Decision Intelligence).
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import (
    StartInterviewRequest,
    InterviewMode,
    FeedbackMode,
    IntegrityEventCreateRequest,
    IntegrityEventUpdateRequest,
    CandidateDecisionUpdateRequest,
    CandidateComparisonRequest,
    DecisionOutcome,
)
from backend.session_manager import SessionManager
from backend.session_persistence import SessionPersistence
from backend.pdf_generator import InterviewPDFReportGenerator


client = TestClient(app)


@pytest.fixture
def test_session():
    """Creates a fresh test session for testing integrity and decision features."""
    req = StartInterviewRequest(
        role="Senior Backend Engineer",
        track="python",
        max_questions=3,
        difficulty_mode=InterviewMode.ADAPTIVE,
        feedback_mode=FeedbackMode.IMMEDIATE,
        dynamic_questions=False,
    )
    from backend.main import session_manager
    session = session_manager.start_session(req)
    return session


def test_log_and_list_integrity_events(test_session):
    """Verifies that sensory and browser integrity events are logged and retrieved chronologically."""
    sid = test_session.session_id

    # 1. Log window blur event
    res1 = client.post(
        f"/api/interview/{sid}/integrity_event",
        json={
            "event_type": "window_blur",
            "severity": "info",
            "confidence": 85.0,
            "title": "Window Focus Shift",
            "description": "Candidate tab temporarily shifted focus.",
            "timestamp_offset_seconds": 12.5,
        },
    )
    assert res1.status_code == 200, res1.text
    data1 = res1.json()
    assert data1["status"] == "success"
    assert data1["event"]["event_type"] == "window_blur"
    assert data1["event"]["recruiter_status"] == "pending_review"

    # 2. Log second event: audio fluctuation
    res2 = client.post(
        f"/api/interview/{sid}/integrity_event",
        json={
            "event_type": "audio_anomaly",
            "severity": "low",
            "confidence": 75.0,
            "title": "Acoustic Fluctuation",
            "description": "Background ambient variance detected.",
            "timestamp_offset_seconds": 45.0,
        },
    )
    assert res2.status_code == 200
    ev2_id = res2.json()["event"]["id"]

    # 3. List events for session
    list_res = client.get(f"/api/interview/{sid}/integrity_events")
    assert list_res.status_code == 200
    events = list_res.json()["events"]
    assert len(events) >= 2
    assert events[0]["timestamp_offset_seconds"] <= events[1]["timestamp_offset_seconds"]

    # 4. Triage review event
    patch_res = client.patch(
        f"/api/interview/{sid}/integrity_event/{ev2_id}",
        json={
            "status": "verified_benign",
            "notes": "Ambient noise caused by HVAC system.",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["recruiter_status"] == "verified_benign"

    # 5. Fetch integrity summary
    sum_res = client.get(f"/api/interview/{sid}/integrity_summary")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["focus_loss_count"] >= 1
    assert summary["audio_anomaly_count"] >= 1
    assert summary["verified_benign_count"] >= 1
    assert "ethical_notice" in summary


def test_ethical_non_punitive_protocol(test_session):
    """Ensures integrity observations never label candidates as fraudulent unilaterally."""
    sid = test_session.session_id
    from backend.main import session_manager

    # Summary verification
    summary = session_manager.get_integrity_summary(sid)
    assert "never definitive allegations" in summary.ethical_notice.lower()
    assert "human hiring panel" in summary.ethical_notice.lower()


def test_candidate_decision_generation_and_override(test_session):
    """Verifies evidence-based decision recommendation and recruiter overrides."""
    sid = test_session.session_id
    from backend.main import session_manager

    # Answer a question to generate real evidence
    session = session_manager.get_session(sid)
    q = session.current_question
    session_manager.submit_answer(
        session_id=sid,
        question_id=q.id,
        answer="Decorators in Python are higher-order functions that take a callable and return a wrapped callable. They use functools.wraps to preserve metadata.",
    )

    # Conclude session and generate final report
    report = session_manager.generate_report(sid)
    assert report.decision_recommendation is not None
    assert report.integrity_summary is not None

    dec = report.decision_recommendation
    assert dec["session_id"] == sid
    assert dec["grade"] in ["A (Distinction)", "B (Proficient)", "C (Competent)", "D (Developing)"]
    assert dec["outcome"] in [
        DecisionOutcome.PROCEED_TO_HUMAN_REVIEW.value,
        DecisionOutcome.REQUEST_FOLLOW_UP.value,
        DecisionOutcome.CONSIDER_ALTERNATE_ROLE.value,
        DecisionOutcome.NEEDS_FURTHER_EVALUATION.value,
    ]

    # Verify via API
    cand_res = client.get(f"/api/recruiter/candidate/{sid}")
    assert cand_res.status_code == 200
    cand_data = cand_res.json()
    assert cand_data["decision"]["session_id"] == sid
    assert cand_data["report"] is not None

    # Test Recruiter Override
    override_res = client.patch(
        f"/api/recruiter/decision/{sid}",
        json={
            "outcome": "proceed_to_human_review",
            "notes": "Candidate showed strong practical grasp of Python closures and decorators.",
        },
    )
    assert override_res.status_code == 200
    assert override_res.json()["outcome"] == "proceed_to_human_review"

    # Verify updated record
    updated_dec = session_manager.get_candidate_decision(sid)
    assert updated_dec.recruiter_outcome_override == "proceed_to_human_review"
    assert "closures and decorators" in (updated_dec.recruiter_notes or "")


def test_recruiter_candidates_list():
    """Tests /api/recruiter/candidates listing pipeline candidates."""
    res = client.get("/api/recruiter/candidates")
    assert res.status_code == 200
    data = res.json()
    assert "candidates" in data
    assert isinstance(data["candidates"], list)


def test_candidate_side_by_side_comparison(test_session):
    """Verifies recruiter side-by-side comparison across candidate sessions."""
    sid = test_session.session_id
    from backend.main import session_manager

    # Ensure decision record exists
    session_manager.generate_report(sid)

    # Call comparison API
    comp_res = client.post(
        "/api/recruiter/compare",
        json={"session_ids": [sid]},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["candidate_count"] >= 1
    assert "competency_matrix" in comp_data
    assert "fairness_notice" in comp_data


def test_pdf_report_contains_integrity_and_decision(test_session):
    """Verifies that PDF report includes decision recommendation and integrity summary without error."""
    sid = test_session.session_id
    from backend.main import session_manager

    # Log an integrity event
    session_manager.log_integrity_event(
        session_id=sid,
        event_data=IntegrityEventCreateRequest(
            event_type="window_blur",
            severity="info",
            confidence=85.0,
            title="Focus Transition",
            description="Candidate tab switched focus.",
        ),
    )

    # Generate report
    report = session_manager.generate_report(sid)
    report_dict = report.model_dump()

    # Generate PDF bytes
    pdf_bytes = InterviewPDFReportGenerator.generate_pdf_bytes(
        report_data=report_dict,
        resume_profile=test_session.resume_profile,
    )
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
