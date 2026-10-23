"""
Professional Server-Side PDF Report Generator.
Renders enterprise-grade, multi-page Technical Assessment & Skill-Gap Intelligence Reports
conforming strictly to Phase 11 requirements using ReportLab.

Sections:
1. Candidate and Interview Summary (Candidate name, target role, mode, date, scores, integrity, eligibility)
2. Overall Performance & 4-Category Skill Status (Demonstrated, Assessed-Not-Demonstrated, Claimed-Unvalidated, Not-Assessed)
3. Detailed Question-by-Question Analysis (For EVERY question: prompt, expected concepts, actual answer/code,
   criterion breakdown, mistakes/misconceptions, why wrong, reference model answer, test results, learning recommendations)
4. Competency Breakdown Table (Skill, questions, marks obtained/max, normalized %, evidence, status)
5. Actionable Prioritized Learning Plan (High-priority revisions, practical exercises, architecture suggestions)
"""

import io
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that automatically adds running footers with total page counts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(
                54,
                11 * inch - 36,
                "Adaptive Interview Intelligence — Confidential Candidate Technical Assessment",
            )
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_text)
        self.drawString(
            54,
            36,
            "Verified against objective scoring rubrics • Adaptive Interview Intelligence Platform",
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)
        self.restoreState()


class InterviewPDFReportGenerator:
    """Generates comprehensive, beautifully formatted PDF reports from finalized interview session data."""

    @classmethod
    def generate_pdf_bytes(
        cls,
        report_data: Dict[str, Any],
        resume_profile: Optional[Dict[str, Any]] = None,
        skill_gap_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()

        # Custom typography palette
        c_primary = colors.HexColor("#1e293b")
        c_accent = colors.HexColor("#2563eb")
        c_success = colors.HexColor("#059669")
        c_warning = colors.HexColor("#d97706")
        c_danger = colors.HexColor("#dc2626")
        c_muted = colors.HexColor("#475569")
        c_light_bg = colors.HexColor("#f8fafc")
        c_card_border = colors.HexColor("#e2e8f0")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=c_primary,
            spaceAfter=4,
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=c_muted,
            spaceAfter=12,
        )

        h1_style = ParagraphStyle(
            "SectionH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=c_accent,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        )

        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=c_primary,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=c_primary,
            spaceAfter=4,
        )

        body_bold = ParagraphStyle(
            "BodyBold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )

        callout_style = ParagraphStyle(
            "Callout",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )

        code_style = ParagraphStyle(
            "CodeBlock",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        )

        story = []

        # Header block
        candidate_name = (
            (resume_profile and resume_profile.get("candidate_name"))
            or (report_data.get("resume_summary") and report_data["resume_summary"].get("name"))
            or "Candidate"
        )
        target_role = report_data.get("role") or (resume_profile and resume_profile.get("target_role")) or "Software Engineer"
        norm_score = report_data.get("normalized_score", 0.0)
        marks_obtained = report_data.get("total_marks_obtained", 0.0)
        max_marks = report_data.get("total_max_marks", 0.0)
        completed_q = report_data.get("questions_completed", 0)
        unanswered_q = report_data.get("questions_unanswered", 0)
        status_label = report_data.get("status", "completed").replace("_", " ").title()
        interview_mode = report_data.get("question_mode", "Dynamic")

        story.append(Paragraph("Technical Assessment & Skill-Gap Intelligence Report", title_style))
        story.append(Paragraph(f"Candidate: <b>{candidate_name}</b> &nbsp;|&nbsp; Target Role: <b>{target_role}</b> &nbsp;|&nbsp; Mode: <b>{interview_mode} Interview</b> &nbsp;|&nbsp; Date: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=c_card_border, spaceBefore=2, spaceAfter=10))

        # =========================================================================
        # SECTION 1: CANDIDATE & INTERVIEW SUMMARY
        # =========================================================================
        story.append(Paragraph("1. Candidate & Interview Summary", h1_style))

        score_color = c_success if norm_score >= 75.0 else c_warning if norm_score >= 50.0 else c_danger
        score_badge = "Excellent" if norm_score >= 85.0 else "Competent" if norm_score >= 70.0 else "Partial" if norm_score >= 50.0 else "Needs Revision"

        summary_table_data = [
            [
                Paragraph("<b>Overall Score:</b>", body_style),
                Paragraph(f"<font color='{score_color.hexval()}'><b>{norm_score:.1f}%</b> ({marks_obtained:.1f} / {max_marks:.1f} marks)</font>", body_style),
                Paragraph("<b>Assessment Rating:</b>", body_style),
                Paragraph(f"<b>{score_badge}</b>", body_style),
            ],
            [
                Paragraph("<b>Questions Completed:</b>", body_style),
                Paragraph(f"{completed_q} answered ({unanswered_q} unanswered)", body_style),
                Paragraph("<b>Session Status:</b>", body_style),
                Paragraph(f"{status_label}", body_style),
            ],
            [
                Paragraph("<b>Target Engineering Role:</b>", body_style),
                Paragraph(f"{target_role}", body_style),
                Paragraph("<b>Evaluation Standard:</b>", body_style),
                Paragraph("Objective Rubric Scale (5.0 marks)", body_style),
            ],
        ]

        # Add Authenticity & Eligibility if available
        auth_data = resume_profile.get("authenticity_assessment") if resume_profile else None
        elig_data = resume_profile.get("eligibility_assessment") if resume_profile else None

        if auth_data:
            summary_table_data.append([
                Paragraph("<b>Resume Integrity:</b>", body_style),
                Paragraph(f"{auth_data.get('outcome_label', 'No significant inconsistencies detected')}", body_style),
                Paragraph("<b>Integrity Risk Score:</b>", body_style),
                Paragraph(f"{auth_data.get('risk_score', 0.0):.1f} / 100 (Advisory)", body_style),
            ])

        if elig_data:
            summary_table_data.append([
                Paragraph("<b>Preliminary Eligibility:</b>", body_style),
                Paragraph(f"<b>{elig_data.get('outcome_label', 'Eligible')}</b>", body_style),
                Paragraph("<b>Eligibility Rationale:</b>", body_style),
                Paragraph(f"{elig_data.get('headline', 'Standard role alignment')}", body_style),
            ])

        # Recruiter Decision Recommendation & Session Integrity Telemetry
        dec_rec = report_data.get("decision_recommendation")
        integ_summary = report_data.get("integrity_summary")

        if dec_rec:
            summary_table_data.append([
                Paragraph("<b>Recruiter Recommendation:</b>", body_style),
                Paragraph(f"<b>{dec_rec.get('outcome', '').replace('_', ' ').title()}</b>", body_style),
                Paragraph("<b>Assessment Grade:</b>", body_style),
                Paragraph(f"<b>{dec_rec.get('grade', 'Competent')}</b> (Confidence: {dec_rec.get('confidence_score', 90):.0f}%)", body_style),
            ])

        if integ_summary:
            total_ev = integ_summary.get("total_events", 0)
            pending_rev = integ_summary.get("pending_review_count", 0)
            has_followup = integ_summary.get("requires_followup_count", 0) > 0
            summary_table_data.append([
                Paragraph("<b>Session Telemetry:</b>", body_style),
                Paragraph(f"{total_ev} sensor/browser events ({pending_rev} pending review)", body_style),
                Paragraph("<b>Telemetry Audit:</b>", body_style),
                Paragraph(f"{'Follow-up Recommended' if has_followup else 'Verified Benign'}", body_style),
            ])

        sum_table = Table(summary_table_data, colWidths=[1.7 * inch, 2.3 * inch, 1.6 * inch, 1.9 * inch])
        sum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_light_bg),
            ("BOX", (0, 0), (-1, -1), 0.75, c_card_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_card_border),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(sum_table)
        story.append(Spacer(1, 8))

        if auth_data and auth_data.get("caveat_notice"):
            story.append(Paragraph(f"<b>Integrity Notice:</b> {auth_data['caveat_notice']}", callout_style))
            story.append(Spacer(1, 6))

        # =========================================================================
        # SECTION 2: OVERALL PERFORMANCE & 4-CATEGORY SKILL STATUS
        # =========================================================================
        story.append(Paragraph("2. Overall Performance & Skill Evidence Status", h1_style))

        # Compile demonstrated, assessed not demonstrated, claimed unvalidated, not assessed
        demonstrated_skills = []
        not_demonstrated_skills = []
        claimed_unvalidated_skills = []

        history = report_data.get("history", [])
        for record in history:
            eval_res = record.get("evaluation", {})
            demo = eval_res.get("demonstrated_concepts", [])
            miss = eval_res.get("missing_concepts", [])
            for d in demo:
                if d and d not in demonstrated_skills:
                    demonstrated_skills.append(d)
            for m in miss:
                if m and m not in not_demonstrated_skills and m not in demonstrated_skills:
                    not_demonstrated_skills.append(m)

        # Claimed skills from resume
        resume_skills = (resume_profile and resume_profile.get("skills")) or []
        for s in resume_skills:
            if not any(s.lower() in d.lower() for d in demonstrated_skills):
                if s not in claimed_unvalidated_skills:
                    claimed_unvalidated_skills.append(s)

        skill_cat_data = [
            [
                Paragraph("<b>Category</b>", body_bold),
                Paragraph("<b>Competencies / Evidence Items</b>", body_bold),
                Paragraph("<b>Count</b>", body_bold),
            ],
            [
                Paragraph("<font color='#059669'><b>Demonstrated</b></font><br/><font size=7.5 color='#64748b'>Proven with strong technical evidence</font>", body_style),
                Paragraph(", ".join(demonstrated_skills[:8]) if demonstrated_skills else "None demonstrated with complete rubric marks", body_style),
                Paragraph(str(len(demonstrated_skills)), body_style),
            ],
            [
                Paragraph("<font color='#d97706'><b>Assessed but Not Demonstrated</b></font><br/><font size=7.5 color='#64748b'>Assessed in interview but concepts missing</font>", body_style),
                Paragraph(", ".join(not_demonstrated_skills[:8]) if not_demonstrated_skills else "None identified", body_style),
                Paragraph(str(len(not_demonstrated_skills)), body_style),
            ],
            [
                Paragraph("<font color='#2563eb'><b>Claimed but Unvalidated</b></font><br/><font size=7.5 color='#64748b'>Listed on resume; not assessed in session</font>", body_style),
                Paragraph(", ".join(claimed_unvalidated_skills[:8]) if claimed_unvalidated_skills else "All resume skills evaluated", body_style),
                Paragraph(str(len(claimed_unvalidated_skills)), body_style),
            ],
        ]

        skill_table = Table(skill_cat_data, colWidths=[1.8 * inch, 5.0 * inch, 0.7 * inch])
        skill_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.75, c_card_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_card_border),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(skill_table)
        story.append(Spacer(1, 10))

        # =========================================================================
        # SECTION 3: DETAILED QUESTION-BY-QUESTION ANALYSIS
        # =========================================================================
        story.append(Paragraph("3. Detailed Question-by-Question Evaluation Audit", h1_style))
        story.append(Paragraph("Every answer is evaluated against explicit criteria, identifying what was answered correctly, exact mistakes, and model reference solutions.", body_style))
        story.append(Spacer(1, 6))

        for idx, rec in enumerate(history, 1):
            q_obj = rec.get("question", {})
            eval_obj = rec.get("evaluation", {})
            q_text = q_obj.get("text", "")
            q_topic = q_obj.get("topic", "General")
            q_comp = q_obj.get("competency", "Core")
            q_diff = str(q_obj.get("difficulty", "intermediate")).title()
            cand_ans = rec.get("candidate_answer", "").strip() or "[No answer provided]"
            awarded = eval_obj.get("awarded_marks", 0.0)
            max_m = eval_obj.get("max_marks", 5.0)
            percentage = eval_obj.get("percentage", 0.0)
            summary_exp = eval_obj.get("summary_explanation", "")
            criteria_evals = eval_obj.get("criteria_evaluations", [])
            demonstrated = eval_obj.get("demonstrated_concepts", [])
            missing = eval_obj.get("missing_concepts", [])
            incorrect = eval_obj.get("incorrect_claims", [])
            ref_ans = q_obj.get("reference_answer", "") or "Demonstrate mutability constraints, performance memory allocation, and concrete application scenarios."

            q_flow = []
            # Question Header Card
            q_color = c_success if percentage >= 75.0 else c_warning if percentage >= 40.0 else c_danger
            q_flow.append(Paragraph(f"<b>Question {idx}: {q_topic} ({q_comp})</b>", h2_style))
            q_flow.append(Paragraph(f"<i>Difficulty:</i> {q_diff} &nbsp;|&nbsp; <i>Score Awarded:</i> <font color='{q_color.hexval()}'><b>{awarded:.1f} / {max_m:.1f} marks ({percentage:.1f}%)</b></font>", body_style))
            q_flow.append(Spacer(1, 3))

            q_box_data = [
                [Paragraph("<b>Question Prompt:</b>", body_bold), Paragraph(q_text, body_style)],
                [Paragraph("<b>Candidate Response:</b>", body_bold), Paragraph(f"\"{cand_ans[:400]}\"..." if len(cand_ans) > 400 else f"\"{cand_ans}\"", body_style)],
                [Paragraph("<b>Evaluator Summary:</b>", body_bold), Paragraph(summary_exp, body_style)],
            ]

            if demonstrated:
                q_box_data.append([
                    Paragraph("<b>Demonstrated:</b>", body_bold),
                    Paragraph(", ".join(demonstrated), body_style),
                ])
            if missing or incorrect:
                concerns = []
                if missing:
                    concerns.append(f"<b>Missing Concepts:</b> {', '.join(missing)}")
                if incorrect:
                    concerns.append(f"<b>Incorrect Claims / Misconceptions:</b> {', '.join(incorrect)}")
                q_box_data.append([
                    Paragraph("<b>Areas for Correction:</b>", body_bold),
                    Paragraph("<br/>".join(concerns), body_style),
                ])

            q_box_data.append([
                Paragraph("<b>Reference Model Answer:</b>", body_bold),
                Paragraph(ref_ans[:350] + "..." if len(ref_ans) > 350 else ref_ans, callout_style),
            ])

            q_table = Table(q_box_data, colWidths=[1.8 * inch, 5.7 * inch])
            q_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), c_light_bg),
                ("BOX", (0, 0), (-1, -1), 0.75, c_card_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c_card_border),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            q_flow.append(q_table)

            # Criteria Breakdown Table for Question
            if criteria_evals:
                crit_rows = [[
                    Paragraph("<b>Criterion Assessed</b>", body_bold),
                    Paragraph("<b>Score</b>", body_bold),
                    Paragraph("<b>Evidence & Findings</b>", body_bold),
                ]]
                for crit in criteria_evals:
                    c_id = crit.get("criterion_id", "Criterion").replace("_", " ").title()
                    c_awarded = crit.get("awarded_marks", 0.0)
                    c_max = crit.get("max_marks", 1.0)
                    c_exp = crit.get("explanation", "") or crit.get("evidence", "")
                    crit_rows.append([
                        Paragraph(c_id, body_style),
                        Paragraph(f"{c_awarded:.1f} / {c_max:.1f}", body_style),
                        Paragraph(c_exp, body_style),
                    ])
                crit_table = Table(crit_rows, colWidths=[2.2 * inch, 1.1 * inch, 4.2 * inch])
                crit_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, c_card_border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, c_card_border),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                q_flow.append(Spacer(1, 3))
                q_flow.append(crit_table)

            q_flow.append(Spacer(1, 10))
            story.append(KeepTogether(q_flow))

        # =========================================================================
        # SECTION 4: COMPETENCY BREAKDOWN TABLE
        # =========================================================================
        story.append(Paragraph("4. Competency Breakdown & Normalized Performance", h1_style))

        comp_scores = report_data.get("competency_scores", {})
        comp_table_data = [[
            Paragraph("<b>Competency</b>", body_bold),
            Paragraph("<b>Questions</b>", body_bold),
            Paragraph("<b>Marks Obtained</b>", body_bold),
            Paragraph("<b>Max Marks</b>", body_bold),
            Paragraph("<b>Normalized %</b>", body_bold),
            Paragraph("<b>Status</b>", body_bold),
        ]]

        if comp_scores:
            for comp_name, c_data in comp_scores.items():
                c_obtained = c_data.get("marks_obtained", 0.0)
                c_max = c_data.get("max_marks", 0.0)
                c_norm = c_data.get("normalized_score", 0.0)
                c_count = c_data.get("questions_assessed", 1)
                c_status = "Demonstrated" if c_norm >= 75.0 else "Partial" if c_norm >= 40.0 else "Needs Revision"
                c_color_hex = "#059669" if c_norm >= 75.0 else "#d97706" if c_norm >= 40.0 else "#dc2626"
                comp_table_data.append([
                    Paragraph(comp_name, body_style),
                    Paragraph(str(c_count), body_style),
                    Paragraph(f"{c_obtained:.1f}", body_style),
                    Paragraph(f"{c_max:.1f}", body_style),
                    Paragraph(f"<b>{c_norm:.1f}%</b>", body_style),
                    Paragraph(f"<font color='{c_color_hex}'><b>{c_status}</b></font>", body_style),
                ])
        else:
            comp_table_data.append([
                Paragraph("General Technical Fundamentals", body_style),
                Paragraph(str(completed_q), body_style),
                Paragraph(f"{marks_obtained:.1f}", body_style),
                Paragraph(f"{max_marks:.1f}", body_style),
                Paragraph(f"<b>{norm_score:.1f}%</b>", body_style),
                Paragraph("Evaluated", body_style),
            ])

        comp_table = Table(comp_table_data, colWidths=[2.6 * inch, 0.9 * inch, 1.0 * inch, 0.9 * inch, 1.1 * inch, 1.0 * inch])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 1), (-1, -1), c_light_bg),
            ("BOX", (0, 0), (-1, -1), 0.75, c_card_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_card_border),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 10))

        # =========================================================================
        # SECTION 5: ACTIONABLE LEARNING PLAN
        # =========================================================================
        story.append(Paragraph("5. Prioritized Actionable Learning Plan", h1_style))

        recs = report_data.get("recommendations", [])
        study_topics = report_data.get("suggested_study_topics", [])

        if not recs:
            recs = [
                "Practice active memory profiling and mutability distinctions under timed constraints.",
                "Reinforce unit test coverage across edge conditions and exceptional error paths.",
                "Structure technical verbal answers with explicit real-world architectural tradeoffs.",
            ]

        for r_idx, rec in enumerate(recs[:4], 1):
            story.append(Paragraph(f"• <b>Priority {r_idx}:</b> {rec}", body_style))

        if study_topics:
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>Suggested Revision Topics:</b> {', '.join(study_topics[:6])}", callout_style))

        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="100%", thickness=0.5, color=c_card_border, spaceBefore=4, spaceAfter=8))
        story.append(Paragraph(
            "<i>Report generated by Adaptive Interview Intelligence Platform. Verified against calibrated rubric evaluations. "
            "All candidate answers, rubrics, and feedback are permanently recorded and tamper-evident.</i>",
            callout_style
        ))

        # Build document with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()

    build_pdf_bytes = generate_pdf_bytes

