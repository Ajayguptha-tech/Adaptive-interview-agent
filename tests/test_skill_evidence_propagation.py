"""
Regression Test Suite for Skill Evidence Propagation and Classification.
Covers all 7 mandatory regression scenarios:
1. A correct answer with 4.5/5 and the matching skill target.
2. An incorrect answer with 0/5.
3. Multiple questions testing the same skill.
4. A question with missing or incorrect target metadata.
5. Early interview termination.
6. Skills that were never assessed (claimed vs unclaimed).
7. Python and Full-Stack report skill gap validation.
Plus: Code execution failure safeguard verification.
"""

import pytest
from backend.resume_analyzer.skill_gap import SkillGapAnalyzer, SkillStatus, SkillEvidenceItem


@pytest.fixture
def sample_resume_profile():
    return {
        "candidate_name": "Jordan Dev",
        "filename": "jordan_resume.pdf",
        "total_experience_years": 4.0,
        "skills": ["Python", "FastAPI", "React", "Docker", "SQL"],
        "skill_evidence": [
            {
                "skill": "Python",
                "source": "experience",
                "evidence_snippet": "Built core backend microservices in Python 3.11",
                "confidence": 0.95,
            },
            {
                "skill": "FastAPI",
                "source": "experience",
                "evidence_snippet": "Engineered REST APIs with FastAPI and Pydantic",
                "confidence": 0.9,
            },
        ],
        "job_matching": {
            "missing_required": ["Kubernetes"],
            "missing_preferred": ["GraphQL"],
        },
    }


# =============================================================================
# SCENARIO 1: Correct Answer with 4.5/5 and Matching Skill Target -> DEMONSTRATED
# =============================================================================
def test_scenario_1_high_scoring_answer_produces_demonstrated_skill(sample_resume_profile):
    history = [
        {
            "question_number": 1,
            "question_id": "py-q1",
            "topic": "Data Structures & Mutability",
            "competency": "Python Fundamentals",
            "target_skills": ["Python"],
            "question_text": "Explain list vs tuple mutability in Python.",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "correctness_status": "correct",
            "summary": "Outstanding answer demonstrating list and tuple mechanics.",
        }
    ]

    report = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, history, track="python")
    py_skill = next((s for s in report.skills if s.skill_name.lower() == "python"), None)

    assert py_skill is not None
    assert py_skill.status == SkillStatus.DEMONSTRATED
    assert py_skill.score_percentage == 90.0
    assert len(py_skill.interview_evidence) == 1
    assert "Q#1" in py_skill.verdict
    assert report.demonstrated_count >= 1
    assert "Python" in report.demonstrated_skills


# =============================================================================
# SCENARIO 2: Incorrect Answer with 0/5 -> NOT_DEMONSTRATED
# =============================================================================
def test_scenario_2_zero_score_answer_produces_not_demonstrated(sample_resume_profile):
    history = [
        {
            "question_number": 1,
            "question_id": "py-q1",
            "topic": "Data Structures & Mutability",
            "competency": "Python Fundamentals",
            "target_skills": ["Python"],
            "question_text": "Explain list vs tuple mutability.",
            "awarded_marks": 0.0,
            "max_marks": 5.0,
            "percentage": 0.0,
            "correctness_status": "incorrect",
            "summary": "Candidate could not answer.",
        }
    ]

    report = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, history, track="python")
    py_skill = next((s for s in report.skills if s.skill_name.lower() == "python"), None)

    assert py_skill is not None
    assert py_skill.status == SkillStatus.NOT_DEMONSTRATED
    assert py_skill.score_percentage == 0.0
    assert "below passing standard" in py_skill.verdict
    assert "Python" in report.not_demonstrated_skills


# =============================================================================
# SCENARIO 3: Multiple Questions Testing the Same Skill
# =============================================================================
def test_scenario_3_multiple_questions_same_skill_positive_and_negative(sample_resume_profile):
    # Case A: Two strong answers (4.5/5 and 4.0/5) -> Average 85% -> DEMONSTRATED
    history_pass = [
        {
            "question_number": 1,
            "target_skills": ["Python"],
            "topic": "Data Structures & Mutability",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "correctness_status": "correct",
        },
        {
            "question_number": 2,
            "target_skills": ["Python"],
            "topic": "Generators & Lazy Evaluation",
            "awarded_marks": 4.0,
            "max_marks": 5.0,
            "percentage": 80.0,
            "correctness_status": "correct",
        },
    ]
    report_pass = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, history_pass, track="python")
    py_pass = next(s for s in report_pass.skills if s.skill_name.lower() == "python")
    assert py_pass.status == SkillStatus.DEMONSTRATED
    assert py_pass.score_percentage == 85.0
    assert len(py_pass.interview_evidence) == 2

    # Case B: One strong (4.5/5 = 90%) and one zero (0.0/5 = 0%) -> Average 45% -> NOT_DEMONSTRATED
    history_fail = [
        {
            "question_number": 1,
            "target_skills": ["Python"],
            "topic": "Data Structures & Mutability",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "correctness_status": "correct",
        },
        {
            "question_number": 2,
            "target_skills": ["Python"],
            "topic": "Generators & Lazy Evaluation",
            "awarded_marks": 0.0,
            "max_marks": 5.0,
            "percentage": 0.0,
            "correctness_status": "incorrect",
        },
    ]
    report_fail = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, history_fail, track="python")
    py_fail = next(s for s in report_fail.skills if s.skill_name.lower() == "python")
    assert py_fail.status == SkillStatus.NOT_DEMONSTRATED
    assert py_fail.score_percentage == 45.0
    assert len(py_fail.interview_evidence) == 2


# =============================================================================
# SCENARIO 4: Missing or Incorrect Target Metadata Fallback Handling
# =============================================================================
def test_scenario_4_missing_target_metadata_falls_back_to_topic_without_cross_contamination(sample_resume_profile):
    history = [
        # Question with empty target_skills, but topic is explicitly Data Structures & Mutability
        {
            "question_number": 1,
            "target_skills": [],
            "topic": "Data Structures & Mutability",
            "competency": "Python Fundamentals",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "correctness_status": "correct",
        },
        # Question with unrelated topic (e.g. Concurrency & GIL), scoring 0/5
        {
            "question_number": 2,
            "target_skills": [],
            "topic": "Concurrency & GIL",
            "competency": "Python Fundamentals",
            "awarded_marks": 0.0,
            "max_marks": 5.0,
            "percentage": 0.0,
            "correctness_status": "incorrect",
        },
    ]

    report = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, history, track="python")
    py_skill = next(s for s in report.skills if s.skill_name.lower() == "python")

    # Q1 matches Python via topic synonym "Data Structures & Mutability"
    # Q2 (Concurrency & GIL) MUST NOT contaminate Python through generic "Python Fundamentals" competency
    assert py_skill.status == SkillStatus.DEMONSTRATED
    assert py_skill.score_percentage == 90.0
    assert len(py_skill.interview_evidence) == 1
    assert py_skill.interview_evidence[0]["question_number"] == 1


# =============================================================================
# SCENARIO 5: Early Interview Termination
# =============================================================================
def test_scenario_5_early_interview_termination_preserves_partial_evidence(sample_resume_profile):
    # Only Q1 was completed before early termination
    history = [
        {
            "question_number": 1,
            "target_skills": ["Python"],
            "topic": "Data Structures & Mutability",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "correctness_status": "correct",
        }
    ]

    report = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, history, track="python")

    # Python demonstrated
    assert "Python" in report.demonstrated_skills

    # Unanswered resume skills remain CLAIMED_UNVALIDATED
    assert "FastAPI" in report.claimed_unvalidated_skills
    assert "React" in report.claimed_unvalidated_skills
    assert "Docker" in report.claimed_unvalidated_skills
    assert "SQL" in report.claimed_unvalidated_skills


# =============================================================================
# SCENARIO 6: Skills That Were Never Assessed
# =============================================================================
def test_scenario_6_unassessed_skills_distinguish_claimed_vs_not_assessed(sample_resume_profile):
    # No questions asked at all
    report = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, [], track="python")

    # All resume skills are CLAIMED_UNVALIDATED
    for claimed in ["FastAPI", "React", "Docker", "SQL"]:
        assert claimed in report.claimed_unvalidated_skills

    # JD required/preferred skills NOT on the resume are NOT_ASSESSED
    assert "Kubernetes" in report.not_assessed_skills
    assert "GraphQL" in report.not_assessed_skills

    k8s = next(s for s in report.skills if s.skill_name == "Kubernetes")
    assert k8s.status == SkillStatus.NOT_ASSESSED
    assert k8s.score_percentage is None


# =============================================================================
# SCENARIO 7: Python and Full-Stack Track Reports
# =============================================================================
def test_scenario_7_python_and_fullstack_track_reports(sample_resume_profile):
    # Full-Stack session testing JavaScript and React
    fs_history = [
        {
            "question_number": 1,
            "target_skills": ["JavaScript"],
            "topic": "JavaScript Core",
            "competency": "Full-Stack Technical Competency",
            "awarded_marks": 4.5,
            "max_marks": 5.0,
            "percentage": 90.0,
            "correctness_status": "correct",
        },
        {
            "question_number": 2,
            "target_skills": ["React"],
            "topic": "React & Component Architecture",
            "competency": "Full-Stack Technical Competency",
            "awarded_marks": 4.0,
            "max_marks": 5.0,
            "percentage": 80.0,
            "correctness_status": "correct",
        },
    ]

    fs_report = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, fs_history, track="fullstack")
    assert "React" in fs_report.demonstrated_skills
    react_item = next(s for s in fs_report.skills if s.skill_name == "React")
    assert react_item.status == SkillStatus.DEMONSTRATED
    assert react_item.score_percentage == 80.0


# =============================================================================
# ADDITIONAL SAFEGUARD: Code Execution Failure Cannot Count as Demonstrated
# =============================================================================
def test_code_execution_failure_cannot_count_as_demonstrated(sample_resume_profile):
    history_exec_fail = [
        {
            "question_number": 1,
            "target_skills": ["Python"],
            "topic": "Data Structures & Mutability",
            "awarded_marks": 4.0,
            "max_marks": 5.0,
            "percentage": 80.0,  # High marks on syntax/style, but failed tests
            "correctness_status": "failed_execution",
            "execution_result": {
                "all_passed": False,
                "passed": 1,
                "failed": 2,
                "syntax_valid": True,
            },
        }
    ]

    report = SkillGapAnalyzer.analyze_skill_gap(sample_resume_profile, history_exec_fail, track="python")
    py_skill = next(s for s in report.skills if s.skill_name.lower() == "python")
    assert py_skill.status == SkillStatus.NOT_DEMONSTRATED
    assert "execution failure" in py_skill.verdict
