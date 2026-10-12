"""
Safe, isolated code evaluation and static analysis for Python interview questions.
Enforces security boundaries, runs isolated subprocess execution with timeouts,
and performs AST-based static analysis.
Arbitrary candidate code is NEVER executed inside the main process.
"""

import ast
import json
import sys
import subprocess
from typing import Dict, Any, List, Optional


class CodeEvaluator:
    """
    Evaluates candidate Python code safely via AST parsing and isolated subprocesses.
    """

    UNSAFE_AST_NAMES = {
        "eval", "exec", "compile", "open", "__import__"
    }
    UNSAFE_MODULES = {
        "os", "sys", "subprocess", "socket", "shutil", "pathlib",
        "requests", "urllib", "threading", "multiprocessing", "pty",
        "ctypes", "winreg"
    }

    @classmethod
    def analyze_static(cls, code: str) -> Dict[str, Any]:
        """
        Performs static AST analysis on candidate code without executing it.
        Checks syntax, extracts constructs, and flags potentially unsafe patterns.
        """
        code = code.strip()
        if not code:
            return {
                "valid_syntax": False,
                "error": "Code submission is empty.",
                "functions": [],
                "classes": [],
                "constructs": [],
                "unsafe_flags": [],
            }

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "valid_syntax": False,
                "error": f"SyntaxError at line {e.lineno}, column {e.offset}: {e.msg}",
                "functions": [],
                "classes": [],
                "constructs": [],
                "unsafe_flags": [],
            }

        functions = []
        classes = []
        constructs = set()
        unsafe_flags = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
                constructs.add("async_function")
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.ListComp):
                constructs.add("list_comprehension")
            elif isinstance(node, ast.DictComp):
                constructs.add("dict_comprehension")
            elif isinstance(node, ast.SetComp):
                constructs.add("set_comprehension")
            elif isinstance(node, ast.GeneratorExp):
                constructs.add("generator_expression")
            elif isinstance(node, ast.Yield) or isinstance(node, ast.YieldFrom):
                constructs.add("yield")
            elif isinstance(node, ast.Try):
                constructs.add("try_except")
            elif isinstance(node, ast.With):
                constructs.add("context_manager")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in cls.UNSAFE_MODULES:
                        unsafe_flags.append(f"Import of restricted module '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in cls.UNSAFE_MODULES:
                    unsafe_flags.append(f"Import from restricted module '{node.module}'")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.UNSAFE_AST_NAMES:
                    unsafe_flags.append(f"Call to restricted built-in '{node.func.id}'")

        return {
            "valid_syntax": True,
            "error": None,
            "functions": functions,
            "classes": classes,
            "constructs": sorted(list(constructs)),
            "unsafe_flags": unsafe_flags,
        }

    @classmethod
    def run_isolated_snippet(cls, snippet: str, timeout_seconds: float = 2.0) -> Optional[str]:
        """
        Safely executes a Python code snippet in an isolated child subprocess
        and returns its stdout. Returns None on errors or timeouts.
        """
        analysis = cls.analyze_static(snippet)
        if not analysis["valid_syntax"] or analysis["unsafe_flags"]:
            return None
        try:
            completed = subprocess.run(
                [sys.executable, "-c", snippet],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            if completed.returncode == 0:
                return completed.stdout
            return None
        except Exception:
            return None

    @classmethod
    def evaluate_code(
        cls,
        candidate_code: str,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        function_name: Optional[str] = None,
        timeout_seconds: float = 2.5,
    ) -> Dict[str, Any]:
        """
        Safely evaluates candidate code.
        If test cases exist and code is statically safe, runs isolated subprocess with strict timeouts.
        Returns a detailed execution and static analysis report.
        """
        static_analysis = cls.analyze_static(candidate_code)

        if not static_analysis["valid_syntax"]:
            return {
                "executed": False,
                "syntax_valid": False,
                "syntax_error": static_analysis["error"],
                "tests_passed": 0,
                "tests_total": len(test_cases) if test_cases else 0,
                "test_results": [],
                "static_analysis": static_analysis,
                "execution_error": None,
                "mode": "static_analysis_only",
                "notes": "Code has syntax errors. Subprocess execution skipped.",
            }

        # If unsafe flags detected, avoid subprocess execution for security
        if static_analysis["unsafe_flags"]:
            return {
                "executed": False,
                "syntax_valid": True,
                "syntax_error": None,
                "tests_passed": 0,
                "tests_total": len(test_cases) if test_cases else 0,
                "test_results": [],
                "static_analysis": static_analysis,
                "execution_error": "Execution aborted due to safety constraints: " + "; ".join(static_analysis["unsafe_flags"]),
                "mode": "static_analysis_only",
                "notes": "Potentially unsafe system operations were flagged. Evaluated via static review only.",
            }

        # If no test cases provided, return static analysis summary
        if not test_cases:
            return {
                "executed": False,
                "syntax_valid": True,
                "syntax_error": None,
                "tests_passed": 0,
                "tests_total": 0,
                "test_results": [],
                "static_analysis": static_analysis,
                "execution_error": None,
                "mode": "static_analysis_only",
                "notes": "Syntax is valid. Evaluated via semantic rubric analysis.",
            }

        # If function name not given, try to detect first defined function
        target_fn = function_name
        if not target_fn and static_analysis["functions"]:
            target_fn = static_analysis["functions"][0]

        # Prepare isolated runner script
        runner_script = cls._build_isolated_runner_script(
            candidate_code=candidate_code,
            target_fn=target_fn,
            test_cases=test_cases,
        )

        try:
            completed = subprocess.run(
                [sys.executable, "-c", runner_script],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )

            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()

            if completed.returncode != 0 and not stdout:
                return {
                    "executed": True,
                    "syntax_valid": True,
                    "syntax_error": None,
                    "tests_passed": 0,
                    "tests_total": len(test_cases),
                    "test_results": [],
                    "static_analysis": static_analysis,
                    "execution_error": stderr or f"Process exited with code {completed.returncode}",
                    "mode": "isolated_subprocess",
                    "notes": "Runtime error during execution of candidate code.",
                }

            try:
                # Find JSON payload in output
                result_json = json.loads(stdout)
                return {
                    "executed": True,
                    "syntax_valid": True,
                    "syntax_error": None,
                    "tests_passed": result_json.get("passed", 0),
                    "tests_total": result_json.get("total", len(test_cases)),
                    "test_results": result_json.get("details", []),
                    "static_analysis": static_analysis,
                    "execution_error": None,
                    "mode": "isolated_subprocess",
                    "notes": f"Executed in isolated subprocess. {result_json.get('passed', 0)}/{result_json.get('total', 0)} tests passed.",
                }
            except json.JSONDecodeError:
                return {
                    "executed": True,
                    "syntax_valid": True,
                    "syntax_error": None,
                    "tests_passed": 0,
                    "tests_total": len(test_cases),
                    "test_results": [],
                    "static_analysis": static_analysis,
                    "execution_error": f"Failed to parse test runner output. Output was: {stdout} Stderr: {stderr}",
                    "mode": "isolated_subprocess",
                    "notes": "Test runner output was malformed.",
                }

        except subprocess.TimeoutExpired:
            return {
                "executed": True,
                "syntax_valid": True,
                "syntax_error": None,
                "tests_passed": 0,
                "tests_total": len(test_cases),
                "test_results": [],
                "static_analysis": static_analysis,
                "execution_error": f"Execution timed out after {timeout_seconds}s (possible infinite loop or blocking call).",
                "mode": "isolated_subprocess",
                "notes": "Execution exceeded timeout limit.",
            }
        except Exception as ex:
            return {
                "executed": False,
                "syntax_valid": True,
                "syntax_error": None,
                "tests_passed": 0,
                "tests_total": len(test_cases),
                "test_results": [],
                "static_analysis": static_analysis,
                "execution_error": f"Subprocess initialization error: {str(ex)}",
                "mode": "static_analysis_only",
                "notes": "Fallback to static analysis due to runner failure.",
            }

    @classmethod
    def _build_isolated_runner_script(
        cls, candidate_code: str, target_fn: Optional[str], test_cases: List[Dict[str, Any]]
    ) -> str:
        """
        Builds a self-contained Python script to execute tests in an isolated child process.
        """
        escaped_tests = json.dumps(test_cases)
        return f"""
import json
import sys

candidate_code = {repr(candidate_code)}
test_cases = json.loads({repr(escaped_tests)})
target_fn_name = {repr(target_fn)}

results = []
passed_count = 0

local_ns = {{}}
try:
    exec(candidate_code, local_ns)
except Exception as e:
    print(json.dumps({{
        "passed": 0,
        "total": len(test_cases),
        "details": [],
        "fatal_error": f"Runtime error defining code: {{type(e).__name__}}: {{e}}"
    }}))
    sys.exit(0)

fn = local_ns.get(target_fn_name)
if not callable(fn):
    print(json.dumps({{
        "passed": 0,
        "total": len(test_cases),
        "details": [],
        "fatal_error": f"Function '{{target_fn_name}}' not found or not callable in candidate submission."
    }}))
    sys.exit(0)

for idx, tc in enumerate(test_cases):
    inp = tc.get("input")
    expected = tc.get("expected")
    try:
        if isinstance(inp, dict):
            actual = fn(**inp)
        elif isinstance(inp, list) and not tc.get("is_single_list_arg", False):
            actual = fn(*inp)
        else:
            actual = fn(inp)
            
        is_pass = (actual == expected)
        if is_pass:
            passed_count += 1
            
        results.append({{
            "case": idx + 1,
            "input": repr(inp),
            "expected": repr(expected),
            "actual": repr(actual),
            "passed": is_pass,
            "error": None
        }})
    except Exception as exc:
        results.append({{
            "case": idx + 1,
            "input": repr(inp),
            "expected": repr(expected),
            "actual": None,
            "passed": False,
            "error": f"{{type(exc).__name__}}: {{exc}}"
        }})

print(json.dumps({{
    "passed": passed_count,
    "total": len(test_cases),
    "details": results
}}))
"""
