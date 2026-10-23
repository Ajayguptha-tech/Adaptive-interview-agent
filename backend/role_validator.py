"""
Strict Role Validation Engine.
Validates candidate job role inputs against deterministic structural rules,
technical taxonomy, gibberish detection heuristics, and contextual validity.
Rejects arbitrary, meaningless, random, or irrelevant text.
"""

import re
from typing import Tuple, Optional, Set

INVALID_ROLE_ERROR_MESSAGE = (
    "Please enter a valid job role, such as Python Developer, Software Engineer, or Data Analyst."
)

# Common gibberish, greetings, keyboard walks, and non-job placeholders
ROLE_BLACKLIST: Set[str] = {
    "asdf",
    "asdfg",
    "asdfgh",
    "asdfghjkl",
    "qwerty",
    "qwertyuiop",
    "zxcv",
    "zxcvbnm",
    "hello",
    "hi",
    "hey",
    "test",
    "testing",
    "tester123",
    "random",
    "none",
    "null",
    "undefined",
    "n/a",
    "na",
    "admin",
    "administrator123",
    "user",
    "root",
    "sample",
    "temp",
    "foo",
    "bar",
    "baz",
    "blah",
    "stuff",
    "thing",
    "someone",
    "nobody",
    "whatever",
    "idk",
    "nothing",
    "abc",
    "abcd",
    "xyz",
    "123456",
    "pass",
    "fail",
    "role",
    "job",
    "work",
    "title",
    "human",
    "candidate",
    "person",
    "applicant",
    "myself",
    "me",
}

# Recognized role nouns that define legitimate professional and technical occupations
ROLE_NOUNS: Set[str] = {
    "engineer",
    "developer",
    "architect",
    "analyst",
    "specialist",
    "consultant",
    "scientist",
    "administrator",
    "programmer",
    "designer",
    "manager",
    "lead",
    "technician",
    "auditor",
    "strategist",
    "coordinator",
    "officer",
    "practitioner",
    "evaluator",
    "director",
    "head",
    "expert",
    "coder",
    "researcher",
    "intern",
    "apprentice",
    "fellow",
}

# Recognized technical / professional domains
KNOWN_DOMAINS: Set[str] = {
    "software",
    "web",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "fullstack",
    "full stack",
    "full-stack",
    "mobile",
    "ios",
    "android",
    "cloud",
    "data",
    "machine learning",
    "ml",
    "ai",
    "artificial intelligence",
    "deep learning",
    "nlp",
    "computer vision",
    "devops",
    "mlops",
    "devsecops",
    "sre",
    "site reliability",
    "security",
    "cybersecurity",
    "infosec",
    "database",
    "db",
    "dba",
    "sql",
    "systems",
    "network",
    "platform",
    "infrastructure",
    "qa",
    "quality assurance",
    "test",
    "automation",
    "sdet",
    "embedded",
    "firmware",
    "iot",
    "blockchain",
    "web3",
    "game",
    "graphics",
    "ui",
    "ux",
    "ui/ux",
    "product",
    "scrum",
    "agile",
    "python",
    "javascript",
    "typescript",
    "java",
    "c++",
    "c#",
    ".net",
    "golang",
    "go",
    "rust",
    "php",
    "ruby",
    "scala",
    "kotlin",
    "swift",
    "react",
    "node",
    "nodejs",
    "django",
    "flask",
    "fastapi",
    "spring",
    "angular",
    "vue",
    "bi",
    "business intelligence",
    "etl",
    "big data",
    "robotics",
}

# Recognized legitimate acronym roles
LEGITIMATE_ACRONYMS: Set[str] = {
    "sre",
    "sdet",
    "dba",
    "qa",
    "pm",
    "tpm",
    "cto",
    "cio",
    "ciso",
    "devops",
    "mlops",
    "sysadmin",
}

# Conversational sentence indicators that belong in chat, not a job role
CONVERSATIONAL_STOPWORDS: Set[str] = {
    "i",
    "am",
    "want",
    "to",
    "be",
    "a",
    "an",
    "the",
    "please",
    "hire",
    "me",
    "looking",
    "for",
    "job",
    "this",
    "that",
    "my",
    "is",
    "are",
    "can",
    "you",
    "hello",
    "world",
    "yesterday",
    "tomorrow",
    "today",
    "working",
    "at",
    "in",
}


class RoleValidator:
    """Deterministic validation pipeline for job and candidate roles."""

    @classmethod
    def normalize_role(cls, role: str) -> str:
        """Trims whitespace, collapses internal spaces, and cleans punctuation."""
        if not role:
            return ""
        # Strip surrounding whitespace and common trailing/leading punctuation
        cleaned = role.strip().strip(".,;:!?~`'\"")
        # Collapse multiple spaces into one
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @classmethod
    def validate_role(
        cls,
        role: Optional[str],
        is_required: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates target job role input.
        Returns: (is_valid, normalized_role, error_message)

        If role is empty:
          - if is_required=True: returns (False, None, error_message)
          - if is_required=False: returns (True, None, None) [optional input]
        """
        if role is None or not str(role).strip():
            if is_required:
                return (False, None, INVALID_ROLE_ERROR_MESSAGE)
            return (True, None, None)

        normalized = cls.normalize_role(str(role))

        # 1. Length checks
        if len(normalized) < 2:
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)
        if len(normalized) > 70:
            return (
                False,
                normalized,
                f"{INVALID_ROLE_ERROR_MESSAGE} Input exceeds maximum allowed length (70 characters).",
            )

        # 2. Reject if no alphabetic characters or purely digits/symbols
        if not re.search(r"[a-zA-Z]", normalized):
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        if re.match(r"^[\d\s]+$", normalized):
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # 3. Reject forbidden symbols (allow '+', '#', '/', '-', '.', '&')
        if re.search(r"[!@$%^*_={}<>?\\]", normalized):
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # 4. Check for repeated characters (e.g., "aaaaa", "zzzz", "!!!!", "zzz")
        if re.search(r"([a-zA-Z])\1{2,}", normalized):
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # 5. Check blacklist (single word or whole phrase)
        lower_role = normalized.lower()
        if lower_role in ROLE_BLACKLIST:
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # 6. Check legitimate short acronyms (e.g., SRE, SDET, QA, PM, DBA)
        clean_alpha_lower = re.sub(r"[^a-zA-Z]", "", lower_role)
        if clean_alpha_lower in LEGITIMATE_ACRONYMS:
            return (True, normalized.upper() if len(normalized) <= 4 else normalized.title(), None)

        words = [w.strip() for w in re.split(r"[\s/\-]+", lower_role) if w.strip()]
        if not words:
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # If any word is an exact blacklist match in a short input
        if len(words) <= 2 and any(w in ROLE_BLACKLIST for w in words):
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # 7. Check for conversational sentence patterns or excessively wordy inputs
        for stopword in ("about", "weather", "sentence", "sentences", "words", "unrelated", "random", "would", "like", "apply"):
            CONVERSATIONAL_STOPWORDS.add(stopword)

        stopword_count = sum(1 for w in words if w in CONVERSATIONAL_STOPWORDS)
        if len(words) >= 4 and stopword_count >= 1:
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        if len(words) > 4 and not any(w in ROLE_NOUNS for w in words):
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # Detect stacked role titles without a domain (e.g. "developer engineer architect manager")
        role_noun_count = sum(1 for w in words if w in ROLE_NOUNS)
        has_domain_word = any(w in KNOWN_DOMAINS for w in words)
        if role_noun_count >= 3 and not has_domain_word:
            return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # 8. Gibberish heuristics
        for word in words:
            clean_word = re.sub(r"[^a-zA-Z]", "", word)
            if not clean_word:
                continue

            # Keyboard walk checks (home row, qwerty)
            if any(walk in clean_word for walk in ("asdf", "qwer", "zxcv", "hjkl")):
                return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

            # Excessive consecutive consonants (e.g., "sdfgh", "ghjkl", "bcdfgh")
            if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", clean_word):
                return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

            # Vowel presence check for tokens (words of length >= 2 must contain vowels unless recognized acronym or domain)
            if (
                len(clean_word) >= 2
                and clean_word not in LEGITIMATE_ACRONYMS
                and clean_word not in KNOWN_DOMAINS
                and clean_word not in {"c", "r"}
            ):
                has_vowel = bool(re.search(r"[aeiouy]", clean_word))
                if not has_vowel:
                    return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

        # 9. Positive matching against known domains and role nouns
        has_role_noun = any(w in ROLE_NOUNS for w in words)
        has_domain = any(w in KNOWN_DOMAINS for w in words) or any(
            d in lower_role for d in KNOWN_DOMAINS if " " in d
        )

        # If it has a known domain or a role noun
        if has_role_noun or has_domain:
            # If it's a single word, it must be either an explicit role noun, known domain, or legitimate acronym
            if len(words) == 1:
                clean_single = re.sub(r"[^a-zA-Z]", "", words[0])
                if (
                    clean_single not in ROLE_NOUNS
                    and clean_single not in KNOWN_DOMAINS
                    and clean_single not in LEGITIMATE_ACRONYMS
                ):
                    return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)

            title_case = " ".join(
                w.upper() if w.lower() in LEGITIMATE_ACRONYMS else w.capitalize()
                for w in normalized.split(" ")
            )
            return (True, title_case, None)

        # 10. Fallback contextual assessment for legitimate 2-3 word titles
        # Single-word inputs without domain or role noun are rejected (e.g., supercalifragilisticexpialidocious)
        if 2 <= len(words) <= 3:
            all_valid_tokens = True
            for word in words:
                clean_word = re.sub(r"[^a-zA-Z]", "", word)
                if not clean_word or len(clean_word) > 25:
                    all_valid_tokens = False
                    break
                vowels = len(re.findall(r"[aeiouy]", clean_word))
                if vowels == 0 and clean_word not in LEGITIMATE_ACRONYMS:
                    all_valid_tokens = False
                    break

            if all_valid_tokens and not any(w in ROLE_BLACKLIST for w in words):
                title_case = " ".join(
                    w.upper() if w.lower() in LEGITIMATE_ACRONYMS else w.capitalize()
                    for w in normalized.split(" ")
                )
                return (True, title_case, None)

        return (False, normalized, INVALID_ROLE_ERROR_MESSAGE)
