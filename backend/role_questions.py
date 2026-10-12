"""
Role-Specific Question Bank Extensions.
Provides curated, rubrics-bound benchmark questions for specialized engineering roles:
- Java Developer
- C/C++ Developer
- Data Analyst
- Data Engineer
- Machine Learning Engineer
- AI/ML Engineer
- SQL / Database Developer
- General Software Engineer

All questions conform to the standard 5.0 marks rubric scale with explicit criteria,
expected concepts, and common misconceptions.
"""

from typing import List, Dict, Optional
from backend.models import (
    Question,
    DifficultyLevel,
    QuestionType,
    RubricCriterion,
)

ROLE_SPECIALIZED_QUESTIONS: List[Question] = [
    # =========================================================================
    # JAVA DEVELOPER
    # =========================================================================
    Question(
        id="java-beg-001",
        topic="Object-Oriented Architecture",
        competency="Java Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="java",
        track="python",
        text=(
            "In Java, what is the difference between an abstract class and an interface, "
            "and when would you choose one over the other in modern Java (Java 8+)?"
        ),
        expected_concepts=[
            "Abstract classes can have state/instance variables and constructors; interfaces cannot have instance state",
            "A class can implement multiple interfaces but extend only one class (single inheritance)",
            "Interfaces can define default and static methods since Java 8",
            "Use interfaces for capability contracts across unrelated classes; abstract classes for code reuse among closely related classes",
        ],
        common_misconceptions=[
            "Believing interfaces can have constructors or instance fields",
            "Believing abstract classes cannot have implemented methods",
        ],
        rubric=[
            RubricCriterion(
                id="state_and_inheritance",
                description="Explains state, constructors, and multiple interface implementation vs single class inheritance",
                max_marks=2.5,
                evidence_guide="Award full marks for noting single class extension vs multiple interface implementation.",
            ),
            RubricCriterion(
                id="modern_java_default_methods",
                description="Mentions default/static methods introduced in Java 8",
                max_marks=1.5,
                evidence_guide="Awarded for noting default methods in interfaces.",
            ),
            RubricCriterion(
                id="architectural_choice",
                description="Valid real-world design scenario for choosing interface vs abstract class",
                max_marks=1.0,
                evidence_guide="Awarded for clear guidance on capability contract vs shared identity hierarchy.",
            ),
        ],
    ),
    Question(
        id="java-int-002",
        topic="JVM Memory Model & GC",
        competency="Concurrency & Performance",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="java",
        track="python",
        text=(
            "Explain how the Java Virtual Machine (JVM) divides memory into Heap and Stack, "
            "how garbage collection identifies unreachable objects, and what causes an OutOfMemoryError in Java."
        ),
        expected_concepts=[
            "Stack stores primitive local variables and method call frames; Heap stores allocated objects",
            "Garbage collection uses GC Roots (threads, static references) to trace object reachability",
            "Generational heap collection: Young Generation (Eden, Survivor) and Old/Tenured Generation",
            "OutOfMemoryError occurs when the heap runs out of allocatable memory due to memory leaks (e.g. unclosed resources, static collections)",
        ],
        rubric=[
            RubricCriterion(
                id="heap_vs_stack",
                description="Clearly explains Stack (frames, primitives) vs Heap (object instances)",
                max_marks=2.0,
                evidence_guide="Award full marks for heap vs stack distinction.",
            ),
            RubricCriterion(
                id="gc_reachability",
                description="Explains GC Roots and reachability tracing",
                max_marks=1.5,
                evidence_guide="Awarded for explaining reachability from GC roots.",
            ),
            RubricCriterion(
                id="oom_causes",
                description="Identifies real-world causes of OutOfMemoryError and memory leaks",
                max_marks=1.5,
                evidence_guide="Awarded for mentioning leaks like unbounded static collections or unclosed listeners.",
            ),
        ],
    ),

    # =========================================================================
    # C/C++ DEVELOPER
    # =========================================================================
    Question(
        id="cpp-beg-001",
        topic="Memory Management & Pointers",
        competency="Systems Programming",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="cpp",
        track="python",
        text=(
            "What is the principle of RAII (Resource Acquisition Is Initialization) in C++, "
            "and how do `std::unique_ptr` and `std::shared_ptr` prevent memory leaks compared to raw pointers?"
        ),
        expected_concepts=[
            "RAII binds resource lifetime to object scope; destructor automatically releases resources on exit/exception",
            "std::unique_ptr provides exclusive ownership with zero runtime overhead over raw pointer",
            "std::shared_ptr uses atomic reference counting for shared ownership",
            "Destructors are invoked deterministically when smart pointer goes out of scope, eliminating manual delete",
        ],
        rubric=[
            RubricCriterion(
                id="raii_concept",
                description="Clearly explains RAII and destructor-driven resource cleanup",
                max_marks=2.0,
                evidence_guide="Award full marks for tying resource cleanup to destructor invocation on scope exit.",
            ),
            RubricCriterion(
                id="unique_ptr_ownership",
                description="Explains unique_ptr exclusive ownership and move semantics",
                max_marks=1.5,
                evidence_guide="Awarded for explaining exclusive ownership.",
            ),
            RubricCriterion(
                id="shared_ptr_ref_count",
                description="Explains shared_ptr reference counting and cyclic reference pitfalls (weak_ptr)",
                max_marks=1.5,
                evidence_guide="Awarded for explaining reference counting.",
            ),
        ],
    ),

    # =========================================================================
    # DATA ANALYST
    # =========================================================================
    Question(
        id="da-beg-001",
        topic="SQL Querying & Aggregations",
        competency="Data Analysis",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="sql",
        track="python",
        text=(
            "In SQL, explain the difference between the `WHERE` clause and the `HAVING` clause. "
            "Give an example scenario where using `WHERE` instead of `HAVING` would cause a syntax error."
        ),
        expected_concepts=[
            "WHERE filters rows BEFORE aggregation; HAVING filters groups AFTER aggregation (GROUP BY)",
            "WHERE cannot be used with aggregate functions (e.g. WHERE COUNT(*) > 5 fails)",
            "HAVING is evaluated after GROUP BY has aggregated rows into summary records",
        ],
        rubric=[
            RubricCriterion(
                id="where_vs_having_timing",
                description="Explains filtering order: WHERE before grouping, HAVING after aggregation",
                max_marks=2.5,
                evidence_guide="Award full marks for explaining execution order relative to GROUP BY.",
            ),
            RubricCriterion(
                id="aggregate_restriction",
                description="Identifies that aggregate functions cannot be placed inside WHERE",
                max_marks=1.5,
                evidence_guide="Awarded for explaining syntax failure when using aggregates in WHERE.",
            ),
            RubricCriterion(
                id="example_scenario",
                description="Provides concrete example (e.g., finding departments with more than 10 employees)",
                max_marks=1.0,
                evidence_guide="Awarded for clear practical example.",
            ),
        ],
    ),
    Question(
        id="da-int-002",
        topic="Statistical Analysis & Missing Data",
        competency="Data Wrangling",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="python",
        track="python",
        text=(
            "When analyzing a real-world dataset containing missing values in a numerical column, "
            "how do you decide between imputation (mean, median, forward fill) versus row deletion, "
            "and how do outliers affect mean imputation?"
        ),
        expected_concepts=[
            "Row deletion is acceptable only when missingness is random (MCAR) and percentage is negligible (< 3-5%)",
            "Mean imputation is distorted by skewed distributions and extreme outliers; median is robust",
            "Forward/backward fill is appropriate for chronological time-series data",
            "Imputation artificially deflates variance unless modeling uncertainty",
        ],
        rubric=[
            RubricCriterion(
                id="deletion_vs_imputation",
                description="Explains tradeoffs of row deletion vs imputation based on percentage and missingness mechanism",
                max_marks=2.0,
                evidence_guide="Award full marks for explaining when deletion loses too much sample power.",
            ),
            RubricCriterion(
                id="mean_vs_median_skew",
                description="Explains why median is preferred over mean in skewed or outlier-heavy data",
                max_marks=2.0,
                evidence_guide="Awarded for stating mean is pulled toward outliers while median is resistant.",
            ),
            RubricCriterion(
                id="time_series_handling",
                description="Mentions forward fill or domain-specific interpolation for time-series",
                max_marks=1.0,
                evidence_guide="Awarded for recognizing chronological continuity.",
            ),
        ],
    ),

    # =========================================================================
    # DATA ENGINEER
    # =========================================================================
    Question(
        id="de-int-001",
        topic="Data Pipeline & ETL Design",
        competency="Data Engineering",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="python",
        track="python",
        text=(
            "Compare ETL (Extract, Transform, Load) with ELT (Extract, Load, Transform). "
            "Why has modern cloud data warehousing (Snowflake, BigQuery) favored ELT, and how do you guarantee idempotent pipeline runs?"
        ),
        expected_concepts=[
            "ETL transforms data on an external compute cluster before loading; ELT loads raw data into warehouse first and transforms using warehouse compute",
            "Cloud warehouses offer elastic, scalable SQL compute, decoupling storage from compute",
            "Raw data is preserved for reprocessing and schema evolution",
            "Idempotency: running a pipeline multiple times produces the same state (e.g. partition overwrite, UPSERT, deduplication)",
        ],
        rubric=[
            RubricCriterion(
                id="etl_vs_elt_architecture",
                description="Clearly explains transformation location: dedicated ETL engine vs cloud warehouse compute",
                max_marks=2.0,
                evidence_guide="Award full marks for clear architectural distinction.",
            ),
            RubricCriterion(
                id="cloud_warehouse_drivers",
                description="Explains storage/compute decoupling and elastic scaling driving ELT",
                max_marks=1.5,
                evidence_guide="Awarded for explaining cloud MPP warehouse advantages.",
            ),
            RubricCriterion(
                id="idempotency_strategies",
                description="Explains idempotency techniques (partition drop/replace, merge/upsert keys)",
                max_marks=1.5,
                evidence_guide="Awarded for practical idempotency mechanism.",
            ),
        ],
    ),

    # =========================================================================
    # MACHINE LEARNING ENGINEER
    # =========================================================================
    Question(
        id="mle-int-001",
        topic="Model Evaluation & Validation",
        competency="Machine Learning",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="python",
        track="python",
        text=(
            "When evaluating a classification model on an imbalanced dataset (e.g., fraud detection where 99.5% of cases are non-fraud), "
            "why is accuracy misleading, and how do Precision, Recall, and the PR-AUC curve provide a more truthful evaluation?"
        ),
        expected_concepts=[
            "A trivial classifier predicting majority class achieves 99.5% accuracy while identifying zero fraudulent cases",
            "Precision = TP / (TP + FP) measures false alarm rate; Recall = TP / (TP + FN) measures capture rate of true fraud",
            "F1-score or PR-AUC focuses directly on the minority positive class without distortion from true negatives",
            "Business context determines threshold: prioritize Recall to catch all fraud, or Precision to minimize user disruption",
        ],
        rubric=[
            RubricCriterion(
                id="accuracy_paradox",
                description="Explains why accuracy is uninformative for severe class imbalance",
                max_marks=1.5,
                evidence_guide="Award full marks for majority class trivial prediction example.",
            ),
            RubricCriterion(
                id="precision_vs_recall",
                description="Defines Precision and Recall with mathematical formulas or clear definitions",
                max_marks=2.0,
                evidence_guide="Awarded for accurate definitions of precision and recall.",
            ),
            RubricCriterion(
                id="metric_selection",
                description="Explains PR-AUC, F1-score, and threshold tuning based on business cost matrix",
                max_marks=1.5,
                evidence_guide="Awarded for explaining decision threshold and trade-off.",
            ),
        ],
    ),

    # =========================================================================
    # AI / ML ENGINEER
    # =========================================================================
    Question(
        id="aiml-int-001",
        topic="Large Language Models & RAG",
        competency="Applied AI Architecture",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="python",
        track="python",
        text=(
            "Explain the architecture of a Retrieval-Augmented Generation (RAG) system. "
            "How does semantic chunking and dense vector retrieval mitigate LLM hallucinations compared to standalone prompting?"
        ),
        expected_concepts=[
            "RAG embeds source documents into vector chunks and retrieves top-k relevant context using cosine similarity",
            "Retrieved chunks are injected into the prompt context window alongside the user query",
            "Grounds the model in verified facts, mitigating hallucinations caused by stale training data or parametric memory gaps",
            "Chunk size trade-off: large chunks dilute retrieval precision; small chunks lose critical context",
        ],
        rubric=[
            RubricCriterion(
                id="rag_pipeline_flow",
                description="Explains ingestion (chunking, embedding) and retrieval-generation inference flow",
                max_marks=2.0,
                evidence_guide="Award full marks for describing end-to-end RAG architecture.",
            ),
            RubricCriterion(
                id="hallucination_mitigation",
                description="Explains how external grounding reduces parametric hallucinations and citation anchoring",
                max_marks=1.5,
                evidence_guide="Awarded for explaining factual grounding in retrieved context.",
            ),
            RubricCriterion(
                id="chunking_and_retrieval_tradeoffs",
                description="Discusses chunking strategies, embedding similarity, or re-ranking (cross-encoder)",
                max_marks=1.5,
                evidence_guide="Awarded for discussing chunking or vector search nuances.",
            ),
        ],
    ),

    # =========================================================================
    # SQL / DATABASE DEVELOPER
    # =========================================================================
    Question(
        id="sql-int-001",
        topic="Query Optimization & Indexing",
        competency="Database Systems",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="sql",
        track="fullstack",
        text=(
            "How does a B-Tree index accelerate SQL queries, what causes an index scan to degrade into a full table scan, "
            "and what are the tradeoffs of adding multiple indexes to a high-write table?"
        ),
        expected_concepts=[
            "B-Tree index maintains sorted hierarchical structure enabling O(log N) lookup instead of O(N) sequential scan",
            "Causes of full table scan: non-sargable predicates (e.g. functions on columns like WHERE UPPER(email)), missing leading index column, low cardinality",
            "Tradeoff: Indexes accelerate SELECT queries but impose write overhead on INSERT/UPDATE/DELETE due to index rebalancing and storage consumption",
        ],
        rubric=[
            RubricCriterion(
                id="btree_mechanism",
                description="Explains B-Tree sorted tree search reducing I/O disk pages",
                max_marks=2.0,
                evidence_guide="Award full marks for explaining logarithmic tree lookup.",
            ),
            RubricCriterion(
                id="index_invalidation",
                description="Identifies non-sargable functions or missing composite index prefixes",
                max_marks=1.5,
                evidence_guide="Awarded for explaining why functions on indexed columns prevent index usage.",
            ),
            RubricCriterion(
                id="write_tradeoff",
                description="Explains write amplification and memory/disk storage tradeoffs",
                max_marks=1.5,
                evidence_guide="Awarded for noting write latency on INSERT/UPDATE.",
            ),
        ],
    ),

    # =========================================================================
    # GENERAL SOFTWARE ENGINEER
    # =========================================================================
    Question(
        id="se-int-001",
        topic="Algorithms & System Complexity",
        competency="Computer Science Fundamentals",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        response_type="verbal",
        language="python",
        track="python",
        text=(
            "Explain how a Hash Table achieves average O(1) time complexity for lookup and insertion, "
            "how hash collisions are resolved (chaining vs open addressing), and what happens in the worst-case scenario."
        ),
        expected_concepts=[
            "Hash function converts arbitrary keys into array bucket indices in O(1) time",
            "Collisions: separate chaining (linked list / balanced tree per bucket) vs open addressing (linear probing, quadratic probing)",
            "Worst-case: All keys hash to the same bucket degrading operations to O(N)",
            "Load factor triggers dynamic resizing and rehashing to maintain low collision probability",
        ],
        rubric=[
            RubricCriterion(
                id="hash_table_fundamentals",
                description="Explains key-to-index mapping via hash function for O(1) expected time",
                max_marks=2.0,
                evidence_guide="Award full marks for explaining hash function array indexing.",
            ),
            RubricCriterion(
                id="collision_resolution",
                description="Distinguishes separate chaining from open addressing",
                max_marks=1.5,
                evidence_guide="Awarded for explaining chaining or linear probing.",
            ),
            RubricCriterion(
                id="worst_case_and_resizing",
                description="Explains O(N) worst-case degradation and load factor resizing",
                max_marks=1.5,
                evidence_guide="Awarded for mentioning load factor or rehashing.",
            ),
        ],
    ),
]


def get_role_specialized_questions(role_family: Optional[str] = None) -> List[Question]:
    """Retrieves curated questions mapped to a specific role family."""
    if not role_family:
        return ROLE_SPECIALIZED_QUESTIONS
    rf = role_family.lower()
    matches = [q for q in ROLE_SPECIALIZED_QUESTIONS if rf in q.id.lower() or rf in q.topic.lower()]
    return matches or ROLE_SPECIALIZED_QUESTIONS
