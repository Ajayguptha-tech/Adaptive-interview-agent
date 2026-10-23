"""
Test suite validating multi-user security, candidate data isolation,
and 403 Forbidden rejection when mismatched candidates access private sessions.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_candidate_session_isolation_and_rejection():
    """Verify that Candidate B cannot submit answers or retrieve reports for Candidate A's session."""
    # Candidate A starts session
    start_res = client.post(
        "/api/interview/start",
        json={
            "candidate_id": "candidate_alice",
            "track": "python",
            "max_questions": 5,
            "dynamic_questions": False,
        },
    )
    assert start_res.status_code == 200
    data = start_res.json()
    session_id = data["session_id"]
    alice_token = data.get("session_token")
    assert data["candidate_id"] == "candidate_alice"
    assert alice_token is not None

    # Candidate A can access their session with valid headers
    alice_headers = {
        "X-Candidate-ID": "candidate_alice",
        "X-Session-Token": alice_token,
    }
    get_res = client.get(f"/api/interview/{session_id}", headers=alice_headers)
    assert get_res.status_code == 200

    # Candidate B tries to access Alice's session with mismatched candidate ID
    bob_headers = {
        "X-Candidate-ID": "candidate_bob",
        "X-Session-Token": alice_token,
    }
    forbidden_get = client.get(f"/api/interview/{session_id}", headers=bob_headers)
    assert forbidden_get.status_code == 403
    assert "Forbidden" in forbidden_get.json()["detail"]

    # Candidate B tries to submit an answer to Alice's session
    forbidden_ans = client.post(
        f"/api/interview/{session_id}/answer",
        json={"answer": "Malicious or unauthorized submission attempt."},
        headers=bob_headers,
    )
    assert forbidden_ans.status_code == 403

    # Candidate B tries to download Alice's PDF report
    forbidden_pdf = client.get(
        f"/api/interview/{session_id}/pdf",
        headers=bob_headers,
    )
    assert forbidden_pdf.status_code == 403

    # Invalid session token is rejected
    tampered_headers = {
        "X-Candidate-ID": "candidate_alice",
        "X-Session-Token": "tampered_invalid_token_xyz",
    }
    tampered_res = client.get(f"/api/interview/{session_id}", headers=tampered_headers)
    assert tampered_res.status_code == 403


def test_pdf_download_with_query_tokens():
    """Verify that PDF download endpoint validates query param authentication."""
    start_res = client.post(
        "/api/interview/start",
        json={
            "candidate_id": "candidate_carol",
            "track": "python",
            "max_questions": 5,
            "dynamic_questions": False,
        },
    )
    assert start_res.status_code == 200
    data = start_res.json()
    session_id = data["session_id"]
    carol_token = data.get("session_token")

    # Access with matching query tokens
    valid_pdf = client.get(
        f"/api/interview/{session_id}/pdf?candidate_id=candidate_carol&token={carol_token}"
    )
    assert valid_pdf.status_code == 200
    assert valid_pdf.headers["content-type"] == "application/pdf"
    assert len(valid_pdf.content) > 1000

    # Access with mismatched query tokens returns 403
    invalid_pdf = client.get(
        f"/api/interview/{session_id}/pdf?candidate_id=candidate_eve&token={carol_token}"
    )
    assert invalid_pdf.status_code == 403
