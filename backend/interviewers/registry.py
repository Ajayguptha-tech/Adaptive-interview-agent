"""
Interviewer Registry and Factory.
Manages domain-specific interviewer models ('python', 'fullstack').
Explicitly rejects unknown track identifiers without silent fallback.
"""

from typing import Dict, Any, List
from backend.interviewers.base import BaseInterviewer
from backend.interviewers.python_interviewer import PythonInterviewer
from backend.interviewers.fullstack_interviewer import FullStackInterviewer


class InterviewerRegistry:
    """Registry maintaining active interviewer models."""

    def __init__(self):
        self._interviewers: Dict[str, BaseInterviewer] = {
            "python": PythonInterviewer(),
            "fullstack": FullStackInterviewer(),
        }

    def register(self, track: str, interviewer: BaseInterviewer) -> None:
        """Registers or replaces an interviewer model for a track."""
        clean_track = track.strip().lower()
        self._interviewers[clean_track] = interviewer

    def get(self, track: str) -> BaseInterviewer:
        """
        Retrieves the interviewer for the specified track.
        Raises ValueError if track is unrecognized. NEVER silently falls back.
        """
        if not track or not isinstance(track, str):
            track = "python"
        clean_track = track.strip().lower()

        if clean_track not in self._interviewers:
            valid = list(self._interviewers.keys())
            raise ValueError(
                f"Unknown interviewer track '{track}'. Supported tracks are: {valid}."
            )
        return self._interviewers[clean_track]

    def list_tracks(self) -> List[Dict[str, Any]]:
        """Returns metadata for all supported tracks."""
        return [
            {
                "id": "python",
                "title": "Python Interviewer",
                "badge": "Python Track",
                "description": "Practice Python programming through adaptive technical questions, conceptual discussions, output prediction, debugging, and coding challenges.",
                "topics": self._interviewers["python"].get_topics_and_competencies()["topics"],
                "competencies": self._interviewers["python"].get_topics_and_competencies()["competencies"],
            },
            {
                "id": "fullstack",
                "title": "Full-Stack Interviewer",
                "badge": "Full-Stack Track",
                "description": "Evaluate frontend, backend, database, API integration, debugging, and complete web application development skills.",
                "topics": self._interviewers["fullstack"].get_topics_and_competencies()["topics"],
                "competencies": self._interviewers["fullstack"].get_topics_and_competencies()["competencies"],
                "tech_stacks": self._interviewers["fullstack"].get_topics_and_competencies().get("tech_stacks", []),
            },
        ]


default_registry = InterviewerRegistry()
