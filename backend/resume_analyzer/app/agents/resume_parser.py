"""Agent 1: Resume Parser & Understanding Agent.
Extracts contact details, sections, experience, education, skills (explicit vs inferred),
projects, certifications, achievements, and languages from normalized text into structured Pydantic models.
"""
import re
from typing import List, Dict, Tuple, Optional, Set
from ..schemas.resume import (
    ContactInfo,
    EducationItem,
    WorkExperienceItem,
    ProjectItem,
    CertificationItem,
    AchievementItem,
    LanguageItem,
    SkillEvidenceItem,
    ResumeParsedData,
)


# Known section header markers
SECTION_PATTERNS = {
    "summary": [
        r"^professional summary\b",
        r"^executive summary\b",
        r"^career summary\b",
        r"^professional profile\b",
        r"^career objective\b",
        r"^about me\b",
        r"^summary\b",
        r"^profile\b",
        r"^objective\b",
    ],
    "experience": [
        r"^work experience\b",
        r"^professional experience\b",
        r"^employment history\b",
        r"^work history\b",
        r"^career history\b",
        r"^relevant experience\b",
        r"^practical experience\b",
        r"^internships?\b",
        r"^internship experience\b",
        r"^experience\b",
    ],
    "education": [
        r"^academic background\b",
        r"^academic history\b",
        r"^academic qualifications\b",
        r"^education & credentials\b",
        r"^education and qualifications\b",
        r"^qualifications\b",
        r"^degrees?\b",
        r"^education\b",
    ],
    "skills": [
        r"^technical skills\b",
        r"^core competencies\b",
        r"^technical competencies\b",
        r"^skills & abilities\b",
        r"^skills and abilities\b",
        r"^tools & technologies\b",
        r"^tools and technologies\b",
        r"^key skills\b",
        r"^areas of expertise\b",
        r"^programming languages\b",
        r"^technologies\b",
        r"^tech stack\b",
        r"^skills\b",
    ],
    "projects": [
        r"^key projects\b",
        r"^personal projects\b",
        r"^academic projects\b",
        r"^selected projects\b",
        r"^technical projects\b",
        r"^project experience\b",
        r"^major projects\b",
        r"^coursework projects\b",
        r"^projects\b",
    ],
    "certifications": [
        r"^licenses & certifications\b",
        r"^licenses and certifications\b",
        r"^professional certifications?\b",
        r"^certifications?\b",
        r"^certificates?\b",
        r"^credentials?\b",
        r"^courses?\b",
        r"^licenses?\b",
    ],
    "achievements": [
        r"^honors & awards\b",
        r"^honors and awards\b",
        r"^key achievements?\b",
        r"^accomplishments?\b",
        r"^achievements?\b",
        r"^honors?\b",
        r"^awards?\b",
    ],
    "languages": [
        r"^language proficiency\b",
        r"^languages spoken\b",
        r"^languages?\b",
    ],
}

COMMON_TECH_SKILLS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "sql", "nosql", "postgresql", "mysql", "mongodb",
    "redis", "sqlite", "react", "react.js", "next.js", "vue", "angular", "node.js",
    "express", "fastapi", "django", "flask", "spring", "docker", "kubernetes", "aws",
    "azure", "gcp", "google cloud", "terraform", "ansible", "jenkins", "git", "github",
    "gitlab", "graphql", "rest api", "html5", "css3", "tailwind", "bootstrap",
    "linux", "bash", "ci/cd", "microservices", "agile", "scrum", "pandas", "numpy",
    "scikit-learn", "tensorflow", "pytorch", "machine learning", "deep learning", "nlp",
    "data analysis", "tableau", "power bi", "kafka", "rabbitmq", "celery", "elasticsearch"
]

KNOWN_LANGUAGES = [
    "english", "spanish", "french", "mandarin", "chinese", "german", "hindi",
    "japanese", "arabic", "portuguese", "russian", "italian", "korean", "dutch"
]


class ResumeParserAgent:
    """Agent 1: Extracts structured candidate information with evidence snippets and explicit/inferred skill separation."""

    def __init__(self):
        pass

    def parse(
        self,
        text: str,
        file_name: str = "Resume.pdf",
        is_scanned: bool = False,
        warning: str = "",
    ) -> ResumeParsedData:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        contact_info = self._extract_contact_info(text, lines)
        sections = self._segment_sections(lines)

        summary = self._extract_summary(sections.get("summary", []))
        experience = self._extract_experience(sections.get("experience", []))
        education = self._extract_education(sections.get("education", []))
        projects = self._extract_projects(sections.get("projects", []))
        certifications = self._extract_certifications(sections.get("certifications", []))
        achievements = self._extract_achievements(sections.get("achievements", []))
        languages = self._extract_languages(sections.get("languages", []))

        # Explicit vs Inferred Skills extraction
        explicit_skills_list, explicit_detailed = self._extract_explicit_skills(sections.get("skills", []))
        inferred_skills_list = self._extract_inferred_skills(experience, projects, summary)

        # Merge for all skills
        all_skills_detailed: List[SkillEvidenceItem] = []
        seen_skill_names: Set[str] = set()

        for item in explicit_detailed:
            low_name = item.name.lower()
            if low_name not in seen_skill_names:
                all_skills_detailed.append(item)
                seen_skill_names.add(low_name)

        for item in inferred_skills_list:
            low_name = item.name.lower()
            if low_name not in seen_skill_names:
                all_skills_detailed.append(item)
                seen_skill_names.add(low_name)

        # Flat combined skills list for backwards compatibility
        combined_skills = sorted(list({s.name for s in all_skills_detailed}), key=lambda s: s.lower())

        # Section detection verified by actual extracted data
        detected_sections: List[str] = []
        if contact_info.email or contact_info.phone:
            detected_sections.append("contact")
        if summary and len(summary.split()) >= 6:
            detected_sections.append("summary")
        if len(combined_skills) > 0:
            detected_sections.append("skills")
        if len(experience) > 0:
            detected_sections.append("experience")
        if len(education) > 0:
            detected_sections.append("education")
        if len(projects) > 0:
            detected_sections.append("projects")
        if len(certifications) > 0:
            detected_sections.append("certifications")
        if len(achievements) > 0:
            detected_sections.append("achievements")
        if len(languages) > 0:
            detected_sections.append("languages")

        # Retain any additional non-empty sections parsed from layout
        for s in sections.keys():
            if s not in detected_sections:
                detected_sections.append(s)

        expected_core = ["contact", "education", "skills", "experience", "projects"]
        missing_sections = [sec for sec in expected_core if sec not in detected_sections]

        word_count = len(text.split())
        char_count = len(text)

        return ResumeParsedData(
            raw_text=text,
            normalized_text=text,
            file_name=file_name,
            file_type="pdf" if file_name.lower().endswith(".pdf") else "docx",
            word_count=word_count,
            character_count=char_count,
            contact_info=contact_info,
            summary=summary,
            skills=combined_skills,
            explicit_skills=explicit_skills_list,
            inferred_skills=inferred_skills_list,
            all_skills_detailed=all_skills_detailed,
            experience=experience,
            education=education,
            projects=projects,
            certifications=certifications,
            achievements=achievements,
            languages=languages,
            detected_sections=detected_sections,
            missing_sections=missing_sections,
            is_scanned_pdf=is_scanned,
            warning_message=warning or None,
        )

    def _extract_contact_info(self, full_text: str, lines: List[str]) -> ContactInfo:
        # Email
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", full_text)
        email = email_match.group(0) if email_match else None

        # Phone
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}", full_text)
        phone = phone_match.group(0) if phone_match and len(re.sub(r"\D", "", phone_match.group(0))) >= 8 else None

        # LinkedIn
        linkedin_match = re.search(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/([a-zA-Z0-9_-]+)", full_text, re.IGNORECASE)
        linkedin = f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else None

        # GitHub
        github_match = re.search(r"(?:https?:\/\/)?(?:www\.)?github\.com\/([a-zA-Z0-9_-]+)", full_text, re.IGNORECASE)
        github = f"https://github.com/{github_match.group(1)}" if github_match else None

        # Website / Portfolio
        email_domain = email.split("@")[1].lower() if email and "@" in email else ""
        web_matches = re.finditer(r"(?<!@)\b(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9_-]+\.(?:dev|me|tech|io|org|app|portfolio|site|com))\b", full_text, re.IGNORECASE)
        website = None
        for m in web_matches:
            cand = m.group(0).strip()
            cand_low = cand.lower()
            if email_domain and email_domain in cand_low:
                continue
            if any(k in cand_low for k in ["linkedin.com", "github.com", "example.com", "gmail.com", "yahoo.com", "hotmail.com"]):
                continue
            website = cand if cand.startswith("http") else f"https://{cand}"
            break

        # Candidate name guess: first line with 1-4 words that isn't contact or section header
        name = None
        for line in lines[:5]:
            if "@" in line or "http" in line or re.search(r"\d{4,}", line):
                continue
            cleaned = re.sub(r"[^\w\s]", "", line).strip()
            low_line = line.strip().lower()
            # If line matches any section header pattern, skip it
            if any(re.match(pat, low_line) for pats in SECTION_PATTERNS.values() for pat in pats):
                continue
            if (
                1 <= len(cleaned.split()) <= 4
                and 2 <= len(cleaned) < 40
                and not any(
                    k in low_line
                    for k in [
                        "resume", "curriculum", "vitae", "summary", "profile",
                        "objective", "note:", "test", "candidate", "page",
                    ]
                )
            ):
                name = line.strip()
                break

        # Location heuristic: City, State or Country pattern
        location = None
        loc_match = re.search(r"([A-Z][a-zA-Z\s]+,\s*(?:[A-Z]{2}|[A-Z][a-zA-Z\s]+))", full_text[:600])
        if loc_match:
            candidate_loc = loc_match.group(1).strip()
            if len(candidate_loc.split()) <= 4:
                location = candidate_loc

        return ContactInfo(
            name=name,
            email=email,
            phone=phone,
            linkedin=linkedin,
            github=github,
            website=website,
            location=location,
        )

    def _segment_sections(self, lines: List[str]) -> Dict[str, List[str]]:
        sections: Dict[str, List[str]] = {}
        current_section = None

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            normalized_line = line_str.lower()
            # Clean leading markdown (#, ##) and bullet characters for header matching
            cleaned_header = re.sub(r"^[\#\*\-\•\:\s]+", "", normalized_line).strip()
            matched_section = None
            inline_content = ""

            # Check if this line starts a section heading
            for section_name, patterns in SECTION_PATTERNS.items():
                for pattern in patterns:
                    m = re.match(pattern, cleaned_header)
                    if m:
                        matched_section = section_name
                        # Check if line contains inline content after colon or delimiter
                        header_end = m.end()
                        rest = cleaned_header[header_end:].strip()
                        if rest.startswith(":") or rest.startswith("-") or rest.startswith("–") or rest.startswith("—") or rest.startswith("|"):
                            # Find matching position in original line
                            delim_idx = -1
                            for d in [":", "-", "–", "—", "|"]:
                                pos = line_str.find(d)
                                if pos != -1 and pos < len(line_str) - 1:
                                    delim_idx = pos
                                    break
                            if delim_idx != -1:
                                inline_content = line_str[delim_idx + 1:].strip()
                            else:
                                inline_content = line_str[header_end:].strip()
                        elif len(rest.split()) > 0 and len(rest) > 2:
                            inline_content = line_str[header_end:].strip()
                        break
                if matched_section:
                    break

            if matched_section:
                current_section = matched_section
                if current_section not in sections:
                    sections[current_section] = []
                if inline_content:
                    sections[current_section].append(inline_content)
            elif current_section:
                sections[current_section].append(line_str)

        # Only retain sections that have meaningful non-empty content
        meaningful_sections: Dict[str, List[str]] = {}
        for sec, sec_lines in sections.items():
            valid_lines = [
                l.strip() for l in sec_lines
                if len(l.strip()) > 1 and not re.match(r"^[\#\*\-\•\:\s]+$", l.strip())
            ]
            if valid_lines:
                meaningful_sections[sec] = valid_lines

        return meaningful_sections

    def _extract_summary(self, lines: List[str]) -> Optional[str]:
        if not lines:
            return None
        return " ".join(lines[:6]).strip()

    def _extract_explicit_skills(self, section_lines: List[str]) -> Tuple[List[str], List[SkillEvidenceItem]]:
        explicit_skills = set()
        detailed: List[SkillEvidenceItem] = []

        if section_lines:
            content = "\n".join(section_lines)
            tokens = re.split(r"[,•|\n;]+", content)
            for t in tokens:
                cleaned = t.strip()
                # Remove leading bullets or markers
                cleaned = re.sub(r"^[•\-*\u2022]\s*", "", cleaned)
                # If token has category label like "Languages: Python", extract value
                if ":" in cleaned and len(cleaned.split(":")[0]) < 25:
                    cleaned = cleaned.split(":")[-1].strip()
                if 1 <= len(cleaned) <= 35 and len(cleaned.split()) <= 4:
                    low_cleaned = cleaned.lower()
                    if not re.search(r"^(responsible|experienced|working|proficient in|note:|this is)\b", low_cleaned):
                        explicit_skills.add(cleaned)
                        detailed.append(
                            SkillEvidenceItem(
                                name=cleaned,
                                category="Explicit Section",
                                source="explicit",
                                is_explicit=True,
                                evidence_snippet=f"Listed in Skills section: '{cleaned}'",
                                confidence=1.0,
                            )
                        )

        sorted_explicit = sorted(list(explicit_skills), key=lambda s: s.lower())
        return sorted_explicit, detailed

    def _extract_inferred_skills(
        self,
        experiences: List[WorkExperienceItem],
        projects: List[ProjectItem],
        summary: Optional[str],
    ) -> List[SkillEvidenceItem]:
        inferred_map: Dict[str, SkillEvidenceItem] = {}

        # 1. Inspect Experience responsibilities
        for exp in experiences:
            role_label = f"{exp.job_title} at {exp.company}" if exp.company else (exp.job_title or "Work Experience")
            for bullet in exp.responsibilities:
                b_low = bullet.lower()
                for skill in COMMON_TECH_SKILLS:
                    pattern = r"\b" + re.escape(skill) + r"\b"
                    if re.search(pattern, b_low):
                        skill_name = skill.title() if not skill.isupper() else skill
                        if skill.lower() not in inferred_map:
                            inferred_map[skill.lower()] = SkillEvidenceItem(
                                name=skill_name,
                                category="Experience Demonstrated",
                                source="experience",
                                is_explicit=False,
                                evidence_snippet=f"Demonstrated in {role_label}: \"{bullet[:120]}\"",
                                confidence=0.95,
                            )
                        # Record in experience item inferred skills
                        if skill_name not in exp.inferred_skills:
                            exp.inferred_skills.append(skill_name)

        # 2. Inspect Projects
        for proj in projects:
            p_text = f"{proj.title} {proj.description or ''}".lower()
            for skill in COMMON_TECH_SKILLS:
                pattern = r"\b" + re.escape(skill) + r"\b"
                if re.search(pattern, p_text):
                    skill_name = skill.title() if not skill.isupper() else skill
                    if skill_name not in proj.technologies:
                        proj.technologies.append(skill_name)
                    if skill_name not in proj.inferred_skills:
                        proj.inferred_skills.append(skill_name)
                    if skill.lower() not in inferred_map:
                        inferred_map[skill.lower()] = SkillEvidenceItem(
                            name=skill_name,
                            category="Project Demonstrated",
                            source="project",
                            is_explicit=False,
                            evidence_snippet=f"Built in Project '{proj.title}': \"{(proj.description or '')[:120]}\"",
                            confidence=0.9,
                        )

        # 3. Inspect Summary
        if summary:
            s_low = summary.lower()
            for skill in COMMON_TECH_SKILLS:
                pattern = r"\b" + re.escape(skill) + r"\b"
                if re.search(pattern, s_low) and skill.lower() not in inferred_map:
                    skill_name = skill.title() if not skill.isupper() else skill
                    inferred_map[skill.lower()] = SkillEvidenceItem(
                        name=skill_name,
                        category="Profile Summary",
                        source="summary",
                        is_explicit=False,
                        evidence_snippet=f"Mentioned in summary: \"{summary[:120]}\"",
                        confidence=0.85,
                    )

        return sorted(list(inferred_map.values()), key=lambda s: s.name.lower())

    def _extract_experience(self, lines: List[str]) -> List[WorkExperienceItem]:
        if not lines:
            return []

        experiences = []
        current_exp: Optional[Dict] = None

        for line in lines:
            date_match = re.search(
                r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*)?\d{4}\s*[-–—to\s]+\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*)?(?:\d{4}|present|current)",
                line,
                re.IGNORECASE,
            )

            if date_match and len(line) < 90:
                if current_exp:
                    experiences.append(self._build_exp_item(current_exp))
                current_exp = {
                    "header": line,
                    "dates": date_match.group(0),
                    "bullets": [],
                }
            elif current_exp:
                if line.startswith("•") or line.startswith("-") or line.startswith("*") or line.startswith("\u2022"):
                    current_exp["bullets"].append(re.sub(r"^[•\-*\u2022]\s*", "", line).strip())
                elif len(line) > 20:
                    current_exp["bullets"].append(line)
            else:
                if len(line) < 60:
                    current_exp = {"header": line, "dates": "", "bullets": []}

        if current_exp:
            experiences.append(self._build_exp_item(current_exp))

        return experiences

    def _build_exp_item(self, data: Dict) -> WorkExperienceItem:
        header = data.get("header", "")
        dates = data.get("dates", "")
        parts = [p.strip() for p in re.split(r"[-–—|@,]", header) if p.strip()]
        job_title = parts[0] if parts else "Position"
        company = parts[1] if len(parts) > 1 and parts[1] != dates else None

        # Parse start and end dates
        start_date = None
        end_date = None
        if dates:
            d_parts = re.split(r"[-–—to]+", dates)
            if len(d_parts) >= 1:
                start_date = d_parts[0].strip()
            if len(d_parts) >= 2:
                end_date = d_parts[1].strip()

        # Calculate approximate duration
        years = 0.0
        years_found = re.findall(r"\b(19\d\d|20\d\d)\b", dates)
        if len(years_found) >= 2:
            try:
                years = max(0.0, float(int(years_found[1]) - int(years_found[0])))
            except Exception:
                pass
        elif len(years_found) == 1 and "present" in dates.lower():
            try:
                # current year approx 2026
                years = max(0.5, float(2026 - int(years_found[0])))
            except Exception:
                pass

        return WorkExperienceItem(
            job_title=job_title,
            company=company,
            dates=dates,
            start_date=start_date,
            end_date=end_date,
            years_calculated=years,
            responsibilities=data.get("bullets", []),
            raw_text=f"{header}\n" + "\n".join(data.get("bullets", [])),
        )

    def _extract_education(self, lines: List[str]) -> List[EducationItem]:
        if not lines:
            return []

        education_items = []
        degree_patterns = r"\b(bachelor|master|phd|b\.s|m\.s|b\.a|m\.a|b\.tech|m\.tech|associate|doctorate|diploma)\b"

        for line in lines:
            if re.search(degree_patterns, line, re.IGNORECASE) or any(u in line.lower() for u in ["university", "college", "institute", "school"]):
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                graduation_year = year_match.group(0) if year_match else None

                # Extract GPA if mentioned (e.g., GPA 3.9/4.0 or 3.8 GPA)
                gpa_match = re.search(r"(?:gpa[:\s]*)(\d\.\d+(?:\/\d\.\d+)?)", line, re.IGNORECASE)
                gpa = gpa_match.group(1) if gpa_match else None

                # Extract honors (e.g. Magna Cum Laude, Dean's List)
                honors_match = re.search(r"(summa cum laude|magna cum laude|cum laude|dean's list|first class)", line, re.IGNORECASE)
                honors = honors_match.group(0) if honors_match else None

                education_items.append(
                    EducationItem(
                        degree=line[:80] if len(line) > 80 else line,
                        institution=None,
                        graduation_year=graduation_year,
                        gpa=gpa,
                        honors=honors,
                        raw_text=line,
                    )
                )
            elif education_items:
                # Check if this line is an addendum to the previous education item (e.g. GPA, Honors)
                gpa_match = re.search(r"(?:gpa[:\s]*)(\d\.\d+(?:\/\d\.\d+)?)", line, re.IGNORECASE)
                if gpa_match and not education_items[-1].gpa:
                    education_items[-1].gpa = gpa_match.group(1)
                honors_match = re.search(r"(summa cum laude|magna cum laude|cum laude|dean's list|first class)", line, re.IGNORECASE)
                if honors_match and not education_items[-1].honors:
                    education_items[-1].honors = honors_match.group(0)

        return education_items

    def _extract_projects(self, lines: List[str]) -> List[ProjectItem]:
        if not lines:
            return []

        projects = []
        current_project: Optional[Dict] = None

        for line in lines:
            if (line.startswith("•") or line.startswith("-")) and current_project:
                current_project["bullets"].append(re.sub(r"^[•\-*]\s*", "", line))
            elif len(line) < 70 and not line.startswith(" "):
                if current_project:
                    desc = " ".join(current_project["bullets"])
                    projects.append(
                        ProjectItem(
                            title=current_project["title"],
                            description=desc,
                            technologies=[],
                            evidence_snippet=desc[:150] if desc else None,
                        )
                    )
                current_project = {"title": line, "bullets": []}
            elif current_project:
                current_project["bullets"].append(line)

        if current_project:
            desc = " ".join(current_project["bullets"])
            projects.append(
                ProjectItem(
                    title=current_project["title"],
                    description=desc,
                    technologies=[],
                    evidence_snippet=desc[:150] if desc else None,
                )
            )

        return projects

    def _extract_certifications(self, lines: List[str]) -> List[CertificationItem]:
        if not lines:
            return []

        certs = []
        for line in lines:
            if len(line) > 3:
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                year = year_match.group(0) if year_match else None
                cleaned_name = re.sub(r"^[•\-*]\s*", "", line).strip()
                certs.append(
                    CertificationItem(
                        name=cleaned_name,
                        issuer=None,
                        year=year,
                    )
                )
        return certs

    def _extract_achievements(self, lines: List[str]) -> List[AchievementItem]:
        if not lines:
            return []

        achievements = []
        for line in lines:
            cleaned = re.sub(r"^[•\-*]\s*", "", line).strip()
            if len(cleaned) >= 5:
                year_match = re.search(r"\b(19|20)\d{2}\b", cleaned)
                year = year_match.group(0) if year_match else None
                achievements.append(
                    AchievementItem(
                        title=cleaned[:60],
                        description=cleaned,
                        year=year,
                        evidence_snippet=cleaned,
                    )
                )
        return achievements

    def _extract_languages(self, lines: List[str]) -> List[LanguageItem]:
        if not lines:
            return []

        languages: List[LanguageItem] = []
        full_text = " ".join(lines).lower()

        for lang in KNOWN_LANGUAGES:
            if lang in full_text:
                # Look for proficiency descriptor near language
                prof_match = re.search(
                    rf"{lang}\s*(?:\((native|fluent|professional|intermediate|basic|bilingual)\)|[-:]\s*(native|fluent|professional|intermediate|basic|bilingual))?",
                    full_text,
                    re.IGNORECASE,
                )
                prof = None
                if prof_match:
                    prof = prof_match.group(1) or prof_match.group(2)
                languages.append(
                    LanguageItem(
                        language=lang.title(),
                        proficiency=prof.title() if prof else None,
                    )
                )
        return languages
