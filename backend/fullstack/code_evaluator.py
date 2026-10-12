"""
Safe, isolated code evaluation and static analysis for Full-Stack interview questions.
Supports:
1. JavaScript execution via Node.js in isolated subprocesses with timeouts.
2. SQL execution via in-memory SQLite sandbox with schema initialization and verified datasets.
3. Python execution delegation for full-stack backend (FastAPI/Django) tasks.
Arbitrary candidate code is NEVER executed inside the main FastAPI process.
"""

import json
import logging
import os
import re
import sqlite3
import subprocess
from typing import Dict, Any, List, Optional
from backend.code_evaluator import CodeEvaluator as PythonCodeEvaluator

logger = logging.getLogger(__name__)


class FullStackCodeEvaluator:
    """Executes and verifies multi-language Full-Stack candidate code."""

    @classmethod
    def evaluate_javascript(
        cls,
        candidate_code: str,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        function_name: Optional[str] = None,
        timeout_seconds: float = 2.5,
    ) -> Dict[str, Any]:
        """
        Runs candidate JavaScript code against test cases in an isolated Node.js subprocess.
        """
        code = candidate_code.strip()
        if not code:
            return {
                "executed": False,
                "syntax_valid": False,
                "syntax_error": "Code submission is empty.",
                "tests_passed": 0,
                "tests_total": len(test_cases) if test_cases else 0,
                "test_results": [],
                "execution_error": None,
                "language": "javascript",
            }

        # Build runner script
        test_cases = test_cases or []
        runner_js = cls._build_js_runner_script(
            candidate_code=code,
            test_cases=test_cases,
            function_name=function_name,
        )

        try:
            # Run in isolated Node.js subprocess with minimal controlled env
            clean_env = {
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "TEMP": os.environ.get("TEMP", ""),
                "TMP": os.environ.get("TMP", ""),
            }
            completed = subprocess.run(
                ["node", "-e", runner_js],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=clean_env,
            )

            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()

            if not stdout:
                # Node failed before outputting JSON (e.g., SyntaxError)
                syntax_match = re.search(r"SyntaxError:.*", stderr)
                syntax_err = syntax_match.group(0) if syntax_match else (stderr or "JavaScript execution failed.")
                return {
                    "executed": False,
                    "syntax_valid": False,
                    "syntax_error": syntax_err,
                    "tests_passed": 0,
                    "tests_total": len(test_cases),
                    "test_results": [],
                    "execution_error": stderr or None,
                    "language": "javascript",
                }

            result_data = json.loads(stdout)
            result_data["language"] = "javascript"
            return result_data

        except subprocess.TimeoutExpired:
            return {
                "executed": False,
                "syntax_valid": True,
                "syntax_error": None,
                "tests_passed": 0,
                "tests_total": len(test_cases),
                "test_results": [],
                "execution_error": f"Execution timed out ({timeout_seconds}s limit exceeded - potential infinite loop).",
                "language": "javascript",
            }
        except Exception as exc:
            return {
                "executed": False,
                "syntax_valid": False,
                "syntax_error": str(exc),
                "tests_passed": 0,
                "tests_total": len(test_cases),
                "test_results": [],
                "execution_error": str(exc),
                "language": "javascript",
            }

    @classmethod
    def _build_js_runner_script(
        cls,
        candidate_code: str,
        test_cases: List[Dict[str, Any]],
        function_name: Optional[str] = None,
    ) -> str:
        """Constructs safe Node.js runner that tests candidate function and outputs JSON."""
        # Detect function name if not explicitly given
        target_fn = function_name
        if not target_fn:
            match = re.search(r"function\s+([a-zA-Z0-9_$]+)\s*\(", candidate_code)
            if not match:
                match = re.search(r"(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*", candidate_code)
            if match:
                target_fn = match.group(1)

        tests_json = json.dumps(test_cases)
        return f"""
const assert = require('assert');

let candidateOutput = {{
    executed: true,
    syntax_valid: true,
    syntax_error: null,
    tests_passed: 0,
    tests_total: {len(test_cases)},
    test_results: [],
    execution_error: null
}};

try {{
    // 1. Evaluate candidate code
    {candidate_code}

    const testCases = {tests_json};
    const targetFn = typeof {target_fn if target_fn else "undefined"} !== 'undefined' ? {target_fn if target_fn else "null"} : null;

    if (testCases.length > 0 && !targetFn) {{
        candidateOutput.execution_error = "Target function '{target_fn or 'function'}' is not defined.";
        candidateOutput.syntax_valid = false;
        console.log(JSON.stringify(candidateOutput));
        process.exit(0);
    }}

    // 2. Run test cases
    for (let i = 0; i < testCases.length; i++) {{
        const tc = testCases[i];
        const rawArgs = tc.input !== undefined ? (Array.isArray(tc.input) ? tc.input : [tc.input]) : [];
        const inputArgs = rawArgs.map(arg => {{
            if (arg === '__parity_fn__') return (x) => x % 2 === 0 ? 'even' : 'odd';
            return arg;
        }});
        const expected = tc.expected;

        try {{
            const actual = targetFn.apply(null, inputArgs);
            let passed = false;
            try {{
                assert.deepStrictEqual(actual, expected);
                passed = true;
            }} catch (_) {{
                passed = false;
            }}

            if (passed) {{
                candidateOutput.tests_passed++;
            }}

            candidateOutput.test_results.push({{
                test_number: i + 1,
                input: inputArgs,
                expected: expected,
                actual: actual,
                passed: passed
            }});
        }} catch (callErr) {{
            candidateOutput.test_results.push({{
                test_number: i + 1,
                input: inputArgs,
                expected: expected,
                actual: null,
                error: callErr.message || String(callErr),
                passed: false
            }});
        }}
    }}
}} catch (runtimeErr) {{
    candidateOutput.syntax_valid = false;
    candidateOutput.execution_error = runtimeErr.message || String(runtimeErr);
}}

console.log(JSON.stringify(candidateOutput));
"""

    @classmethod
    def evaluate_sql(
        cls,
        candidate_sql: str,
        db_schema: str,
        expected_rows: Optional[List[Dict[str, Any]]] = None,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Executes candidate SQL query against an in-memory SQLite sandbox with verified schema and data.
        """
        query = candidate_sql.strip()
        # Clean trailing semicolon or comments
        query = re.sub(r"--.*$", "", query, flags=re.MULTILINE).strip()

        if not query:
            return {
                "executed": False,
                "syntax_valid": False,
                "syntax_error": "SQL query submission is empty.",
                "tests_passed": 0,
                "tests_total": 1,
                "test_results": [],
                "execution_error": None,
                "language": "sql",
            }

        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        try:
            # 1. Initialize schema and seed data
            if db_schema and db_schema.strip():
                cursor.executescript(db_schema)

            # 2. Run candidate query
            cursor.execute(query)
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            # Format actual rows as list of dicts
            actual_records = [
                {col_names[idx].lower(): val for idx, val in enumerate(row)}
                for row in rows
            ]

            # 3. Compare with expected data
            expected = expected_rows or []
            if test_cases and not expected:
                expected = test_cases[0].get("expected", [])

            passed = False
            # Normalize comparisons
            if len(actual_records) == len(expected):
                passed = True
                for act, exp in zip(actual_records, expected):
                    # Check each expected key
                    for k, v in exp.items():
                        if str(act.get(k.lower())).lower() != str(v).lower():
                            passed = False
                            break
                    if not passed:
                        break

            return {
                "executed": True,
                "syntax_valid": True,
                "syntax_error": None,
                "tests_passed": 1 if passed else 0,
                "tests_total": 1,
                "test_results": [{
                    "expected": expected,
                    "actual": actual_records,
                    "passed": passed,
                }],
                "execution_error": None,
                "language": "sql",
            }

        except sqlite3.OperationalError as e:
            return {
                "executed": False,
                "syntax_valid": False,
                "syntax_error": f"SQLite OperationalError: {e}",
                "tests_passed": 0,
                "tests_total": 1,
                "test_results": [],
                "execution_error": str(e),
                "language": "sql",
            }
        except Exception as e:
            return {
                "executed": False,
                "syntax_valid": False,
                "syntax_error": str(e),
                "tests_passed": 0,
                "tests_total": 1,
                "test_results": [],
                "execution_error": str(e),
                "language": "sql",
            }
        finally:
            conn.close()

    @classmethod
    def run_isolated_snippet(cls, snippet: str, language: str = "javascript", db_schema: Optional[str] = None) -> Optional[str]:
        """Runs a snippet and captures stdout for output-prediction comparison."""
        lang = (language or "").lower()
        if lang in ("javascript", "js", "typescript", "ts"):
            try:
                completed = subprocess.run(
                    ["node", "-e", snippet],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    env={"PATH": os.environ.get("PATH", "")},
                )
                if completed.returncode == 0:
                    return completed.stdout.strip()
            except Exception as e:
                logger.warning("Error running JS snippet: %s", e)
                return None

        elif lang == "sql" and db_schema:
            try:
                conn = sqlite3.connect(":memory:")
                cur = conn.cursor()
                cur.executescript(db_schema)
                cur.execute(snippet)
                rows = cur.fetchall()
                conn.close()
                return "\n".join(str(r) for r in rows)
            except Exception as e:
                logger.warning("Error running SQL snippet: %s", e)
                return None

        # Fallback to Python evaluator
        return PythonCodeEvaluator.run_isolated_snippet(snippet)

    @classmethod
    def evaluate_code(
        cls,
        candidate_code: str,
        language: str = "javascript",
        test_cases: Optional[List[Dict[str, Any]]] = None,
        function_name: Optional[str] = None,
        db_schema: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Unified dispatch to language-specific evaluator."""
        lang = (language or "javascript").lower()
        if lang in ("javascript", "js", "typescript", "ts"):
            return cls.evaluate_javascript(candidate_code, test_cases, function_name)
        elif lang == "sql":
            return cls.evaluate_sql(candidate_code, db_schema or "", test_cases=test_cases)
        elif lang in ("python", "py"):
            return PythonCodeEvaluator.evaluate_code(candidate_code, test_cases, function_name)
        else:
            return cls.evaluate_javascript(candidate_code, test_cases, function_name)
