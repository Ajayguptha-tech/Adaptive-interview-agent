"""
Deterministic Domain and Role Router for Adaptive Interview Intelligence.
Analyzes candidate resume profile and target role to automatically select
the appropriate interviewer agent and specialized role assessment profile
across 12 supported engineering role families without candidate-facing agent selectors.

Supported Role Families:
1. Python Developer
2. Full-Stack Developer
3. Frontend Developer
4. Backend Developer
5. Java Developer
6. C/C++ Developer
7. Data Analyst
8. Data Engineer
9. Machine Learning Engineer
10. AI/ML Engineer
11. SQL / Database Developer
12. General Software Engineer
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RoleProfile(BaseModel):
    role_id: str
    display_title: str
    underlying_track: str  # "python" or "fullstack"
    specialization_mode: str
    coverage_level: str  # "Specialized Agent" or "Role-Specific Assessment Profile"
    recommended_tech_stack: Optional[str] = None
    primary_competencies: List[str] = Field(default_factory=list)
    primary_topics: List[str] = Field(default_factory=list)
    skill_keywords: List[str] = Field(default_factory=list)
    role_keywords: List[str] = Field(default_factory=list)
    description: str = ""


# Master 12-Role Registry
SUPPORTED_ROLE_REGISTRY: Dict[str, RoleProfile] = {
    "python": RoleProfile(
        role_id="python",
        display_title="Python Developer",
        underlying_track="python",
        specialization_mode="core_python",
        coverage_level="Specialized Agent",
        recommended_tech_stack="Python + FastAPI + PyTest",
        primary_competencies=[
            "Python Fundamentals", "Data Structures & Mutability", "Object-Oriented Programming",
            "Concurrency & AsyncIO", "Testing & Debugging"
        ],
        primary_topics=[
            "Data Structures & Mutability", "Object-Oriented Programming", "Asyncio & Coroutines",
            "Concurrency & GIL", "Generators & Lazy Evaluation", "Testing & Testable Design"
        ],
        skill_keywords=[
            "python", "django", "flask", "fastapi", "asyncio", "aiohttp", "gil", "celery",
            "pytest", "unittest", "numpy", "pandas", "scipy", "oop", "decorators", "generators",
            "multiprocessing", "threading", "pydantic", "sqlalchemy", "peewee"
        ],
        role_keywords=[
            "python", "python developer", "python engineer", "backend python", "cpython"
        ],
        description="Comprehensive evaluation across Python core execution model, memory management, and asynchronous architecture."
    ),
    "fullstack": RoleProfile(
        role_id="fullstack",
        display_title="Full-Stack Developer",
        underlying_track="fullstack",
        specialization_mode="fullstack_end_to_end",
        coverage_level="Specialized Agent",
        recommended_tech_stack="React + Node.js + Express + SQL",
        primary_competencies=[
            "Frontend Architecture", "Backend & REST APIs", "Database Systems",
            "Full-Stack Integration", "Web Performance & Security"
        ],
        primary_topics=[
            "HTML & Semantic Web", "CSS Layout & Box Model", "JavaScript Core",
            "React & Component Architecture", "Backend & REST APIs", "SQL & Databases",
            "Full-Stack Integration & Architecture"
        ],
        skill_keywords=[
            "javascript", "typescript", "react", "redux", "next.js", "nextjs", "vue", "angular",
            "node", "node.js", "express", "html", "css", "rest", "api", "graphql", "sql",
            "postgresql", "mysql", "mongodb", "webpack", "vite", "frontend", "fullstack"
        ],
        role_keywords=[
            "fullstack", "full-stack", "full stack", "web developer", "mern", "mean"
        ],
        description="Evaluates complete web application stack from browser UI rendering to server APIs and database queries."
    ),
    "frontend": RoleProfile(
        role_id="frontend",
        display_title="Frontend Developer",
        underlying_track="fullstack",
        specialization_mode="frontend_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="React + TypeScript + Tailwind CSS",
        primary_competencies=[
            "Frontend Fundamentals", "Modern JavaScript", "Component Architecture & State",
            "UI Performance & Layout", "Web Accessibility (A11y)"
        ],
        primary_topics=[
            "HTML & Semantic Web", "CSS Layout & Box Model", "JavaScript Core",
            "React & Component Architecture", "Full-Stack Integration & Architecture"
        ],
        skill_keywords=[
            "javascript", "typescript", "react", "redux", "vue", "angular", "html", "html5",
            "css", "css3", "tailwind", "sass", "flexbox", "grid", "webpack", "vite", "ui", "dom"
        ],
        role_keywords=[
            "frontend", "front-end", "ui engineer", "react developer", "web designer", "javascript developer"
        ],
        description="Specialized assessment concentrating on DOM manipulation, component state lifecycles, and responsive layouts."
    ),
    "backend": RoleProfile(
        role_id="backend",
        display_title="Backend Developer",
        underlying_track="fullstack",
        specialization_mode="backend_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="Node.js + Express + PostgreSQL + Redis",
        primary_competencies=[
            "API Architecture & Design", "Database Modeling & Querying", "Authentication & Security",
            "Caching & Asynchronous Processing", "System Reliability"
        ],
        primary_topics=[
            "Backend & REST APIs", "SQL & Databases", "Full-Stack Integration & Architecture",
            "JavaScript Core", "Security & Concurrency"
        ],
        skill_keywords=[
            "node", "express", "backend", "api", "rest", "graphql", "sql", "postgresql",
            "mongodb", "redis", "jwt", "oauth", "microservices", "docker", "fastapi"
        ],
        role_keywords=[
            "backend", "back-end", "api developer", "server engineer", "node developer"
        ],
        description="Focuses on RESTful interface design, relational and document persistence, authentication, and caching tiers."
    ),
    "java": RoleProfile(
        role_id="java",
        display_title="Java Developer",
        underlying_track="python",  # Evaluated with OOP, concurrency, and system design benchmarks
        specialization_mode="java_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="Java + Spring Boot + Hibernate + SQL",
        primary_competencies=[
            "Object-Oriented Architecture", "JVM Memory Model & GC", "Concurrency & Multithreading",
            "Enterprise Frameworks & Spring", "Data Structures"
        ],
        primary_topics=[
            "Object-Oriented Programming", "Data Structures & Mutability", "Concurrency & GIL",
            "Testing & Testable Design", "Backend Architecture"
        ],
        skill_keywords=[
            "java", "spring", "spring boot", "hibernate", "maven", "gradle", "junit",
            "jvm", "garbage collection", "multithreading", "oop", "enterprise"
        ],
        role_keywords=[
            "java", "java developer", "java engineer", "spring developer"
        ],
        description="Assesses enterprise OOP principles, design patterns, multithreading synchronization, and robust architecture."
    ),
    "cpp": RoleProfile(
        role_id="cpp",
        display_title="C/C++ Developer",
        underlying_track="python",
        specialization_mode="cpp_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="C++17/20 + CMake + STL + Linux",
        primary_competencies=[
            "Memory Management & Pointers", "RAII & Resource Lifetimes", "Data Structures & Algorithms",
            "System Performance & Concurrency", "Object-Oriented & Generic Programming"
        ],
        primary_topics=[
            "Data Structures & Mutability", "Object-Oriented Programming", "Concurrency & GIL",
            "Testing & Testable Design", "Low-Level Performance"
        ],
        skill_keywords=[
            "c++", "cpp", "c", "pointers", "memory management", "raii", "stl", "cmake",
            "gdb", "multithreading", "linux", "embedded"
        ],
        role_keywords=[
            "c++", "cpp", "c developer", "c++ developer", "systems engineer", "embedded engineer"
        ],
        description="Focuses on memory management, pointer manipulation, cache locality, and algorithmic efficiency."
    ),
    "data_analyst": RoleProfile(
        role_id="data_analyst",
        display_title="Data Analyst",
        underlying_track="python",
        specialization_mode="data_analysis_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="Python (Pandas, NumPy) + SQL + Tableau",
        primary_competencies=[
            "SQL Querying & Aggregations", "Data Cleaning & Transformation", "Statistical Analysis",
            "Data Visualization & Communication", "Business Metrics"
        ],
        primary_topics=[
            "Data Structures & Mutability", "Testing & Testable Design", "Generators & Lazy Evaluation",
            "Function Arguments & Packing", "SQL Queries"
        ],
        skill_keywords=[
            "sql", "data analysis", "pandas", "numpy", "tableau", "power bi", "excel",
            "statistics", "matplotlib", "seaborn", "analytics", "bi", "reporting"
        ],
        role_keywords=[
            "data analyst", "bi analyst", "business intelligence", "analytics engineer", "reporting analyst"
        ],
        description="Evaluates data extraction, aggregation queries, trend analysis, and descriptive statistical reasoning."
    ),
    "data_engineer": RoleProfile(
        role_id="data_engineer",
        display_title="Data Engineer",
        underlying_track="python",
        specialization_mode="data_engineering_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="Python + SQL + Apache Spark + Airflow + Docker",
        primary_competencies=[
            "Data Pipeline & ETL Design", "Distributed Computing & Partitioning", "Database Modeling & Data Warehousing",
            "Stream & Batch Processing", "System Scalability"
        ],
        primary_topics=[
            "Data Structures & Mutability", "Concurrency & GIL", "Generators & Lazy Evaluation",
            "Asyncio & Coroutines", "Testing & Testable Design"
        ],
        skill_keywords=[
            "spark", "airflow", "kafka", "hadoop", "etl", "data pipeline", "sql", "postgresql",
            "snowflake", "bigquery", "data warehouse", "distributed", "docker", "python"
        ],
        role_keywords=[
            "data engineer", "etl developer", "pipeline engineer", "big data engineer"
        ],
        description="Assesses high-throughput pipeline design, partition strategies, data warehousing schemas, and distributed processing."
    ),
    "ml_engineer": RoleProfile(
        role_id="ml_engineer",
        display_title="Machine Learning Engineer",
        underlying_track="python",
        specialization_mode="machine_learning_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="Python + Scikit-Learn + PyTorch + Pandas + NumPy",
        primary_competencies=[
            "Supervised & Unsupervised Learning", "Model Evaluation & Validation", "Feature Engineering & Data Preprocessing",
            "Optimization & Regularization", "Production Deployment"
        ],
        primary_topics=[
            "Data Structures & Mutability", "Generators & Lazy Evaluation", "Object-Oriented Programming",
            "Concurrency & GIL", "Testing & Testable Design"
        ],
        skill_keywords=[
            "machine learning", "ml", "scikit-learn", "pytorch", "tensorflow", "keras",
            "numpy", "pandas", "feature engineering", "model evaluation", "cross validation", "mlops"
        ],
        role_keywords=[
            "machine learning", "ml engineer", "machine learning engineer", "data scientist"
        ],
        description="Evaluates model selection, bias-variance tradeoffs, feature transforms, loss functions, and inference validation."
    ),
    "aiml_engineer": RoleProfile(
        role_id="aiml_engineer",
        display_title="AI/ML Engineer",
        underlying_track="python",
        specialization_mode="applied_ai_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="Python + PyTorch + Hugging Face + Ollama + LangChain",
        primary_competencies=[
            "Deep Learning & Neural Architectures", "Large Language Models & Transformers", "RAG & Vector Embeddings",
            "Prompt Engineering & Grounding", "Model Fine-Tuning & Evaluation"
        ],
        primary_topics=[
            "Data Structures & Mutability", "Asyncio & Coroutines", "Generators & Lazy Evaluation",
            "Object-Oriented Programming", "Testing & Testable Design"
        ],
        skill_keywords=[
            "ai", "artificial intelligence", "deep learning", "llm", "transformers", "hugging face",
            "langchain", "ollama", "rag", "embeddings", "vector database", "fine-tuning", "pytorch"
        ],
        role_keywords=[
            "ai engineer", "ai/ml engineer", "applied ai", "generative ai", "llm engineer", "deep learning engineer"
        ],
        description="Concentrates on modern AI architectures, embeddings, RAG pipelines, contextual grounding, and LLM applications."
    ),
    "sql_developer": RoleProfile(
        role_id="sql_developer",
        display_title="SQL / Database Developer",
        underlying_track="fullstack",
        specialization_mode="database_focus",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="PostgreSQL + SQL + Schema Optimization + Indexing",
        primary_competencies=[
            "Relational Data Modeling & Normalization", "Query Optimization & Execution Plans", "ACID Transactions & Concurrency",
            "Indexing Strategies (B-Tree, GIN, Hash)", "Data Integrity & Constraints"
        ],
        primary_topics=[
            "SQL & Databases", "Backend & REST APIs", "Full-Stack Integration & Architecture",
            "Data Modeling", "Transactions"
        ],
        skill_keywords=[
            "sql", "database", "postgresql", "mysql", "sqlite", "oracle", "stored procedures",
            "indexing", "normalization", "acid", "transactions", "query optimization", "schema"
        ],
        role_keywords=[
            "sql developer", "database developer", "dba", "database engineer", "rdbms developer"
        ],
        description="Specialized evaluation in database design, execution plan analysis, index selection, and transactional integrity."
    ),
    "software_engineer": RoleProfile(
        role_id="software_engineer",
        display_title="General Software Engineer",
        underlying_track="python",
        specialization_mode="general_software_engineering",
        coverage_level="Role-Specific Assessment Profile",
        recommended_tech_stack="Python + Algorithms + OOP + Unit Testing",
        primary_competencies=[
            "Algorithms & Complexity", "Data Structures", "System Design & Architecture",
            "Object-Oriented Design & Clean Code", "Problem Solving & Debugging"
        ],
        primary_topics=[
            "Data Structures & Mutability", "Object-Oriented Programming", "Generators & Lazy Evaluation",
            "Testing & Testable Design", "Exception Handling"
        ],
        skill_keywords=[
            "software engineering", "algorithms", "data structures", "oop", "problem solving",
            "git", "testing", "design patterns", "clean code", "system design"
        ],
        role_keywords=[
            "software engineer", "software developer", "sde", "engineer", "developer"
        ],
        description="Broad technical assessment of computer science fundamentals, algorithm efficiency, and software maintainability."
    ),
}


class DomainRouter:
    """
    Deterministic domain and role classifier.
    Maps candidate credentials and target role to one of 12 supported role profiles,
    preserves specialist agent isolation, and explains the routing logic.
    """

    @classmethod
    def get_role_profile(cls, role_id: str) -> RoleProfile:
        return SUPPORTED_ROLE_REGISTRY.get(role_id, SUPPORTED_ROLE_REGISTRY["software_engineer"])

    @classmethod
    def match_domain_skills(cls, skills: List[str]) -> Tuple[List[str], List[str]]:
        """Identifies which candidate skills align with Python vs Full-Stack domains."""
        py_matches = []
        fs_matches = []

        py_vocab = set(SUPPORTED_ROLE_REGISTRY["python"].skill_keywords)
        fs_vocab = set(SUPPORTED_ROLE_REGISTRY["fullstack"].skill_keywords)

        for skill in skills:
            s_clean = skill.strip().lower()
            if not s_clean:
                continue

            if s_clean in py_vocab or any(re.search(rf"\b{re.escape(k)}\b", s_clean) for k in py_vocab):
                if skill not in py_matches:
                    py_matches.append(skill)

            if s_clean in fs_vocab or any(re.search(rf"\b{re.escape(k)}\b", s_clean) for k in fs_vocab):
                if skill not in fs_matches:
                    fs_matches.append(skill)

        return py_matches, fs_matches

    @classmethod
    def identify_role_family(cls, target_role: str, claimed_skills: List[str]) -> str:
        """Determines the closest matching of the 12 role families."""
        role_lower = (target_role or "").strip().lower()

        # 1. Target role exact / keyword matching
        for role_key, profile in SUPPORTED_ROLE_REGISTRY.items():
            if any(k in role_lower for k in profile.role_keywords):
                return role_key

        # 2. Strong skill signature matching if target role is generic
        skills_lower = [s.lower() for s in claimed_skills]
        if any(k in skills_lower for k in ["pytorch", "tensorflow", "transformers", "langchain", "ollama", "rag"]):
            return "aiml_engineer"
        if any(k in skills_lower for k in ["scikit-learn", "machine learning", "ml"]):
            return "ml_engineer"
        if any(k in skills_lower for k in ["spark", "airflow", "kafka", "hadoop", "etl"]):
            return "data_engineer"
        if any(k in skills_lower for k in ["tableau", "power bi", "data analysis"]) and "sql" in skills_lower:
            return "data_analyst"
        if any(k in skills_lower for k in ["react", "vue", "angular", "html5", "css3"]) and not any(k in skills_lower for k in ["python", "node", "django"]):
            return "frontend"
        if any(k in skills_lower for k in ["java", "spring", "hibernate"]):
            return "java"
        if any(k in skills_lower for k in ["c++", "cpp"]):
            return "cpp"

        # 3. Default based on track balance
        py_matches, fs_matches = cls.match_domain_skills(claimed_skills)
        if len(fs_matches) > len(py_matches):
            return "fullstack"
        elif len(py_matches) > 0:
            return "python"
        return "software_engineer"

    @classmethod
    def route(
        cls,
        resume_profile: Dict[str, Any],
        target_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Determines the appropriate role family and underlying interviewer track.
        Maintains backwards compatibility for 'routed_track' ('python' or 'fullstack').
        """
        skills = (
            resume_profile.get("claimed_skills")
            or resume_profile.get("skills")
            or []
        )
        effective_role = (target_role or resume_profile.get("target_role") or "Software Engineer").strip()
        role_family = cls.identify_role_family(effective_role, skills)
        profile = SUPPORTED_ROLE_REGISTRY[role_family]

        py_matches, fs_matches = cls.match_domain_skills(skills)
        py_skill_count = len(py_matches)
        fs_skill_count = len(fs_matches)

        # Underlying interviewer agent selection (preserves isolated Python & Full-Stack agents)
        routed_track = profile.underlying_track
        is_mixed_profile = py_skill_count >= 2 and fs_skill_count >= 2

        # Recommended tech stack
        recommended_tech_stack = profile.recommended_tech_stack
        if is_mixed_profile and routed_track == "fullstack":
            has_fastapi_or_python = any(
                s.lower() in ("python", "fastapi", "django", "flask") for s in skills
            )
            if has_fastapi_or_python:
                recommended_tech_stack = "React + FastAPI + PostgreSQL"

        # Confidence calculation
        dominant_count = fs_skill_count if routed_track == "fullstack" else py_skill_count
        total_skills_count = max(1, py_skill_count + fs_skill_count)
        base_confidence = min(0.96, max(0.65, 0.60 + (dominant_count / total_skills_count) * 0.35))
        confidence = round(base_confidence, 2)

        primary_skills = fs_matches if routed_track == "fullstack" else py_matches
        matched_summary = ", ".join(primary_skills[:4]) if primary_skills else "General technical skills"

        # Structured explainability
        if profile.coverage_level == "Specialized Agent":
            reason = (
                f"Candidate targeted '{effective_role}' ({profile.display_title}). Automatically routed to "
                f"{profile.display_title} with {int(confidence * 100)}% domain confidence based on verified skills ({matched_summary})."
            )
        else:
            reason = (
                f"Candidate targeted '{effective_role}'. Mapped to the {profile.display_title} Assessment Profile "
                f"leveraging {routed_track.title()} core infrastructure and specialized {profile.specialization_mode.replace('_', ' ')} benchmarks."
            )

        logger.info(
            "[DOMAIN_ROUTER] target_role='%s' -> role_family='%s' (track='%s', conf=%.2f)",
            effective_role, role_family, routed_track, confidence
        )

        return {
            "routed_track": routed_track,  # Backwards compatibility: "python" or "fullstack"
            "role_family": role_family,
            "role_title": profile.display_title,
            "coverage_level": profile.coverage_level,
            "specialization_mode": profile.specialization_mode,
            "domain_confidence": confidence,
            "routing_reason": reason,
            "is_mixed_profile": is_mixed_profile,
            "recommended_tech_stack": recommended_tech_stack,
            "matched_python_skills": py_matches,
            "matched_fullstack_skills": fs_matches,
            "primary_skills": primary_skills,
            "focus_competencies": profile.primary_competencies,
            "focus_topics": profile.primary_topics,
        }
