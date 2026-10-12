"""
Curated Full-Stack Question Bank.
Covers core full-stack domains across Beginner, Intermediate, and Advanced tiers:
- HTML & CSS (Box model, Flexbox/Grid, Specificity, Accessibility)
- JavaScript (Event loop, Closures, Promises, Prototypes, Array transformations)
- React (Hooks, Reconciliation, State updates, Custom hooks, Stale closures)
- Backend & REST APIs (HTTP methods, Status codes, Middleware, JWT vs Cookies, CORS)
- SQL & Databases (Aggregation, Joins, Indexing, ACID transactions, SQLite sandbox verification)
- Full-Stack Integration & Architecture (Auth flows, 401 debugging, Race conditions, Performance)
"""

from typing import List, Dict, Optional, Any
from backend.models import (
    Question,
    DifficultyLevel,
    QuestionType,
    RubricCriterion,
)

FULLSTACK_QUESTION_BANK: List[Question] = [
    # =========================================================================
    # 1. HTML & CSS
    # =========================================================================
    Question(
        id="fs-beg-html-001",
        topic="HTML & Semantic Web",
        competency="Frontend Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        track="fullstack",
        language="html",
        text=(
            "What is semantic HTML, why is it critical for accessibility (a11y) and SEO, "
            "and how does `<main>`, `<article>`, and `<section>` differ from standard `<div>` containers?"
        ),
        expected_concepts=[
            "Semantic tags convey meaning to browsers, search engines, and screen readers (accessibility tree)",
            "<main> represents the dominant unique content of the document (only one per page)",
            "<article> represents a self-contained, independently distributable composition (e.g., blog post)",
            "<section> groups thematically related content with a heading",
            "<div> has no semantic meaning and is purely a stylistic container",
        ],
        rubric=[
            RubricCriterion(
                id="semantic_definition",
                description="Explains what semantic HTML is and its impact on screen readers and SEO",
                max_marks=2.0,
                evidence_guide="Award full marks for explaining that semantic tags give role/meaning to accessibility trees and search engines.",
            ),
            RubricCriterion(
                id="element_distinctions",
                description="Clearly distinguishes <main>, <article>, and <section> with accurate use cases",
                max_marks=2.0,
                evidence_guide="Award full marks for stating article is self-contained and distributable, section is thematic, main is primary content.",
            ),
            RubricCriterion(
                id="div_contrast",
                description="Explains why generic div containers should not replace semantic elements",
                max_marks=1.0,
                evidence_guide="Awarded for noting div lacks accessibility roles and semantic landmark structure.",
            ),
        ],
        reference_answer=(
            "Semantic HTML uses tags that convey the meaning and purpose of their enclosed content rather than just presentation. "
            "It is critical because assistive technologies (screen readers) build an accessibility tree that relies on semantic landmarks "
            "for navigation, while search engine crawlers use semantic structure to index content relevance. `<main>` represents the primary, "
            "non-repeating content of the page. `<article>` is a self-contained composition intended for independent syndication (e.g., news article). "
            "`<section>` is a generic thematic grouping of content, typically accompanied by a heading. In contrast, `<div>` has no semantic "
            "meaning and should only be used as a styling or grouping hook."
        ),
    ),

    Question(
        id="fs-beg-css-001",
        topic="CSS Layout & Box Model",
        competency="Frontend Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        track="fullstack",
        language="css",
        text=(
            "Explain the CSS Box Model. What is the crucial difference between `box-sizing: content-box` "
            "and `box-sizing: border-box`, and why is `border-box` universally favored in modern responsive design?"
        ),
        expected_concepts=[
            "Box model consists of content, padding, border, and margin",
            "content-box: width and height apply only to content; padding and border add to the element's total rendered width",
            "border-box: width and height include content, padding, and border; padding and border absorb inward",
            "border-box prevents unexpected layout overflow when padding is added and simplifies percentage/grid calculations",
        ],
        rubric=[
            RubricCriterion(
                id="box_model_components",
                description="Identifies the four layers: content, padding, border, margin",
                max_marks=1.5,
                evidence_guide="Award full marks for listing all 4 concentric layers in order.",
            ),
            RubricCriterion(
                id="box_sizing_difference",
                description="Explains the exact math difference between content-box and border-box",
                max_marks=2.5,
                evidence_guide="Award full marks for noting content-box adds padding/border to width, whereas border-box includes them within width.",
            ),
            RubricCriterion(
                id="responsive_preference",
                description="Explains why border-box is standard in responsive development",
                max_marks=1.0,
                evidence_guide="Awarded for explaining elimination of accidental layout breaking when adding padding.",
            ),
        ],
        reference_answer=(
            "The CSS Box Model consists of four concentric boxes: content, padding, border, and margin. "
            "With `box-sizing: content-box` (the default), setting `width: 300px` with `padding: 20px` and `border: 2px` produces a total rendered "
            "width of 344px (300 + 40 + 4). With `box-sizing: border-box`, setting `width: 300px` guarantees the element's total border-to-border width "
            "remains exactly 300px, with the padding and border shrinking the available content area inward. Modern developers reset all elements to "
            "`border-box` because it makes responsive multi-column layouts predictable and prevents unexpected horizontal scrolling."
        ),
    ),

    Question(
        id="fs-int-css-001",
        topic="CSS Layout & Box Model",
        competency="Frontend Fundamentals",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CODE_OUTPUT,
        track="fullstack",
        language="css",
        text="What will be the rendered text color of the button below, and what is the exact specificity calculation for each matching selector?",
        code_snippet=(
            "/* CSS Rules */\n"
            "#nav .actions button.btn { color: red; }        /* Rule 1 */\n"
            "button.btn.primary { color: blue; }             /* Rule 2 */\n"
            "#nav button#submit-btn { color: green; }        /* Rule 3 */\n"
            "\n"
            "/* HTML */\n"
            "<nav id=\"nav\">\n"
            "  <div class=\"actions\">\n"
            "    <button id=\"submit-btn\" class=\"btn primary\">Submit</button>\n"
            "  </div>\n"
            "</nav>"
        ),
        expected_output="green",
        expected_concepts=[
            "Specificity calculation in format (Inline, ID, Class/Attribute/Pseudo, Element)",
            "Rule 1 (#nav .actions button.btn): (0, 1, 2, 1)",
            "Rule 2 (button.btn.primary): (0, 0, 2, 1)",
            "Rule 3 (#nav button#submit-btn): (0, 2, 0, 1)",
            "Rule 3 wins with 2 IDs (green color)",
        ],
        rubric=[
            RubricCriterion(
                id="correct_winner",
                description="Identifies 'green' as the final applied color",
                max_marks=2.5,
                evidence_guide="Full marks for explicitly stating the button will be green.",
            ),
            RubricCriterion(
                id="specificity_tuples",
                description="Accurately breaks down specificity counts for the competing selectors",
                max_marks=2.5,
                evidence_guide="Awarded for noting Rule 3 has 2 ID selectors (0,2,0,1) which outweighs Rule 1's single ID (0,1,2,1).",
            ),
        ],
        reference_answer=(
            "The button will be GREEN.\n"
            "Specificity breakdown:\n"
            "- Rule 1: #nav (1 ID) + .actions, .btn (2 classes) + button (1 tag) = (0, 1, 2, 1)\n"
            "- Rule 2: .btn, .primary (2 classes) + button (1 tag) = (0, 0, 2, 1)\n"
            "- Rule 3: #nav, #submit-btn (2 IDs) + button (1 tag) = (0, 2, 0, 1)\n"
            "Because an ID selector always outweighs any number of class selectors, Rule 3 with two IDs (0, 2, 0, 1) has the highest specificity."
        ),
    ),

    # =========================================================================
    # 2. JAVASCRIPT CORE & ASYNC
    # =========================================================================
    Question(
        id="fs-beg-js-001",
        topic="JavaScript Core",
        competency="JavaScript Programming",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_OUTPUT,
        track="fullstack",
        language="javascript",
        text="What will be logged to the console when the following JavaScript code runs, and in what exact sequence?",
        code_snippet=(
            "console.log('1');\n"
            "\n"
            "setTimeout(() => {\n"
            "    console.log('2');\n"
            "}, 0);\n"
            "\n"
            "Promise.resolve().then(() => {\n"
            "    console.log('3');\n"
            "}).then(() => {\n"
            "    console.log('4');\n"
            "});\n"
            "\n"
            "console.log('5');"
        ),
        expected_output="1\n5\n3\n4\n2",
        expected_concepts=[
            "Synchronous execution runs first ('1', '5')",
            "Microtask queue (Promise.then) runs before macrotask queue ('3', '4')",
            "Macrotask queue (setTimeout) runs after all microtasks have drained ('2')",
            "Output sequence: 1, 5, 3, 4, 2",
        ],
        rubric=[
            RubricCriterion(
                id="exact_sequence",
                description="States the exact sequence: 1, 5, 3, 4, 2",
                max_marks=3.0,
                evidence_guide="Full marks for the exact chronological order.",
            ),
            RubricCriterion(
                id="event_loop_explanation",
                description="Explains difference between synchronous code, microtask queue (Promises), and macrotask queue (setTimeout)",
                max_marks=2.0,
                evidence_guide="Awarded for explicitly explaining why Promise microtasks run before setTimeout macrotask.",
            ),
        ],
        reference_answer=(
            "The output sequence is:\n1\n5\n3\n4\n2\n\n"
            "Explanation:\n"
            "1. Synchronous code executes immediately: '1', then '5'.\n"
            "2. `setTimeout` schedules its callback in the macrotask/task queue.\n"
            "3. The resolved Promise chain schedules microtasks in the microtask queue: '3', then '4'.\n"
            "4. The Event Loop prioritizes the microtask queue before the next macrotask, printing '3' and '4'.\n"
            "5. Finally, the Event Loop takes the callback from the macrotask queue, printing '2'."
        ),
    ),

    Question(
        id="fs-beg-js-002",
        topic="JavaScript Core",
        competency="JavaScript Programming",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_WRITING,
        track="fullstack",
        language="javascript",
        text=(
            "Implement a function `createCounter(initialValue)` that uses closures to maintain a private counter state. "
            "It must return an object with three methods:\n"
            "- `increment()`: increases counter by 1 and returns the new value\n"
            "- `decrement()`: decreases counter by 1 and returns the new value\n"
            "- `reset()`: resets the counter back to initialValue and returns it\n"
            "The counter state must NOT be accessible directly via property access."
        ),
        starter_code=(
            "function createCounter(initialValue = 0) {\n"
            "    // Implement closure counter\n"
            "}\n"
        ),
        function_name="createCounter",
        test_cases=[
            {
                "input": [5],
                "expected": {"inc": 6, "dec": 5, "res": 5},
                "notes": "Verify increment, decrement, reset cycle",
            },
            {
                "input": [0],
                "expected": {"inc": 1, "dec": 0, "res": 0},
                "notes": "Verify zero boundary",
            },
        ],
        expected_concepts=[
            "Lexical scope & closures preserving private state",
            "Returning object with increment, decrement, reset methods",
            "State remains private inside outer function scope",
        ],
        rubric=[
            RubricCriterion(
                id="closure_encapsulation",
                description="Correctly encapsulates counter state without exposing it on returned object",
                max_marks=2.5,
                evidence_guide="State must be held in local variable, not this.val or obj.val.",
            ),
            RubricCriterion(
                id="method_behavior",
                description="increment, decrement, and reset functions work accurately",
                max_marks=2.5,
                evidence_guide="All test cases pass and return updated count.",
            ),
        ],
        reference_answer=(
            "function createCounter(initialValue = 0) {\n"
            "    let current = initialValue;\n"
            "    return {\n"
            "        increment: () => ++current,\n"
            "        decrement: () => --current,\n"
            "        reset: () => { current = initialValue; return current; }\n"
            "    };\n"
            "}"
        ),
    ),

    Question(
        id="fs-int-js-001",
        topic="JavaScript Core",
        competency="JavaScript Programming",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CODE_WRITING,
        track="fullstack",
        language="javascript",
        text=(
            "Implement an array grouping function `groupBy(array, keyOrFn)` that groups an array of objects "
            "into a dictionary. `keyOrFn` can be either a property name string (e.g., 'category') or a callback function (e.g., item => item.age >= 18 ? 'adult' : 'minor'). "
            "Return an object where each key maps to an array of matching items."
        ),
        starter_code=(
            "function groupBy(array, keyOrFn) {\n"
            "    // Your implementation here\n"
            "}\n"
        ),
        function_name="groupBy",
        test_cases=[
            {
                "input": [
                    [
                        {"name": "Alice", "role": "admin"},
                        {"name": "Bob", "role": "user"},
                        {"name": "Charlie", "role": "admin"}
                    ],
                    "role"
                ],
                "expected": {
                    "admin": [{"name": "Alice", "role": "admin"}, {"name": "Charlie", "role": "admin"}],
                    "user": [{"name": "Bob", "role": "user"}]
                }
            },
            {
                "input": [
                    [1, 2, 3, 4, 5, 6],
                    "__parity_fn__"  # Replaced in test harness with parity callback
                ],
                "expected": {
                    "even": [2, 4, 6],
                    "odd": [1, 3, 5]
                }
            }
        ],
        expected_concepts=[
            "Array reduce or iteration pattern",
            "Handling both string property and function callback selectors",
            "Grouping elements into bucketed arrays without mutating inputs",
        ],
        rubric=[
            RubricCriterion(
                id="reducer_logic",
                description="Accurately groups elements into key-based arrays",
                max_marks=2.5,
                evidence_guide="Must return object mapping keys to arrays of elements.",
            ),
            RubricCriterion(
                id="dual_selector_support",
                description="Handles both string property accessor and selector function",
                max_marks=2.5,
                evidence_guide="Must check typeof keyOrFn === 'function'.",
            ),
        ],
        reference_answer=(
            "function groupBy(array, keyOrFn) {\n"
            "    const getKey = typeof keyOrFn === 'function' ? keyOrFn : (item) => item[keyOrFn];\n"
            "    return array.reduce((acc, item) => {\n"
            "        const key = getKey(item);\n"
            "        if (!acc[key]) acc[key] = [];\n"
            "        acc[key].push(item);\n"
            "        return acc;\n"
            "    }, {});\n"
            "}"
        ),
    ),

    # =========================================================================
    # 3. REACT & FRONTEND ARCHITECTURE
    # =========================================================================
    Question(
        id="fs-beg-react-001",
        topic="React & Component Architecture",
        competency="React Architecture",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        track="fullstack",
        language="javascript",
        text=(
            "In React, why must state never be mutated directly (e.g. `state.count = 5`), and why does React "
            "require a unique `key` prop when rendering lists? What problems happen if an array index is used as the key?"
        ),
        expected_concepts=[
            "Immutability enables shallow comparison in React's reconciliation / virtual DOM diffing",
            "Direct mutation does not trigger re-render because object reference remains identical",
            "Keys give elements stable identity across renders so React re-uses existing DOM nodes instead of unmounting",
            "Using array index as key breaks when elements are filtered, sorted, added, or deleted from middle/beginning",
            "Index keys cause component state (like inputs, checkboxes) to bleed into wrong sibling elements",
        ],
        rubric=[
            RubricCriterion(
                id="immutability_reasons",
                description="Explains why state immutability is required for shallow reference checks and re-renders",
                max_marks=2.5,
                evidence_guide="Must mention shallow reference check or reconciliation algorithm.",
            ),
            RubricCriterion(
                id="key_prop_and_index_pitfall",
                description="Explains key prop purpose and dangers of using array indices as keys",
                max_marks=2.5,
                evidence_guide="Must explain that index key causes wrong input/focus state when list order changes.",
            ),
        ],
        reference_answer=(
            "React relies on state immutability because its reconciliation engine performs shallow reference comparisons (`prev !== next`) "
            "to detect whether a component needs to re-render. Directly mutating an object or array changes its contents but preserves its memory address, "
            "so React assumes nothing changed and skips rendering. The `key` prop provides a persistent identity for list items across renders. "
            "React uses keys to track which items have been added, moved, or deleted. If an array index is used as key, inserting or deleting an item "
            "shifts the indices of all subsequent elements. This fools React into reusing DOM nodes with mismatched internal state (such as text input "
            "values, focus, or animations), causing severe visual and functional bugs."
        ),
    ),

    Question(
        id="fs-int-react-001",
        topic="React & Component Architecture",
        competency="React Architecture",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.DEBUGGING,
        track="fullstack",
        language="javascript",
        text=(
            "The React component below causes an infinite re-render loop and crashes the browser tab. "
            "Identify the bug, explain why the loop happens, and provide the corrected code using `useCallback` or dependency fixes."
        ),
        code_snippet=(
            "import React, { useState, useEffect } from 'react';\n"
            "\n"
            "function UserProfile({ userId }) {\n"
            "    const [user, setUser] = useState(null);\n"
            "    const [options, setOptions] = useState({ theme: 'dark' });\n"
            "\n"
            "    // Buggy function recreated on every render\n"
            "    const fetchUserData = async () => {\n"
            "        const res = await fetch(`/api/users/${userId}?theme=${options.theme}`);\n"
            "        const data = await res.json();\n"
            "        setUser(data);\n"
            "    };\n"
            "\n"
            "    useEffect(() => {\n"
            "        fetchUserData();\n"
            "    }, [fetchUserData]); // Problematic dependency\n"
            "\n"
            "    return <div>{user ? user.name : 'Loading...'}</div>;\n"
            "}"
        ),
        expected_concepts=[
            "fetchUserData is recreated on every render with a new reference address",
            "useEffect depends on fetchUserData; sees a new reference after every render",
            "useEffect executes fetchUserData -> setUser(data) -> triggers re-render -> new fetchUserData -> infinite loop",
            "Fix 1: Wrap fetchUserData in useCallback with [userId, options.theme] dependencies",
            "Fix 2: Move fetchUserData definition inside useEffect body",
        ],
        rubric=[
            RubricCriterion(
                id="root_cause_diagnosis",
                description="Accurately explains the function reference recreation causing effect re-triggering",
                max_marks=2.5,
                evidence_guide="Must explain that function creation produces a new reference each render.",
            ),
            RubricCriterion(
                id="correct_remediation",
                description="Provides valid idiomatic solution (useCallback or moving function inside effect)",
                max_marks=2.5,
                evidence_guide="Correct code provided with proper dependencies.",
            ),
        ],
        reference_answer=(
            "Bug Cause:\n"
            "On every render, `fetchUserData` is declared anew as a fresh function with a different memory reference. "
            "Because `fetchUserData` is in `useEffect`'s dependency array, React detects a reference change after every render "
            "and re-runs the effect. The effect calls `fetchUserData`, which calls `setUser(data)`. Calling `setUser` schedules a re-render, "
            "which recreates `fetchUserData`, which triggers the effect again, causing an infinite loop.\n\n"
            "Fix 1 (Preferred: define inside effect):\n"
            "useEffect(() => {\n"
            "    let isMounted = true;\n"
            "    async function fetchUserData() {\n"
            "        const res = await fetch(`/api/users/${userId}?theme=${options.theme}`);\n"
            "        const data = await res.json();\n"
            "        if (isMounted) setUser(data);\n"
            "    }\n"
            "    fetchUserData();\n"
            "    return () => { isMounted = false; };\n"
            "}, [userId, options.theme]);\n\n"
            "Fix 2 (useCallback):\n"
            "Wrap `fetchUserData` with `useCallback(async () => { ... }, [userId, options.theme]);`"
        ),
    ),

    # =========================================================================
    # 4. BACKEND & REST APIS
    # =========================================================================
    Question(
        id="fs-beg-api-001",
        topic="Backend & REST APIs",
        competency="Backend & API Architecture",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        track="fullstack",
        language="javascript",
        text=(
            "Explain the difference between `PUT` and `PATCH` in RESTful API design. "
            "Which HTTP methods are idempotent, what does idempotency mean in practical API architecture, "
            "and what HTTP status code should be returned after successfully creating a resource?"
        ),
        expected_concepts=[
            "PUT replaces the entire resource representation (complete update)",
            "PATCH applies partial modifications/deltas to an existing resource",
            "Idempotency: Making identical multiple requests has the same server side-effect as a single request",
            "Idempotent methods: GET, HEAD, PUT, DELETE, OPTIONS (POST and PATCH are generally non-idempotent)",
            "HTTP 201 Created is the standard status code after creating a new resource",
        ],
        rubric=[
            RubricCriterion(
                id="put_patch_distinction",
                description="Distinguishes complete replacement (PUT) from partial update (PATCH)",
                max_marks=2.0,
                evidence_guide="Award full marks for full replacement vs partial delta update.",
            ),
            RubricCriterion(
                id="idempotency_definition_methods",
                description="Defines idempotency accurately and lists idempotent methods",
                max_marks=2.0,
                evidence_guide="Must note GET, PUT, DELETE are idempotent while POST is not.",
            ),
            RubricCriterion(
                id="creation_status_code",
                description="Names HTTP 201 Created as the correct status code",
                max_marks=1.0,
                evidence_guide="Must cite 201 Created.",
            ),
        ],
        reference_answer=(
            "`PUT` is used for full resource replacement. The client sends the entire representation; any omitted fields "
            "are typically removed or reset to defaults. `PATCH` is designed for partial updates, where the client sends only the fields "
            "that need to be modified. An HTTP method is idempotent if executing it multiple times produces the exact same server side-effects "
            "as executing it once. `GET`, `PUT`, `DELETE`, `HEAD`, and `OPTIONS` are idempotent (e.g., deleting resource #5 three times leaves "
            "it deleted without changing other state). `POST` is not idempotent because repeating it creates multiple duplicate resources. "
            "The standard status code returned upon successful resource creation is `201 Created` (frequently accompanied by a `Location` header)."
        ),
    ),

    Question(
        id="fs-int-api-001",
        topic="Backend & REST APIs",
        competency="Backend & API Architecture",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        track="fullstack",
        language="javascript",
        text=(
            "When authenticating users in a modern web application, compare storing JWTs in `localStorage` "
            "versus `HttpOnly, Secure, SameSite=Strict` cookies. What specific vulnerabilities (XSS vs CSRF) "
            "threaten each approach, and how does the backend verify a JWT's authenticity without contacting a database?"
        ),
        expected_concepts=[
            "localStorage is accessible to any running JavaScript: highly vulnerable to XSS (Cross-Site Scripting)",
            "HttpOnly cookies cannot be read by JavaScript (mitigates token theft via XSS)",
            "Cookies are automatically sent by browsers: vulnerable to CSRF (Cross-Site Request Forgery)",
            "SameSite=Strict/Lax and CSRF tokens protect cookies against CSRF",
            "JWT verification is stateless: backend uses secret/public key to hash header + payload and compare with signature",
        ],
        rubric=[
            RubricCriterion(
                id="storage_threat_analysis",
                description="Analyzes XSS risk of localStorage vs CSRF risk of cookies",
                max_marks=2.5,
                evidence_guide="Full marks for explaining that XSS steals localStorage tokens, while cookies need SameSite/CSRF protection.",
            ),
            RubricCriterion(
                id="jwt_verification_mechanism",
                description="Explains cryptographic signature verification of header and payload",
                max_marks=2.5,
                evidence_guide="Must explain HMAC/RSA signature check against header.payload without DB query.",
            ),
        ],
        reference_answer=(
            "Storing JWTs in `localStorage` exposes them to Cross-Site Scripting (XSS). If an attacker injects malicious JavaScript via a third-party "
            "dependency or unsanitized input, they can access `localStorage.getItem('token')` and exfiltrate credentials. In contrast, `HttpOnly` cookies "
            "cannot be read by client-side scripts, protecting tokens from XSS theft. However, because browsers automatically attach cookies to matching requests, "
            "cookies are susceptible to Cross-Site Request Forgery (CSRF). This is mitigated by setting `SameSite=Strict` or `SameSite=Lax`, using HTTPS (`Secure`), "
            "and employing anti-CSRF tokens. The backend verifies a JWT without database lookups using cryptographic signatures: it decodes the header and payload, "
            "computes the cryptographic hash using the shared secret or public key (e.g., HMAC-SHA256(header + '.' + payload, secret)), and checks if the result matches "
            "the token's signature. If they match, the payload has not been tampered with."
        ),
    ),

    # =========================================================================
    # 5. SQL & DATABASES
    # =========================================================================
    Question(
        id="fs-beg-sql-001",
        topic="SQL & Databases",
        competency="Database Engineering",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_WRITING,
        track="fullstack",
        language="sql",
        text=(
            "Write a SQL query to find the total revenue generated by each product category. "
            "Only include categories with total revenue greater than 1000, ordered from highest revenue to lowest.\n"
            "Table `orders`: `(id INTEGER, category TEXT, revenue REAL)`"
        ),
        starter_code="SELECT category, SUM(revenue) AS total_revenue FROM orders ...",
        db_schema=(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, category TEXT, revenue REAL);\n"
            "INSERT INTO orders VALUES (1, 'Electronics', 600.0);\n"
            "INSERT INTO orders VALUES (2, 'Electronics', 800.0);\n"
            "INSERT INTO orders VALUES (3, 'Books', 300.0);\n"
            "INSERT INTO orders VALUES (4, 'Books', 200.0);\n"
            "INSERT INTO orders VALUES (5, 'Home', 1200.0);\n"
            "INSERT INTO orders VALUES (6, 'Home', 400.0);\n"
        ),
        test_cases=[
            {
                "expected": [
                    {"category": "Home", "total_revenue": 1600.0},
                    {"category": "Electronics", "total_revenue": 1400.0},
                ]
            }
        ],
        expected_concepts=[
            "GROUP BY category",
            "HAVING SUM(revenue) > 1000 (not WHERE)",
            "ORDER BY total_revenue DESC",
        ],
        rubric=[
            RubricCriterion(
                id="group_by_having",
                description="Uses GROUP BY with HAVING clause for aggregate filtering",
                max_marks=3.0,
                evidence_guide="Must use HAVING SUM(revenue) > 1000 rather than WHERE.",
            ),
            RubricCriterion(
                id="order_by_desc",
                description="Orders by total revenue descending",
                max_marks=2.0,
                evidence_guide="Must have ORDER BY ... DESC.",
            ),
        ],
        reference_answer=(
            "SELECT category, SUM(revenue) AS total_revenue\n"
            "FROM orders\n"
            "GROUP BY category\n"
            "HAVING SUM(revenue) > 1000\n"
            "ORDER BY total_revenue DESC;"
        ),
    ),

    Question(
        id="fs-int-sql-001",
        topic="SQL & Databases",
        competency="Database Engineering",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CODE_WRITING,
        track="fullstack",
        language="sql",
        text=(
            "Write a SQL query to find all customers who have NEVER placed an order. "
            "Return `customer_id` and `name`, ordered alphabetically by `name`.\n"
            "Tables:\n"
            "- `customers`: `(id INTEGER, name TEXT)`\n"
            "- `orders`: `(id INTEGER, customer_id INTEGER, amount REAL)`"
        ),
        starter_code="SELECT customers.id, customers.name FROM customers ...",
        db_schema=(
            "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);\n"
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL);\n"
            "INSERT INTO customers VALUES (1, 'Alice');\n"
            "INSERT INTO customers VALUES (2, 'Bob');\n"
            "INSERT INTO customers VALUES (3, 'Charlie');\n"
            "INSERT INTO customers VALUES (4, 'Diana');\n"
            "INSERT INTO orders VALUES (101, 1, 99.0);\n"
            "INSERT INTO orders VALUES (102, 3, 149.0);\n"
        ),
        test_cases=[
            {
                "expected": [
                    {"id": 2, "name": "Bob"},
                    {"id": 4, "name": "Diana"},
                ]
            }
        ],
        expected_concepts=[
            "LEFT JOIN customers WITH orders ON customers.id = orders.customer_id",
            "WHERE orders.id IS NULL (or NOT EXISTS / NOT IN)",
            "ORDER BY customers.name ASC",
        ],
        rubric=[
            RubricCriterion(
                id="outer_join_null_filter",
                description="Correctly implements LEFT JOIN with IS NULL filter or NOT EXISTS",
                max_marks=3.0,
                evidence_guide="Must isolate customers having no order record.",
            ),
            RubricCriterion(
                id="sorting_and_columns",
                description="Returns id and name sorted alphabetically",
                max_marks=2.0,
                evidence_guide="Output matches expected records exactly.",
            ),
        ],
        reference_answer=(
            "SELECT c.id, c.name\n"
            "FROM customers c\n"
            "LEFT JOIN orders o ON c.id = o.customer_id\n"
            "WHERE o.id IS NULL\n"
            "ORDER BY c.name ASC;"
        ),
    ),

    # =========================================================================
    # 6. FULL-STACK INTEGRATION & SCENARIOS
    # =========================================================================
    Question(
        id="fs-int-scen-001",
        topic="Full-Stack Integration & Architecture",
        competency="Full-Stack Systems",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.SCENARIO,
        track="fullstack",
        language="javascript",
        text=(
            "Scenario: A React frontend submits login credentials to a Node/Express backend (`POST /api/auth/login`). "
            "The backend validates credentials and responds with HTTP 200 and an `HttpOnly` session cookie. "
            "However, subsequent requests from the React app to protected endpoints (e.g. `GET /api/dashboard`) receive `HTTP 401 Unauthorized`. "
            "Diagnose the possible causes across CORS, cookies, fetch/axios configuration, and reverse proxy settings, and explain how to fix each."
        ),
        expected_concepts=[
            "Client request missing credentials flag (credentials: 'include' in fetch or withCredentials: true in axios)",
            "CORS Access-Control-Allow-Credentials: true missing on backend",
            "CORS Access-Control-Allow-Origin cannot be wildcard '*' when credentials are sent; must match exact origin",
            "Cookie SameSite/Secure mismatch (e.g. SameSite=None without Secure, or Secure over localhost HTTP)",
            "Reverse proxy (Nginx/Cloudflare) stripping Cookie headers or not forwarding host headers",
        ],
        rubric=[
            RubricCriterion(
                id="client_credentials_flag",
                description="Identifies missing credentials: 'include' or withCredentials: true on frontend request",
                max_marks=2.0,
                evidence_guide="Must cite fetch credentials flag or axios config.",
            ),
            RubricCriterion(
                id="backend_cors_credentials",
                description="Identifies Access-Control-Allow-Credentials and exact origin requirements",
                max_marks=2.0,
                evidence_guide="Must explain that wildcard origin '*' is prohibited with credentials.",
            ),
            RubricCriterion(
                id="cookie_attributes_proxy",
                description="Mentions SameSite/Secure cookie attribute mismatch or proxy stripping",
                max_marks=1.0,
                evidence_guide="Awarded for noting Secure on HTTP localhost or Nginx header forwarding.",
            ),
        ],
        reference_answer=(
            "This classic full-stack authentication failure is caused by one of three issues:\n"
            "1. Client-side missing credentials flag: By default, browser `fetch` does not send cookies on cross-origin requests. "
            "The frontend must specify `fetch(url, { credentials: 'include' })` or `axios.defaults.withCredentials = true`.\n"
            "2. Backend CORS configuration: When sending credentials, the backend must set `Access-Control-Allow-Credentials: true`. "
            "Crucially, `Access-Control-Allow-Origin` CANNOT be the wildcard `*`; it must explicitly match the client origin (e.g. `http://localhost:3000`).\n"
            "3. Cookie Attributes & Protocols: If the cookie is marked `Secure`, the browser will not send it over HTTP unless on localhost. "
            "If the frontend and backend are on different domains, `SameSite=None; Secure` is required. Additionally, check that reverse proxies "
            "like Nginx are not stripping `Cookie` headers with proxy_set_header."
        ),
    ),

    Question(
        id="fs-adv-scen-001",
        topic="Full-Stack Integration & Architecture",
        competency="Full-Stack Systems",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.SCENARIO,
        track="fullstack",
        language="javascript",
        text=(
            "Scenario: A high-traffic e-commerce flash sale endpoint (`POST /api/orders`) experiences race conditions: "
            "two customers concurrently buy the last remaining item in stock, resulting in negative inventory (-1). "
            "The database is PostgreSQL. Propose three architectural solutions across database locking, SQL transactions, "
            "and application layer queues to guarantee zero overselling under heavy concurrent load."
        ),
        expected_concepts=[
            "Pessimistic locking: SELECT ... FOR UPDATE within a transaction locks the inventory row until commit",
            "Optimistic concurrency control: UPDATE inventory SET stock = stock - 1 WHERE id = 1 AND stock > 0 (atomic check)",
            "Database constraint: CHECK (stock >= 0) enforces data integrity at the database engine level",
            "Message queue / serialization: Redis queue or transactional inbox to serialize purchase requests per SKU",
        ],
        rubric=[
            RubricCriterion(
                id="db_locking_mechanisms",
                description="Explains pessimistic SELECT FOR UPDATE and atomic conditional updates",
                max_marks=2.5,
                evidence_guide="Must detail row-level locking or atomic WHERE stock >= quantity.",
            ),
            RubricCriterion(
                id="db_constraint_defense",
                description="Recommends CHECK (stock >= 0) constraint as hard guarantee",
                max_marks=1.0,
                evidence_guide="Awarded for citing database-level CHECK constraints.",
            ),
            RubricCriterion(
                id="async_queue_architecture",
                description="Explains message queue/Redis serialization for high-throughput concurrency",
                max_marks=1.5,
                evidence_guide="Awarded for detailing Redis atomicity (DECR) or job queue serialization.",
            ),
        ],
        reference_answer=(
            "Three complementary solutions to prevent inventory overselling under high concurrency:\n"
            "1. Atomic Conditional Update (Optimistic): Instead of reading stock into memory and writing back, execute an atomic SQL update:\n"
            "   `UPDATE products SET stock = stock - 1 WHERE id = :id AND stock > 0 RETURNING stock;`\n"
            "   If rows affected is 0, the item was already sold out. This avoids explicit lock contention.\n"
            "2. Pessimistic Row Locking (`SELECT ... FOR UPDATE`): Inside a transaction, lock the row before validation:\n"
            "   `BEGIN; SELECT stock FROM products WHERE id = :id FOR UPDATE;`\n"
            "   Concurrent transactions block until the first commits or rolls back, ensuring strictly serial verification.\n"
            "3. Hard Database Invariant: Add a constraint `ALTER TABLE products ADD CONSTRAINT stock_non_negative CHECK (stock >= 0);` "
            "so any transaction attempting to drop stock below 0 aborts with an integrity violation.\n"
            "4. Application-Layer Queue: Offload high-traffic flash sales to Redis using atomic `DECR` or a FIFO message queue (BullMQ/RabbitMQ) "
            "to buffer requests and process inventory updates serially per product."
        ),
    ),
]


def get_all_fullstack_questions() -> List[Question]:
    """Returns all curated Full-Stack questions."""
    return list(FULLSTACK_QUESTION_BANK)


def get_all_fullstack_topics() -> List[str]:
    """Returns distinct topics present in the Full-Stack question bank."""
    topics = []
    for q in FULLSTACK_QUESTION_BANK:
        if q.topic not in topics:
            topics.append(q.topic)
    return topics


def get_all_fullstack_competencies() -> List[str]:
    """Returns distinct competencies present in the Full-Stack question bank."""
    competencies = []
    for q in FULLSTACK_QUESTION_BANK:
        if q.competency not in competencies:
            competencies.append(q.competency)
    return competencies


# Load Role Specialized Fullstack Questions (SQL/Database Developer, Frontend, etc.)
try:
    from backend.role_questions import ROLE_SPECIALIZED_QUESTIONS
    for _sq in ROLE_SPECIALIZED_QUESTIONS:
        if _sq.track == "fullstack" and _sq.id not in [q.id for q in FULLSTACK_QUESTION_BANK]:
            FULLSTACK_QUESTION_BANK.append(_sq)
except ImportError:
    pass


def get_fullstack_question_by_id(question_id: str) -> Optional[Question]:
    """Finds a question by ID."""
    for q in FULLSTACK_QUESTION_BANK:
        if q.id == question_id:
            return q
    return None


TECH_STACK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "React + Node.js + Express + SQL": {
        "topics": ["React & Component Architecture", "JavaScript Core", "Backend & REST APIs", "SQL & Databases"],
        "description": "Modern full-stack JavaScript environment with relational persistence.",
    },
    "React + FastAPI + PostgreSQL": {
        "topics": ["React & Component Architecture", "Backend & REST APIs", "SQL & Databases", "Full-Stack Integration & Architecture"],
        "description": "High-performance Python backend paired with modern React frontend.",
    },
    "HTML + CSS + JavaScript + REST APIs + SQL": {
        "topics": ["HTML & Semantic Web", "CSS Layout & Box Model", "JavaScript Core", "Backend & REST APIs", "SQL & Databases"],
        "description": "Foundational web standards and comprehensive full-stack tier fundamentals.",
    },
    "Full-Stack Fundamentals (Multi-Technology)": {
        "topics": ["HTML & Semantic Web", "JavaScript Core", "React & Component Architecture", "Backend & REST APIs", "SQL & Databases", "Full-Stack Integration & Architecture"],
        "description": "Broad assessment covering browser frontend, application servers, databases, and system design.",
    },
}

