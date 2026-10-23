"""
Comprehensive test suite for Strict Role Validation.
Validates:
1. Valid roles (Python Developer, Software Engineer, Full Stack Developer, Data Analyst, etc.)
2. Invalid roles (asdfghjkl, qwerty, hello, 123456, !!!!, random sentences, empty, too long)
3. Legitimate unfamiliar roles (e.g., Site Reliability Engineer, Distributed Systems Engineer, Platform Architect)
4. Non-silent rejection on backend API endpoints (/api/role/validate, /api/resume/upload, /api/interview/prepare)
5. Ensuring no fallback role is silently accepted when validation fails.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.role_validator import RoleValidator
from backend.models import PrepareInterviewRequest, StartInterviewRequest

client = TestClient(app)

KNOWN_VALID_ROLES = [
    "Python Developer",
    "Software Engineer",
    "Full Stack Developer",
    "Backend Developer",
    "Frontend Developer",
    "Data Analyst",
    "Machine Learning Engineer",
    "AI Engineer",
    "DevOps Engineer",
    "Cybersecurity Analyst",
    "Database Engineer",
]

LEGITIMATE_UNFAMILIAR_ROLES = [
    "Site Reliability Engineer",
    "Cloud Solutions Architect",
    "Distributed Systems Specialist",
    "Platform Engineer",
    "NLP Researcher",
    "Firmware Developer",
    "Kubernetes Administrator",
    "Big Data Architect",
    "Computer Vision Scientist",
]

INVALID_ROLES = [
    ("asdfghjkl", "gibberish consonant clusters"),
    ("qwerty", "keyboard row pattern"),
    ("hello", "greeting"),
    ("123456", "pure numeric"),
    ("!!!!", "pure punctuation"),
    ("!@#$%^&*", "symbols only"),
    ("   ", "whitespace only"),
    ("", "empty"),
    ("Random unrelated sentences about the weather", "conversational sentence"),
    ("I would like to apply for any job you have available", "conversational sentence"),
    ("zzz xxx ccc vvv", "nonsense sequences"),
    ("developer engineer architect manager", "excessive stacked titles without domain"),
    ("a" * 85, "exceeding max length"),
    ("supercalifragilisticexpialidocious", "long nonsense word"),
]


class TestRoleValidatorDirect:
    """Direct unit tests for RoleValidator class."""

    @pytest.mark.parametrize("role", KNOWN_VALID_ROLES)
    def test_known_valid_roles_pass(self, role: str):
        is_valid, normalized, err = RoleValidator.validate_role(role, is_required=True)
        assert is_valid is True, f"Role '{role}' should be valid, but got error: {err}"
        assert normalized, f"Normalized role should not be empty for '{role}'"
        assert err is None

    @pytest.mark.parametrize("role", LEGITIMATE_UNFAMILIAR_ROLES)
    def test_legitimate_unfamiliar_roles_pass(self, role: str):
        is_valid, normalized, err = RoleValidator.validate_role(role, is_required=True)
        assert is_valid is True, f"Unfamiliar role '{role}' should be accepted as legitimate, but failed: {err}"
        assert normalized, f"Normalized role should not be empty for '{role}'"
        assert err is None

    @pytest.mark.parametrize("role,reason", INVALID_ROLES)
    def test_invalid_roles_rejected(self, role: str, reason: str):
        is_valid, normalized, err = RoleValidator.validate_role(role, is_required=True)
        assert is_valid is False, f"Role '{role}' ({reason}) should have been rejected"
        assert err is not None, f"Error message must be provided for '{role}'"
        assert "Please enter a valid job role" in err

    def test_optional_empty_role_behavior(self):
        """When role is optional, empty input returns valid=True with None."""
        is_valid, normalized, err = RoleValidator.validate_role("", is_required=False)
        assert is_valid is True
        assert normalized is None
        assert err is None

    def test_whitespace_trimming_and_casing(self):
        """Valid roles with trailing whitespace or varied casing are normalized."""
        is_valid, normalized, err = RoleValidator.validate_role("   python developer   ", is_required=True)
        assert is_valid is True
        assert normalized == "Python Developer"
        assert err is None


class TestRoleValidationAPI:
    """API endpoint verification for role validation."""

    def test_api_role_validate_valid(self):
        resp = client.get("/api/role/validate", params={"role": "Backend Developer"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["normalized_role"] == "Backend Developer"
        assert data["error_message"] is None

    @pytest.mark.parametrize("invalid_role", ["asdfghjkl", "qwerty", "hello", "123456", "!!!!"])
    def test_api_role_validate_invalid(self, invalid_role: str):
        resp = client.get("/api/role/validate", params={"role": invalid_role})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert data["normalized_role"] is None
        assert "Please enter a valid job role" in data["error_message"]

    def test_upload_resume_rejects_invalid_role(self):
        sample_resume = b"Alex Morgan\nExperienced Python developer with 5 years experience in FastAPI and SQL."
        files = {"file": ("test_resume.txt", sample_resume, "text/plain")}
        data = {"target_role": "asdfghjkl"}

        resp = client.post("/api/resume/upload", files=files, data=data)
        assert resp.status_code == 422
        json_data = resp.json()
        assert "Please enter a valid job role" in json_data["detail"]

    def test_upload_resume_accepts_valid_role(self):
        sample_resume = b"Alex Morgan\nExperienced Python developer with 5 years experience in FastAPI and SQL."
        files = {"file": ("test_resume.txt", sample_resume, "text/plain")}
        data = {"target_role": "Python Developer"}

        resp = client.post("/api/resume/upload", files=files, data=data)
        assert resp.status_code == 200
        json_data = resp.json()
        assert json_data["target_role"] == "Python Developer"

    def test_upload_resume_accepts_empty_optional_role(self):
        """When no target role is passed, system infers from resume without error."""
        sample_resume = b"Alex Morgan\nExperienced Python developer with 5 years experience in FastAPI and SQL."
        files = {"file": ("test_resume.txt", sample_resume, "text/plain")}
        data = {}

        resp = client.post("/api/resume/upload", files=files, data=data)
        assert resp.status_code == 200
        json_data = resp.json()
        assert json_data["is_success"] is True

    def test_pydantic_model_rejects_invalid_role(self):
        with pytest.raises(ValueError) as excinfo:
            PrepareInterviewRequest(
                resume_id="test_id",
                target_role="qwerty",
            )
        assert "Please enter a valid job role" in str(excinfo.value)

    def test_pydantic_start_model_rejects_invalid_role(self):
        with pytest.raises(ValueError) as excinfo:
            StartInterviewRequest(
                role="123456",
            )
        assert "Please enter a valid job role" in str(excinfo.value)
