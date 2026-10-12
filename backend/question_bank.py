"""
Comprehensive Python Question Bank for Adaptive Interview Intelligence.
Includes Level 1 (Beginner), Level 2 (Intermediate), and Level 3 (Advanced)
covering all required topics, question types, scoring rubrics, expected concepts,
and common misconceptions.
"""

from typing import List, Optional, Dict
from backend.models import (
    Question,
    DifficultyLevel,
    QuestionType,
    RubricCriterion,
)

# Standard default marks per question: 5.0
DEFAULT_QUESTION_MARKS = 5.0

QUESTION_BANK: List[Question] = [
    # =========================================================================
    # LEVEL 1 — BEGINNER QUESTIONS
    # =========================================================================
    Question(
        id="py-beg-001",
        topic="Data Structures & Mutability",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CONCEPTUAL,
        text=(
            "What is the core difference between a list and a tuple in Python? "
            "Explain when you would choose a tuple over a list in a real-world scenario."
        ),
        expected_concepts=[
            "Lists are mutable while tuples are immutable",
            "Lists use square brackets [] and tuples use parentheses ()",
            "Tuples are used for fixed collections, dictionary keys, or data integrity protection",
            "Tuples offer slight performance and memory benefits over lists",
        ],
        optional_concepts=[
            "Hashability requirement for dict keys and set elements",
            "Tuples cannot have elements added, removed, or reassigned in-place",
        ],
        common_misconceptions=[
            "Claiming tuples are always faster by an order of magnitude or have different algorithms",
            "Claiming tuples can never contain mutable elements (e.g., a tuple holding a list)",
            "Claiming tuples can be modified using list methods like append()",
        ],
        rubric=[
            RubricCriterion(
                id="mutability_distinction",
                description="Clearly explains the mutability difference between lists and tuples",
                max_marks=2.5,
                evidence_guide="Full marks for explicitly stating lists are mutable and tuples are immutable.",
            ),
            RubricCriterion(
                id="practical_use_case",
                description="Provides a valid scenario where a tuple is preferred (e.g., coordinates, dictionary keys, constant records)",
                max_marks=1.5,
                evidence_guide="Full marks for a concrete use case demonstrating need for immutability or hashability.",
            ),
            RubricCriterion(
                id="technical_depth",
                description="Mentions syntax, performance/memory, or hashability nuances accurately",
                max_marks=1.0,
                evidence_guide="Awarded if candidate mentions hashability, syntax, or memory overhead accurately.",
            ),
        ],
        reference_answer=(
            "Lists in Python are mutable, meaning their elements can be added, removed, or modified in-place after creation. "
            "Tuples are immutable; once created, their element references cannot be reassigned. "
            "Tuples are preferred when data should not be changed (such as geographical coordinates or database records), "
            "when storing heterogeneous records, or when a sequence must serve as a dictionary key or set member (since tuples "
            "of hashable items are hashable). Tuples also have slightly lower memory overhead."
        ),
    ),

    Question(
        id="py-beg-002",
        topic="Control Flow & Loops",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_OUTPUT,
        text="What will be printed when the following Python code executes? Explain step-by-step why.",
        code_snippet=(
            "for i in range(1, 6):\n"
            "    if i == 3:\n"
            "        continue\n"
            "    if i == 5:\n"
            "        break\n"
            "    print(i, end=' ')\n"
            "else:\n"
            "    print('Done')\n"
        ),
        expected_concepts=[
            "Output is '1 2 4 ' (no 'Done' printed)",
            "range(1, 6) produces numbers 1, 2, 3, 4, 5",
            "continue skips printing when i == 3 and moves to next iteration",
            "break terminates the loop when i == 5",
            "The for...else block executes only if the loop terminates normally without encountering break",
        ],
        optional_concepts=[
            "The end=' ' parameter suppresses the newline and prints spaces between items",
        ],
        common_misconceptions=[
            "Thinking 'Done' will print because the loop finished iterating up to 5",
            "Thinking 3 is printed",
            "Thinking continue terminates the loop completely",
        ],
        rubric=[
            RubricCriterion(
                id="correct_output",
                description="Correctly states the output as '1 2 4 ' without 'Done'",
                max_marks=2.5,
                evidence_guide="Full marks if the exact printed sequence 1 2 4 is stated.",
            ),
            RubricCriterion(
                id="continue_and_break_logic",
                description="Explains how continue skips 3 and break stops at 5",
                max_marks=1.5,
                evidence_guide="Awarded for clear explanation of skip on 3 and termination at 5.",
            ),
            RubricCriterion(
                id="for_else_behavior",
                description="Explains why the else clause does not execute (because of the break)",
                max_marks=1.0,
                evidence_guide="Full marks for explaining that loop else only runs if no break occurred.",
            ),
        ],
        reference_answer=(
            "The output is: '1 2 4 '\n"
            "Explanation: The loop iterates over 1, 2, 3, 4, 5. For 1 and 2, print outputs them. "
            "When i is 3, 'continue' skips the print statement. When i is 4, it prints 4. "
            "When i is 5, 'break' immediately terminates the loop. Because the loop exited via 'break', "
            "the 'else' block does not execute, so 'Done' is not printed."
        ),
    ),

    Question(
        id="py-beg-003",
        topic="Functions & Default Arguments",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.DEBUGGING,
        text=(
            "A developer wrote the following function to append an item to a shopping cart, but unexpected behavior occurs "
            "when calling it multiple times without passing a cart. What is the bug, why does it happen, and how do you fix it?"
        ),
        code_snippet=(
            "def add_item(item, cart=[]):\n"
            "    cart.append(item)\n"
            "    return cart\n"
        ),
        expected_concepts=[
            "Default parameter `cart=[]` is evaluated once when the function is defined, not per call",
            "The default list is mutable and shared across all subsequent invocations that omit the argument",
            "Fix: Use `cart=None` as the default value",
            "Inside the function, check `if cart is None: cart = []`",
        ],
        optional_concepts=[
            "Functions in Python are first-class objects; default parameter values are stored in `add_item.__defaults__`",
        ],
        common_misconceptions=[
            "Claiming Python re-initializes the default list to empty every time the function is called",
            "Claiming lists cannot be used as function arguments",
            "Suggesting changing cart to a tuple inside the signature without solving the accumulation",
        ],
        rubric=[
            RubricCriterion(
                id="identify_bug_cause",
                description="Identifies that mutable default arguments are evaluated once at definition time and shared",
                max_marks=2.5,
                evidence_guide="Full marks for explaining that default arguments are bound once at function definition.",
            ),
            RubricCriterion(
                id="provide_idiomatic_fix",
                description="Provides the standard idiom: default to None and initialize new list inside the body",
                max_marks=2.0,
                evidence_guide="Full marks for code/explanation with cart=None and `if cart is None: cart = []`.",
            ),
            RubricCriterion(
                id="code_clarity",
                description="Clear explanation of the consequence (state leaking between calls)",
                max_marks=0.5,
                evidence_guide="Awarded for describing the accumulating list behavior across function calls.",
            ),
        ],
        reference_answer=(
            "The bug is the mutable default argument `cart=[]`. In Python, default parameter expressions are evaluated once "
            "when the function is defined, not every time it is invoked. Since lists are mutable, all calls that rely on the "
            "default share the exact same list in memory, causing items from earlier calls to persist.\n"
            "The standard fix is:\n"
            "def add_item(item, cart=None):\n"
            "    if cart is None:\n"
            "        cart = []\n"
            "    cart.append(item)\n"
            "    return cart"
        ),
    ),

    Question(
        id="py-beg-004",
        topic="Strings & Operations",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_WRITING,
        text=(
            "Write a Python function `is_palindrome(text: str) -> bool` that returns True if the given string is a palindrome "
            "and False otherwise. It should be case-insensitive and ignore spaces and punctuation."
        ),
        expected_concepts=[
            "Normalizing text: lowercase conversion and stripping non-alphanumeric characters",
            "Comparing the filtered string with its reverse (e.g., filtered == filtered[::-1] or two-pointer approach)",
            "Handling empty string or single-character string as True",
        ],
        optional_concepts=[
            "str.isalnum() to filter characters",
            "Memory efficiency of two-pointer versus string slicing",
        ],
        common_misconceptions=[
            "Forgetting case sensitivity or ignoring spaces/punctuation",
            "Modifying strings in-place (strings are immutable)",
        ],
        rubric=[
            RubricCriterion(
                id="normalization",
                description="Correctly converts text to lowercase and strips non-alphanumeric characters",
                max_marks=2.0,
                evidence_guide="Full marks for using isalnum() or regex and lower() to normalize the input.",
            ),
            RubricCriterion(
                id="reversal_comparison",
                description="Correctly tests whether the normalized sequence equals its reverse",
                max_marks=2.0,
                evidence_guide="Full marks for slicing [::-1] or two-pointer comparison.",
            ),
            RubricCriterion(
                id="edge_case_handling",
                description="Handles edge cases cleanly: empty strings, single characters, strings with only spaces/punctuation",
                max_marks=1.0,
                evidence_guide="Full marks for returning True on empty or single-character strings.",
            ),
        ],
        reference_answer=(
            "def is_palindrome(text: str) -> bool:\n"
            "    cleaned = ''.join(ch.lower() for ch in text if ch.isalnum())\n"
            "    return cleaned == cleaned[::-1]\n"
        ),
        test_cases=[
            {"input": "Racecar", "expected": True},
            {"input": "A man, a plan, a canal: Panama!", "expected": True},
            {"input": "hello world", "expected": False},
            {"input": "", "expected": True},
            {"input": "   ", "expected": True},
        ],
    ),

    Question(
        id="py-beg-005",
        topic="Exception Handling",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.PRACTICAL,
        text=(
            "Explain the difference between `except Exception as e:` and a bare `except:`. "
            "Why is using a bare `except:` generally considered an anti-pattern in Python production code?"
        ),
        expected_concepts=[
            "A bare `except:` catches all exceptions inheriting from BaseException, including KeyboardInterrupt, SystemExit, and GeneratorExit",
            "`except Exception:` catches exceptions inheriting from Exception, leaving system-exiting signals unblocked",
            "Catching KeyboardInterrupt prevents the user or orchestration from gracefully terminating the script via Ctrl+C",
            "A bare except masks unexpected bugs and makes debugging difficult",
        ],
        optional_concepts=[
            "Python exception hierarchy: BaseException -> Exception",
            "Best practice is to catch the most specific exception type possible (e.g. ValueError, KeyError)",
        ],
        common_misconceptions=[
            "Believing `except Exception:` catches Ctrl+C",
            "Believing there is no difference between the two",
        ],
        rubric=[
            RubricCriterion(
                id="hierarchy_distinction",
                description="Explains that bare except catches BaseException while except Exception catches standard program exceptions",
                max_marks=2.5,
                evidence_guide="Full marks for mentioning BaseException vs Exception or specific system exceptions.",
            ),
            RubricCriterion(
                id="system_signals_consequence",
                description="Explains the impact on KeyboardInterrupt or SystemExit (preventing clean shutdown)",
                max_marks=1.5,
                evidence_guide="Full marks for identifying that Ctrl+C / KeyboardInterrupt or SystemExit get accidentally intercepted.",
            ),
            RubricCriterion(
                id="best_practice",
                description="Advocates for specific exception handling and avoids masking bugs",
                max_marks=1.0,
                evidence_guide="Full marks for stating specific exceptions should be caught.",
            ),
        ],
        reference_answer=(
            "In Python's exception hierarchy, `BaseException` is the root class. `Exception` inherits from `BaseException`, "
            "while system-exiting exceptions like `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` inherit directly from "
            "`BaseException`.\n"
            "A bare `except:` catches EVERYTHING, including `KeyboardInterrupt` and `SystemExit`. This makes it impossible for "
            "users to interrupt the program via Ctrl+C and can prevent normal application termination.\n"
            "`except Exception as e:` only catches standard application errors, allowing interrupt signals through. "
            "A bare `except:` is an anti-pattern because it masks syntax or name errors and impedes diagnostics."
        ),
    ),

    # =========================================================================
    # LEVEL 2 — INTERMEDIATE QUESTIONS
    # =========================================================================
    Question(
        id="py-int-001",
        topic="Function Arguments & Packing",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text=(
            "Explain how `*args` and `**kwargs` work in Python function definitions and function calls. "
            "In what order must parameters appear in a function signature?"
        ),
        expected_concepts=[
            "`*args` collects arbitrary positional arguments into a tuple",
            "`**kwargs` collects arbitrary keyword arguments into a dictionary",
            "Unpacking: `*` unpacks an iterable into positional arguments; `**` unpacks a mapping into keyword arguments",
            "Signature order: positional/standard args, default args, *args, keyword-only args, **kwargs",
        ],
        optional_concepts=[
            "Keyword-only arguments using `*` without args (e.g., `def f(a, *, b=1):`)",
            "Positional-only parameters using `/` (Python 3.8+)",
        ],
        common_misconceptions=[
            "Thinking the variable names must literally be named 'args' and 'kwargs' (the asterisk is what matters)",
            "Thinking `*args` creates a list rather than a tuple",
            "Placing `**kwargs` before `*args` in the parameter list",
        ],
        rubric=[
            RubricCriterion(
                id="args_kwargs_definition",
                description="Accurately defines *args as packing into a tuple and **kwargs into a dictionary",
                max_marks=2.0,
                evidence_guide="Full marks for tuple (args) and dict (kwargs) packing explanation.",
            ),
            RubricCriterion(
                id="signature_ordering",
                description="Correctly outlines parameter ordering rules in Python functions",
                max_marks=2.0,
                evidence_guide="Full marks for correct ordering (positional -> default/*args -> keyword-only -> **kwargs).",
            ),
            RubricCriterion(
                id="call_site_unpacking",
                description="Explains or mentions unpacking behavior when calling functions (*iterable, **dict)",
                max_marks=1.0,
                evidence_guide="Full marks for distinguishing parameter packing from call-site argument unpacking.",
            ),
        ],
        reference_answer=(
            "`*args` allows a function to accept any number of additional positional arguments, packed into a tuple.\n"
            "`**kwargs` allows a function to accept any number of additional keyword arguments, packed into a dictionary.\n"
            "At call sites, `*` and `**` perform unpacking of iterables and dictionaries respectively.\n"
            "Parameter ordering in function signatures must be:\n"
            "1. Positional-only parameters (before `/`)\n"
            "2. Standard positional-or-keyword parameters\n"
            "3. Default value parameters\n"
            "4. `*args` (variable positional)\n"
            "5. Keyword-only parameters (parameters after `*` or `*args`)\n"
            "6. `**kwargs` (variable keyword arguments must be last)"
        ),
    ),

    Question(
        id="py-int-002",
        topic="Generators & Lazy Evaluation",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.PRACTICAL,
        text=(
            "What is a generator in Python, how does the `yield` keyword work, and what advantages do generators offer "
            "over returning a complete list when processing large files or data streams?"
        ),
        expected_concepts=[
            "A generator function contains `yield` and returns a generator iterator object",
            "`yield` pauses function execution, saves its local state/frame, and produces a value to the caller",
            "Resumption occurs via `next()` from where it left off until StopIteration is raised",
            "Memory efficiency: generates items one at a time (O(1) memory) rather than loading entire dataset into memory",
            "Lazy evaluation: pipeline processing without upfront computation",
        ],
        optional_concepts=[
            "Generator methods: `.send()`, `.throw()`, `.close()`",
            "Generator expressions `(x for x in iterable)`",
        ],
        common_misconceptions=[
            "Thinking `yield` terminates the function like `return` and destroys local variables",
            "Thinking generators are always faster in raw CPU time than list comprehensions",
            "Believing you can index or slice a generator directly like `gen[0]`",
        ],
        rubric=[
            RubricCriterion(
                id="yield_mechanics",
                description="Explains how yield suspends execution and preserves local state",
                max_marks=2.0,
                evidence_guide="Full marks for explaining suspension, state preservation, and resumption with next().",
            ),
            RubricCriterion(
                id="memory_advantages",
                description="Highlights constant memory usage O(1) and avoidance of loading entire datasets into RAM",
                max_marks=2.0,
                evidence_guide="Full marks for contrasting memory footprint of lists vs stream processing of generators.",
            ),
            RubricCriterion(
                id="practical_scenario",
                description="Mentions file processing, streaming pipelines, or infinite sequences",
                max_marks=1.0,
                evidence_guide="Awarded for a realistic large file or streaming pipeline use case.",
            ),
        ],
        reference_answer=(
            "A generator is an iterator created by a function that uses `yield` instead of or in addition to `return`. "
            "When `yield` is encountered, the function yields a value, pauses its execution, and saves its execution frame "
            "and local variables. When `next()` is called again, execution resumes immediately after the `yield` statement.\n"
            "Advantages over lists:\n"
            "1. Memory efficiency: Generates values on-demand, requiring O(1) memory instead of O(N) memory needed to store an entire list in RAM.\n"
            "2. Latency / immediate start: Processing begins immediately without waiting for the entire dataset to be loaded or computed.\n"
            "3. Ideal for large log files, infinite streams, and data transformation pipelines."
        ),
    ),

    Question(
        id="py-int-003",
        topic="Object-Oriented Programming",
        competency="Object-Oriented Programming",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text=(
            "In Python OOP, what are the distinct roles of `@classmethod` and `@staticmethod` compared to regular instance methods? "
            "Provide a concrete scenario illustrating when `@classmethod` is the right choice."
        ),
        expected_concepts=[
            "Instance methods receive `self` (the instance) as the first argument and can inspect/modify instance state",
            "`@classmethod` receives `cls` (the class object) as the first argument and can modify class-level state or instantiate objects",
            "`@staticmethod` receives neither `self` nor `cls`; behaves like a plain function scoped inside the class namespace",
            "Primary use case for `@classmethod`: Alternative constructors (e.g. `from_dict`, `from_csv`, `from_json`)",
        ],
        optional_concepts=[
            "Inheritance behavior: `@classmethod` respects subclasses because `cls` refers to the derived class when called on it",
        ],
        common_misconceptions=[
            "Thinking `@staticmethod` receives the class object",
            "Thinking `@classmethod` and `@staticmethod` are completely interchangeable",
            "Thinking instance methods cannot access class attributes",
        ],
        rubric=[
            RubricCriterion(
                id="method_types_distinction",
                description="Clearly explains self vs cls vs neither for instance, class, and static methods",
                max_marks=2.5,
                evidence_guide="Full marks for contrasting self (instance), cls (class), and no automatic bound argument.",
            ),
            RubricCriterion(
                id="classmethod_use_case",
                description="Identifies alternative constructors (factory methods) as the canonical use case for @classmethod",
                max_marks=1.5,
                evidence_guide="Full marks for citing factory methods like from_json, from_dict, or subclass-aware instantiation.",
            ),
            RubricCriterion(
                id="staticmethod_purpose",
                description="Explains when @staticmethod is appropriate (utility function logically belonging to class namespace)",
                max_marks=1.0,
                evidence_guide="Full marks for explaining staticmethod as an encapsulated utility function.",
            ),
        ],
        reference_answer=(
            "1. Instance methods: Automatically receive `self` as the first argument, allowing access and mutation of instance attributes and class attributes.\n"
            "2. `@classmethod`: Decorated with `@classmethod`, receives the class `cls` as its first parameter instead of `self`. "
            "It can access and modify class state and works cleanly with inheritance.\n"
            "Canonical use case: Alternative constructors (factory methods), e.g. `Person.from_birth_year(cls, name, year)` or `Config.from_json(cls, filepath)`.\n"
            "3. `@staticmethod`: Decorated with `@staticmethod`, receives neither `self` nor `cls`. It is a self-contained utility function "
            "placed inside the class namespace for logical grouping and readability."
        ),
    ),

    Question(
        id="py-int-004",
        topic="Identity, Equality & Copying",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CODE_OUTPUT,
        text="Analyze the following code. What will each print statement output? Explain the difference between `==` and `is`, as well as shallow vs deep copy.",
        code_snippet=(
            "import copy\n"
            "a = [1, [2, 3]]\n"
            "b = a\n"
            "c = a.copy()\n"
            "d = copy.deepcopy(a)\n"
            "a[1].append(4)\n"
            "print(a == b, a is b)\n"
            "print(a == c, a is c)\n"
            "print(c[1])\n"
            "print(d[1])\n"
        ),
        expected_concepts=[
            "`a == b` is True and `a is b` is True (b is a reference alias to a)",
            "`a == c` is True and `a is c` is False (c is a new list object, but elements are shallow-copied)",
            "`c[1]` outputs `[2, 3, 4]` because the nested list reference was shared in the shallow copy",
            "`d[1]` outputs `[2, 3]` because `deepcopy` recursively cloned nested objects",
            "`==` checks value equality (`__eq__`) while `is` checks object identity / memory address (`id()`)",
        ],
        optional_concepts=[
            "`copy.copy` vs `copy.deepcopy` mechanisms",
        ],
        common_misconceptions=[
            "Thinking `c.copy()` makes a deep copy of nested lists",
            "Thinking `==` checks whether variables point to the same memory address",
            "Thinking `d[1]` also has 4 appended",
        ],
        rubric=[
            RubricCriterion(
                id="equality_vs_identity",
                description="Explains difference between == (value comparison) and is (object identity)",
                max_marks=1.5,
                evidence_guide="Full marks for defining value equality vs identity (id/memory address).",
            ),
            RubricCriterion(
                id="shallow_copy_behavior",
                description="Explains why c[1] contains [2, 3, 4] due to shared references in shallow copy",
                max_marks=1.5,
                evidence_guide="Full marks for explaining that shallow copy clones only outer container.",
            ),
            RubricCriterion(
                id="deepcopy_behavior",
                description="Explains why d[1] remains [2, 3] due to recursive cloning in deepcopy",
                max_marks=1.0,
                evidence_guide="Full marks for explaining recursive object copying in deepcopy.",
            ),
            RubricCriterion(
                id="correct_printed_outputs",
                description="Accurately predicts the output of all print statements",
                max_marks=1.0,
                evidence_guide="Full marks for correctly predicting all four lines of output.",
            ),
        ],
        reference_answer=(
            "Outputs:\n"
            "True True\n"
            "True False\n"
            "[2, 3, 4]\n"
            "[2, 3]\n\n"
            "Explanation:\n"
            "- `b = a` creates an alias to the same object: `a is b` and `a == b` are both True.\n"
            "- `c = a.copy()` creates a shallow copy. The outer list is a new object (`a is c` is False), but the nested list `[2, 3]` is shared by reference. "
            "Modifying `a[1]` modifies `c[1]`, resulting in `[2, 3, 4]`. `a == c` is True because both have identical elements `[1, [2, 3, 4]]`.\n"
            "- `d = copy.deepcopy(a)` recursively clones all nested objects. Modifications to `a[1]` do not affect `d[1]`, so `d[1]` remains `[2, 3]`.\n"
            "- `==` checks value equality via `__eq__`, whereas `is` checks memory identity (`id(x) == id(y)`)."
        ),
    ),

    Question(
        id="py-int-005",
        topic="File Handling & Context Managers",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CODE_WRITING,
        text=(
            "Write a function `count_word_frequency(filepath: str, min_length: int = 3) -> dict[str, int]` that reads a text file, "
            "handles file not found errors gracefully (returning an empty dict), and returns a dictionary mapping words to their occurrence counts. "
            "Words should be lowercased, stripped of punctuation, and must meet `min_length`. Use context managers."
        ),
        expected_concepts=[
            "Using `with open(filepath, 'r', encoding='utf-8') as f:` context manager for safe file closure",
            "Handling `FileNotFoundError` using try...except",
            "Normalizing words: `.lower()`, removing punctuation (e.g. `re.findall` or `str.strip`)",
            "Counting occurrences using `collections.Counter` or a standard dictionary",
            "Filtering words with `len(word) >= min_length`",
        ],
        optional_concepts=[
            "Reading line-by-line for memory efficiency",
            "Explicit encoding specification (`encoding='utf-8'`)",
        ],
        common_misconceptions=[
            "Forgetting to handle FileNotFoundError and letting it crash",
            "Not using a `with` statement to guarantee file descriptor cleanup",
            "Not handling punctuation attached to words (like 'end.')",
        ],
        rubric=[
            RubricCriterion(
                id="file_handling_context_manager",
                description="Uses `with open(...)` context manager and handles FileNotFoundError gracefully",
                max_marks=2.0,
                evidence_guide="Full marks for context manager with try-except FileNotFoundError returning empty dict.",
            ),
            RubricCriterion(
                id="word_normalization_and_filtering",
                description="Correctly strips punctuation, lowercases words, and applies min_length filter",
                max_marks=2.0,
                evidence_guide="Full marks for regex or strip cleaning + min_length validation.",
            ),
            RubricCriterion(
                id="frequency_counting",
                description="Correctly counts word frequencies (dict or Counter) and returns the dictionary",
                max_marks=1.0,
                evidence_guide="Full marks for accurate count accumulation and correct return type.",
            ),
        ],
        reference_answer=(
            "import re\n"
            "from collections import Counter\n\n"
            "def count_word_frequency(filepath: str, min_length: int = 3) -> dict[str, int]:\n"
            "    counts = Counter()\n"
            "    try:\n"
            "        with open(filepath, 'r', encoding='utf-8') as f:\n"
            "            for line in f:\n"
            "                words = re.findall(r'\\b[a-zA-Z0-9]+\\b', line.lower())\n"
            "                counts.update(w for w in words if len(w) >= min_length)\n"
            "        return dict(counts)\n"
            "    except FileNotFoundError:\n"
            "        return {}\n"
        ),
    ),

    # =========================================================================
    # LEVEL 3 — ADVANCED QUESTIONS
    # =========================================================================
    Question(
        id="py-adv-001",
        topic="Decorators & Closures",
        competency="Advanced Python Concepts",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.CODE_WRITING,
        text=(
            "Write a custom decorator `@retry(max_attempts=3, delay=1.0, exceptions=(Exception,))` that retries the decorated "
            "function if one of the specified exceptions is raised, waiting `delay` seconds between attempts. "
            "If all attempts fail, it must re-raise the last exception. Preserve the original function's metadata."
        ),
        expected_concepts=[
            "Decorator factory taking configuration arguments (`max_attempts`, `delay`, `exceptions`)",
            "Inner decorator and inner wrapper function taking `*args, **kwargs`",
            "`functools.wraps` to preserve `__name__`, `__doc__`, and function signatures",
            "Looping up to `max_attempts`, using `time.sleep(delay)`, catching specified exception tuple",
            "Re-raising the final exception when attempts are exhausted",
        ],
        optional_concepts=[
            "Exponential backoff or jitter support",
            "Distinguishing retryable exceptions from non-retryable exceptions",
        ],
        common_misconceptions=[
            "Forgetting `@functools.wraps(fn)`, which obscures function metadata and breaks introspection",
            "Writing a 2-level decorator instead of a 3-level decorator factory when taking decorator parameters",
            "Catching all exceptions instead of the parameterized `exceptions` tuple",
            "Swallowing the exception silently without re-raising after exhausting attempts",
        ],
        rubric=[
            RubricCriterion(
                id="decorator_factory_structure",
                description="Proper 3-layer structure for parameterized decorator factory taking args",
                max_marks=1.5,
                evidence_guide="Full marks for decorator factory -> decorator -> wrapper structure.",
            ),
            RubricCriterion(
                id="functools_wraps",
                description="Preserves function metadata using @functools.wraps(func)",
                max_marks=1.0,
                evidence_guide="Full marks for importing and applying functools.wraps.",
            ),
            RubricCriterion(
                id="retry_logic_and_reraise",
                description="Retries specified exceptions up to max_attempts, applies delay, and re-raises on final failure",
                max_marks=2.0,
                evidence_guide="Full marks for correct loop, exception catching, time.sleep, and re-raising.",
            ),
            RubricCriterion(
                id="signature_flexibility",
                description="Wrapper accepts (*args, **kwargs) and returns the decorated function's return value",
                max_marks=0.5,
                evidence_guide="Full marks for passing args/kwargs and returning result.",
            ),
        ],
        reference_answer=(
            "import time\n"
            "from functools import wraps\n\n"
            "def retry(max_attempts=3, delay=1.0, exceptions=(Exception,)):\n"
            "    def decorator(func):\n"
            "        @wraps(func)\n"
            "        def wrapper(*args, **kwargs):\n"
            "            last_exception = None\n"
            "            for attempt in range(1, max_attempts + 1):\n"
            "                try:\n"
            "                    return func(*args, **kwargs)\n"
            "                except exceptions as exc:\n"
            "                    last_exception = exc\n"
            "                    if attempt < max_attempts:\n"
            "                        time.sleep(delay)\n"
            "                    else:\n"
            "                        raise last_exception\n"
            "        return wrapper\n"
            "    return decorator\n"
        ),
    ),

    Question(
        id="py-adv-002",
        topic="Concurrency & GIL",
        competency="Concurrency & Asyncio",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.CONCEPTUAL,
        text=(
            "Explain Python's Global Interpreter Lock (GIL) and its practical consequences. "
            "When should you choose `multiprocessing` versus `threading` versus `asyncio` for high-throughput Python systems?"
        ),
        expected_concepts=[
            "GIL is a mutex in CPython that ensures only one native thread executes Python bytecode at any given moment",
            "CPU-bound tasks with `threading` do not achieve true parallelism in CPython due to GIL contention",
            "I/O-bound tasks release the GIL during syscalls (network, disk, sleep), so `threading` and `asyncio` work well",
            "`multiprocessing`: Bypasses the GIL by creating separate OS processes with independent memory spaces (ideal for CPU-bound tasks, e.g. data crunching, ML)",
            "`threading`: Shared memory, preemptive multitasking by OS, good for blocking I/O with legacy libraries",
            "`asyncio`: Cooperative multitasking on a single thread using an event loop; ideal for thousands of concurrent I/O-bound connections (e.g. web servers, websockets)",
        ],
        optional_concepts=[
            "Inter-process communication (IPC) overhead and memory duplication in multiprocessing",
            "Python 3.12+ / 3.13 free-threaded Python (PEP 703) developments",
        ],
        common_misconceptions=[
            "Believing Python threads are 'fake' or green threads (they are real OS threads, but serialized by the GIL)",
            "Believing asyncio uses multiple CPU cores",
            "Claiming the GIL prevents all race conditions (GIL guarantees bytecode atomicity, not compound operation thread-safety)",
        ],
        rubric=[
            RubricCriterion(
                id="gil_definition_and_mechanism",
                description="Accurately defines the GIL as CPython's bytecode execution mutex and its effect on multi-core CPU parallelism",
                max_marks=1.5,
                evidence_guide="Full marks for explaining CPython mutex serializing Python bytecode execution.",
            ),
            RubricCriterion(
                id="multiprocessing_vs_threading",
                description="Contrasts multiprocessing (separate processes, CPU-bound parallelism) with threading (shared memory, I/O-bound)",
                max_marks=1.5,
                evidence_guide="Full marks for distinguishing CPU-bound vs I/O-bound suitability and process vs thread models.",
            ),
            RubricCriterion(
                id="asyncio_event_loop",
                description="Explains asyncio's cooperative single-threaded event loop for high-concurrency non-blocking I/O",
                max_marks=1.5,
                evidence_guide="Full marks for cooperative single-threaded event-driven concurrency explanation.",
            ),
            RubricCriterion(
                id="thread_safety_nuance",
                description="Recognizes that GIL does not eliminate race conditions in user code or mentions I/O GIL release",
                max_marks=0.5,
                evidence_guide="Awarded for noting that thread synchronization (Locks) is still needed for shared state.",
            ),
        ],
        reference_answer=(
            "The Global Interpreter Lock (GIL) is a mutex in CPython that prevents multiple native threads from executing "
            "Python bytecodes simultaneously. It exists to protect CPython's internal memory management and reference counting.\n"
            "Consequences:\n"
            "- Multi-threaded CPU-bound programs run on only one CPU core at a time, often slower than single-threaded code due to lock overhead.\n"
            "- I/O-bound programs still benefit from threads because CPython releases the GIL during blocking system calls (disk, network, sleep).\n\n"
            "Architecture selection:\n"
            "1. `multiprocessing`: Separate Python processes, each with its own GIL and memory space. Use for CPU-bound computations (image processing, data science). "
            "Trade-off: IPC overhead and serialization (pickle).\n"
            "2. `threading`: OS threads sharing memory. Ideal for I/O-bound tasks when using synchronous/blocking third-party libraries.\n"
            "3. `asyncio`: Single-threaded cooperative multitasking managed by an event loop with non-blocking I/O (`async/await`). "
            "Best for ultra-high concurrency network services (10k+ concurrent connections) with low memory overhead."
        ),
    ),

    Question(
        id="py-adv-003",
        topic="Python Data Model & Descriptors",
        competency="Advanced Python Concepts",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.CODE_WRITING,
        text=(
            "Implement a reusable descriptor `PositiveNumber` that enforces that an assigned attribute value is a float or int "
            "greater than zero. It should raise `TypeError` for non-numeric types and `ValueError` if the value is <= 0. "
            "Support multiple instances of the owner class without attribute name collision."
        ),
        expected_concepts=[
            "Descriptor protocol: implementing `__get__`, `__set__`, and optionally `__set_name__`",
            "`__set_name__(self, owner, name)` captures the attribute name dynamically (Python 3.6+)",
            "Storing the value on the instance's `__dict__` or a private instance attribute (e.g., `_name`) to avoid memory leaks",
            "Validating that value is `isinstance(val, (int, float))` and `val > 0`",
            "Raising `TypeError` and `ValueError` as specified",
        ],
        optional_concepts=[
            "Handling `__get__` when called on the owner class (`if instance is None: return self`)",
            "Avoiding storing instance state in descriptor's own dictionary (avoids instance leaks or cross-instance mutation)",
        ],
        common_misconceptions=[
            "Storing the attribute value as an attribute on the descriptor itself (which shares state across all owner instances)",
            "Storing values in a dictionary keyed by instance without using WeakKeyDictionary, causing memory leaks",
            "Failing to support access via class object in `__get__`",
        ],
        rubric=[
            RubricCriterion(
                id="descriptor_protocol_implementation",
                description="Implements __set__, __get__, and ideally __set_name__ properly",
                max_marks=2.0,
                evidence_guide="Full marks for standard descriptor protocol methods.",
            ),
            RubricCriterion(
                id="type_and_value_validation",
                description="Validates numeric types (raises TypeError) and positive values (raises ValueError)",
                max_marks=1.5,
                evidence_guide="Full marks for raising TypeError on non-numeric and ValueError on non-positive.",
            ),
            RubricCriterion(
                id="instance_isolation",
                description="Stores state on instance.__dict__ or uses unique private attribute name without collision",
                max_marks=1.5,
                evidence_guide="Full marks for avoiding shared descriptor state across different owner instances.",
            ),
        ],
        reference_answer=(
            "class PositiveNumber:\n"
            "    def __set_name__(self, owner, name):\n"
            "        self.private_name = f'_{name}'\n\n"
            "    def __get__(self, instance, owner=None):\n"
            "        if instance is None:\n"
            "            return self\n"
            "        return getattr(instance, self.private_name, None)\n\n"
            "    def __set__(self, instance, value):\n"
            "        if not isinstance(value, (int, float)) or isinstance(value, bool):\n"
            "            raise TypeError(f'Expected numeric value, got {type(value).__name__}')\n"
            "        if value <= 0:\n"
            "            raise ValueError(f'Value must be positive (> 0), got {value}')\n"
            "        setattr(instance, self.private_name, value)\n"
        ),
    ),

    Question(
        id="py-adv-004",
        topic="Memory Management & Garbage Collection",
        competency="Memory & Performance",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.SCENARIO,
        text=(
            "You are profiling a long-running Python microservice and notice memory steadily increasing over days, "
            "even though data structures are supposedly dereferenced. Explain CPython's two-part memory management system "
            "(reference counting + generational garbage collection). How do cyclic references cause leaks, and how would you diagnose and resolve this?"
        ),
        expected_concepts=[
            "Reference counting is CPython's primary memory management: deallocates object immediately when refcount reaches zero",
            "Cyclic garbage collector handles reference cycles (e.g. object A references B, and B references A) using generational collection (Gen 0, 1, 2)",
            "Issues: Objects with `__del__` methods historically (pre-3.4) prevented cyclic GC from breaking cycles",
            "Global caches, class-level dictionaries, event listeners, or unclosed closures retaining references",
            "Diagnosis tools: `tracemalloc`, `objgraph`, `gc.collect()`, `gc.garbage`, `sys.getrefcount()`",
            "Fixes: `weakref` module for non-owning references, explicitly breaking cycles, managing cache sizes with LRU eviction",
        ],
        optional_concepts=[
            "PyMalloc allocator arena/pool management preventing memory return to OS immediately",
            "PEP 442 safe object finalization",
        ],
        common_misconceptions=[
            "Believing Python only uses a mark-and-sweep garbage collector and has no reference counting",
            "Believing `del variable` immediately deletes the object (it only decrements refcount and deletes the name binding)",
            "Thinking memory freed by CPython is always immediately returned to the OS",
        ],
        rubric=[
            RubricCriterion(
                id="memory_architecture_explanation",
                description="Explains reference counting as primary mechanism and generational cyclic GC as secondary mechanism",
                max_marks=2.0,
                evidence_guide="Full marks for distinguishing reference count immediacy from generational cyclic sweeps.",
            ),
            RubricCriterion(
                id="cycle_mechanics_and_retention",
                description="Explains how cycles form and how lingering references (caches, closures, listeners) prevent deallocation",
                max_marks=1.5,
                evidence_guide="Full marks for explaining cyclic self-references or unevicted caches.",
            ),
            RubricCriterion(
                id="diagnosis_and_resolution_tools",
                description="Proposes concrete diagnostics (tracemalloc, objgraph, gc) and architectural remedies (weakref, bounded caches)",
                max_marks=1.5,
                evidence_guide="Full marks for citing tracemalloc/objgraph and weakref or cache bounding.",
            ),
        ],
        reference_answer=(
            "1. Dual Memory Architecture in CPython:\n"
            "- Reference Counting: Every Python object has an `ob_refcnt`. When a reference is created it increments; when reassigned/deleted it decrements. "
            "When it hits 0, memory is immediately deallocated.\n"
            "- Generational Cyclic GC: Reference counting cannot reclaim circular references (A -> B -> A). The `gc` module runs a cyclic detector across "
            "three generations (0, 1, 2) with increasing sweep intervals based on object survival.\n\n"
            "2. Why Leaks Occur:\n"
            "- Lingering strong references: Global registries, module-level dicts, callback lists, or closures holding large objects.\n"
            "- Object pools / PyMalloc fragmentation: Memory freed internally by Python may remain in CPython arenas rather than returned to OS.\n\n"
            "3. Diagnosis & Resolution:\n"
            "- Diagnosis: Use `tracemalloc` to take memory snapshots over time and diff them; use `objgraph.show_most_common_types()` and `objgraph.show_backrefs()` to trace reference chains.\n"
            "- Resolution: Use `weakref.ref` or `weakref.WeakValueDictionary` for caches and observers; explicitly clear data structures or break circular links; enforce bounded LRU caches."
        ),
    ),

    Question(
        id="py-adv-005",
        topic="MRO & Multiple Inheritance",
        competency="Object-Oriented Programming",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.CODE_OUTPUT,
        text="What will be the output of `D().test()`? Explain the C3 Linearization algorithm and how `super()` behaves in this hierarchy.",
        code_snippet=(
            "class A:\n"
            "    def test(self):\n"
            "        print('A', end=' ')\n\n"
            "class B(A):\n"
            "    def test(self):\n"
            "        print('B', end=' ')\n"
            "        super().test()\n\n"
            "class C(A):\n"
            "    def test(self):\n"
            "        print('C', end=' ')\n"
            "        super().test()\n\n"
            "class D(B, C):\n"
            "    def test(self):\n"
            "        print('D', end=' ')\n"
            "        super().test()\n\n"
            "D().test()\n"
        ),
        expected_concepts=[
            "Output is 'D B C A '",
            "MRO for D is [D, B, C, A, object] using C3 linearization",
            "`super()` in class B does NOT call A statically; it dynamically calls the next class in D's MRO, which is C",
            "This cooperative multiple inheritance prevents diamond problem duplication and ensures each class executes in order",
        ],
        optional_concepts=[
            "Checking `D.__mro__` or `D.mro()`",
            "Rules of C3: monotonicity and local precedence order",
        ],
        common_misconceptions=[
            "Believing B's `super().test()` directly calls A because B inherits from A (ignoring dynamic MRO dispatch)",
            "Thinking output is 'D B A C A '",
            "Thinking Python uses simple depth-first search (DFS) for multiple inheritance (Python 2.3+ replaced DFS with C3)",
        ],
        rubric=[
            RubricCriterion(
                id="predict_output",
                description="Correctly predicts output sequence 'D B C A '",
                max_marks=2.0,
                evidence_guide="Full marks for specifying output as D B C A.",
            ),
            RubricCriterion(
                id="mro_order_explanation",
                description="Derives the MRO for D as D -> B -> C -> A -> object",
                max_marks=1.5,
                evidence_guide="Full marks for explicitly stating the MRO order.",
            ),
            RubricCriterion(
                id="super_dynamic_dispatch",
                description="Explains that super() in B resolves to C according to the runtime instance's MRO, not compile-time parent",
                max_marks=1.5,
                evidence_guide="Full marks for explaining that super() in B calls C, demonstrating understanding of cooperative multiple inheritance.",
            ),
        ],
        reference_answer=(
            "Output: 'D B C A '\n\n"
            "Explanation:\n"
            "1. In Python, Method Resolution Order (MRO) is computed using the C3 Linearization algorithm. "
            "For class `D(B, C)`, the MRO is: `[D, B, C, A, object]`.\n"
            "2. When `D().test()` is invoked:\n"
            "- `D.test` prints 'D' and calls `super().test()`. The next class in D's MRO is `B`.\n"
            "- `B.test` prints 'B' and calls `super().test()`. Crucially, because the active instance is an instance of `D`, "
            "`super()` in `B` does NOT jump to `A`; it looks up the next class in `D`'s MRO, which is `C`!\n"
            "- `C.test` prints 'C' and calls `super().test()`, which resolves to `A`.\n"
            "- `A.test` prints 'A' and terminates.\n"
            "This cooperative dispatch guarantees each method in the diamond hierarchy is executed exactly once in consistent order."
        ),
    ),

    # =========================================================================
    # ADDITIONAL FOLLOW-UP & PRACTICAL QUESTIONS
    # =========================================================================
    Question(
        id="py-fol-001",
        topic="Data Structures & Mutability",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.FOLLOW_UP,
        text=(
            "You previously discussed list and tuple mutability. Can a tuple ever change the values it contains? "
            "Consider: `t = (1, [2, 3])`. Can `t[1].append(4)` succeed? Why or why not?"
        ),
        expected_concepts=[
            "Yes, `t[1].append(4)` succeeds and changes the contents of `t` to `(1, [2, 3, 4])`",
            "The tuple itself is immutable in that its element bindings / references cannot be reassigned (e.g. `t[1] = ...` raises TypeError)",
            "If an element inside the tuple is a mutable object (like a list), that referenced object can be mutated in-place",
            "A tuple containing mutable elements is unhashable and cannot be used as a dict key",
        ],
        optional_concepts=[
            "Augmented assignment trap: `t[1] += [4]` raises TypeError but still mutates the list!",
        ],
        common_misconceptions=[
            "Believing tuples freeze all nested objects recursively",
            "Believing modifying the inner list raises an error",
        ],
        rubric=[
            RubricCriterion(
                id="nested_mutation_answer",
                description="Correctly states that t[1].append(4) succeeds and explains why",
                max_marks=2.5,
                evidence_guide="Full marks for confirming it succeeds and modifies the nested list.",
            ),
            RubricCriterion(
                id="reference_immutability",
                description="Explains that the tuple only fixes references to its elements, not the internal state of those elements",
                max_marks=1.5,
                evidence_guide="Full marks for distinguishing reference immutability from value immutability.",
            ),
            RubricCriterion(
                id="hashability_implication",
                description="Mentions that such a tuple is not hashable / cannot be used as a dictionary key",
                max_marks=1.0,
                evidence_guide="Awarded for noting hashability loss when holding mutable elements.",
            ),
        ],
        reference_answer=(
            "Yes, `t[1].append(4)` succeeds! The tuple becomes `(1, [2, 3, 4])`.\n"
            "Explanation: Immutability in a tuple means that its collection of references is fixed; you cannot reassign `t[0]` or `t[1]`, "
            "nor can you add or remove reference slots. However, if an object referenced by the tuple is itself mutable (such as a list), "
            "that underlying object can be mutated in-place.\n"
            "Because this tuple contains a mutable object, it is not hashable and cannot be used as a dictionary key or in a set."
        ),
        follow_up_to="py-beg-001",
    ),

    Question(
        id="py-int-006",
        topic="Comprehensions & Expressions",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.PRACTICAL,
        text=(
            "What is the difference between a list comprehension and a generator expression in terms of syntax, memory consumption, "
            "and execution timing? When is a list comprehension preferable over a generator?"
        ),
        expected_concepts=[
            "Syntax: `[x for x in data]` (list comprehension) vs `(x for x in data)` (generator expression)",
            "Memory: List comprehension allocates the entire list in memory immediately; generator expression produces items lazily on demand with O(1) memory",
            "Execution: List comp evaluates eagerly; generator evaluates lazily upon iteration",
            "When list comprehension is preferred: When you need indexing, len(), multiple passes over the data, or when total size is small and immediate access is needed",
        ],
        optional_concepts=[
            "Re-iterating a generator: Once exhausted, a generator cannot be iterated again without recreating it",
        ],
        common_misconceptions=[
            "Thinking `(x for x in data)` produces a tuple",
            "Thinking generator expressions can be indexed",
        ],
        rubric=[
            RubricCriterion(
                id="syntax_and_eval_timing",
                description="Contrasts brackets vs parentheses and eager vs lazy evaluation",
                max_marks=2.0,
                evidence_guide="Full marks for syntax distinction and eager vs lazy explanation.",
            ),
            RubricCriterion(
                id="memory_behavior",
                description="Explains O(N) full allocation vs O(1) lazy memory footprint",
                max_marks=1.5,
                evidence_guide="Full marks for memory difference explanation.",
            ),
            RubricCriterion(
                id="list_comp_use_case",
                description="Explains when list comp is better (multiple iterations, len(), slicing/indexing)",
                max_marks=1.5,
                evidence_guide="Full marks for identifying multiple passes or random access requirements.",
            ),
        ],
        reference_answer=(
            "Syntax & Type:\n"
            "- List comprehension uses square brackets `[x for x in items]` and produces a list.\n"
            "- Generator expression uses parentheses `(x for x in items)` and produces a generator object (not a tuple!).\n\n"
            "Execution & Memory:\n"
            "- List comprehension evaluates eagerly and allocates all elements in memory immediately (O(N) memory).\n"
            "- Generator expression evaluates lazily, computing values only when iterated with `next()` or in a loop (O(1) memory).\n\n"
            "When to prefer a List Comprehension:\n"
            "1. When you need to iterate over the collection multiple times (generators exhaust after one pass).\n"
            "2. When you need sequence operations like `len()`, indexing `seq[0]`, slicing, or sorting.\n"
            "3. When the data size is modest and you want fast sequential iteration in memory."
        ),
    ),

    Question(
        id="py-adv-006",
        topic="Testing & Testable Design",
        competency="Software Testing & Design",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.SCENARIO,
        text=(
            "You need to unit test a function `fetch_and_aggregate_metrics(client, service_url: str)` that calls an external HTTP API "
            "and writes processed records to an S3 bucket. How would you design unit tests for this function without making real network or AWS calls? "
            "Discuss `unittest.mock` (or `pytest-mock`), patching scope, and how to verify both success and failure cases."
        ),
        expected_concepts=[
            "Isolating external dependencies using mocking / patching (`unittest.mock.patch` or `MagicMock`)",
            "Patch where the object is looked up, not where it is defined (target the namespace of the module under test)",
            "Mocking client methods to return simulated responses or raise network/HTTP exceptions",
            "Asserting interactions: `mock.assert_called_once_with(...)`, call counts, and argument payloads",
            "Testing failure pathways: simulating timeouts or 500 errors to verify retry or fallback behavior",
            "Dependency injection design: passing clients into the function rather than instantiating hardcoded singletons",
        ],
        optional_concepts=[
            "Using `pytest` fixtures for clean setup/teardown",
            "Mock autospecing (`spec=...` or `autospec=True`) to avoid mocking methods that don't exist",
        ],
        common_misconceptions=[
            "Believing unit tests should hit live external staging servers",
            "Patching the original definition instead of the imported reference in the consumer module",
            "Only testing the happy path and never simulating raised exceptions",
        ],
        rubric=[
            RubricCriterion(
                id="mocking_strategy",
                description="Explains mocking/patching external HTTP and S3 clients and dependency injection",
                max_marks=2.0,
                evidence_guide="Full marks for mocking external boundaries and using mocks/fixtures.",
            ),
            RubricCriterion(
                id="patching_location_rule",
                description="Mentions the principle of patching where the name is used/imported",
                max_marks=1.0,
                evidence_guide="Full marks for citing the 'patch where used' rule.",
            ),
            RubricCriterion(
                id="assertion_and_interaction",
                description="Explains asserting call arguments, return values, and call counts",
                max_marks=1.0,
                evidence_guide="Full marks for assert_called_with or payload validation.",
            ),
            RubricCriterion(
                id="failure_testing",
                description="Explains simulating exceptions (side_effect=TimeoutError/HTTPError) to test error handling",
                max_marks=1.0,
                evidence_guide="Full marks for testing error responses with side_effect or mocked exceptions.",
            ),
        ],
        reference_answer=(
            "1. Isolation Strategy:\n"
            "Use `unittest.mock.patch` or pass mock clients via Dependency Injection. "
            "Do not execute real network requests or AWS calls in unit tests.\n\n"
            "2. Where to Patch:\n"
            "Patch the client or requests in the namespace where the function under test imports it, "
            "not where the library was originally defined ('patch where used').\n\n"
            "3. Happy Path Verification:\n"
            "- Configure mock return values: `mock_client.get.return_value.json.return_value = {'data': [...]}`.\n"
            "- Call the function and assert returned aggregated data.\n"
            "- Assert interactions: `mock_s3.put_object.assert_called_once_with(Bucket='...', Key='...', Body=expected_payload)`.\n\n"
            "4. Failure Scenarios:\n"
            "- Simulate exceptions using `side_effect`: `mock_client.get.side_effect = requests.exceptions.Timeout`.\n"
            "- Verify that the function handles the exception gracefully, logs appropriately, or raises custom domain exceptions."
        ),
    ),

    # --- ADDITIONAL CURRICULUM QUESTIONS ---
    Question(
        id="py-beg-006",
        topic="Types & Falsiness",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.CODE_OUTPUT,
        text="What will each of the following expressions evaluate to in Python (True or False), and why? `bool('')`, `bool('False')`, `bool([])`, `bool([0])`, `bool(None)`.",
        expected_concepts=[
            "bool('') is False (empty string is falsy)",
            "bool('False') is True (non-empty string is truthy regardless of its text)",
            "bool([]) is False (empty collection is falsy)",
            "bool([0]) is True (non-empty list is truthy)",
            "bool(None) is False (None is inherently falsy)",
        ],
        optional_concepts=["Python calls __bool__() or falls back to __len__() to determine truthiness"],
        common_misconceptions=["Believing 'False' evaluates to False because the text says false"],
        rubric=[
            RubricCriterion(
                id="string_falsiness",
                description="Correctly evaluates bool('') as False and bool('False') as True with reasoning",
                max_marks=2.0,
                evidence_guide="Full marks for empty vs non-empty string truthiness.",
            ),
            RubricCriterion(
                id="collection_falsiness",
                description="Correctly evaluates bool([]) as False and bool([0]) as True with reasoning",
                max_marks=2.0,
                evidence_guide="Full marks for empty vs non-empty collection distinction.",
            ),
            RubricCriterion(
                id="none_falsiness",
                description="Correctly identifies bool(None) as False",
                max_marks=1.0,
                evidence_guide="Full marks for None being falsy.",
            ),
        ],
        reference_answer=(
            "1. bool('') -> False (empty string is falsy)\n"
            "2. bool('False') -> True (non-empty string; length > 0 evaluates to True)\n"
            "3. bool([]) -> False (empty collection is falsy)\n"
            "4. bool([0]) -> True (non-empty collection containing 1 element is truthy)\n"
            "5. bool(None) -> False (None singleton is falsy)\n"
            "Python determines truthiness by calling __bool__() if defined, or __len__() > 0."
        ),
    ),

    Question(
        id="py-beg-007",
        topic="Variable Scope & Globals",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.DEBUGGING,
        text=(
            "Explain why the following code raises an `UnboundLocalError`, and provide two clean ways to fix it:\n\n"
            "counter = 0\n"
            "def increment():\n"
            "    counter += 1\n"
            "increment()\n"
        ),
        expected_concepts=[
            "Python treats any variable assigned within a function scope as a local variable unless declared otherwise",
            "In `counter += 1`, Python looks up the local variable `counter` before it has been bound, raising UnboundLocalError",
            "Fix 1: Declare `global counter` inside the function",
            "Fix 2: Pass counter as a parameter and return the incremented value (pure function approach)",
        ],
        common_misconceptions=["Thinking Python searches global scope dynamically during augmented assignment without checking local bindings"],
        rubric=[
            RubricCriterion(
                id="explain_unbound_local",
                description="Explains that assignment within function scope marks the variable as local at compile time",
                max_marks=2.5,
                evidence_guide="Full marks for explaining local variable binding rules in Python.",
            ),
            RubricCriterion(
                id="global_keyword_fix",
                description="Provides global keyword fix",
                max_marks=1.5,
                evidence_guide="Full marks for declaring global counter.",
            ),
            RubricCriterion(
                id="pure_function_fix",
                description="Suggests pure function / parameter return or object encapsulation",
                max_marks=1.0,
                evidence_guide="Full marks for passing parameter and returning new value.",
            ),
        ],
        reference_answer=(
            "Because `counter += 1` includes an assignment (`counter = counter + 1`), the Python compiler marks `counter` as local to `increment()`. "
            "When executing the right-hand side `counter + 1`, local `counter` has not been assigned a value yet, raising `UnboundLocalError`.\n"
            "Fix 1 (Global declaration):\n"
            "def increment():\n"
            "    global counter\n"
            "    counter += 1\n\n"
            "Fix 2 (Idiomatic pure function):\n"
            "def increment(val):\n"
            "    return val + 1\n"
            "counter = increment(counter)"
        ),
    ),

    Question(
        id="py-beg-008",
        topic="Sets & Dictionary Hashing",
        competency="Python Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.PRACTICAL,
        text=(
            "Why is membership testing (`x in container`) significantly faster in a Python `set` or `dict` than in a `list`? "
            "What requirements must an object satisfy to be used as a set element or dictionary key?"
        ),
        expected_concepts=[
            "Sets and dicts use hash tables with average O(1) time complexity for lookup",
            "Lists require linear search O(N) checking elements one by one",
            "Objects in sets/dict keys must be hashable: implementing `__hash__()` and `__eq__()`",
            "Hash value must remain unchanged during the object's lifetime (immutability requirement)",
        ],
        common_misconceptions=["Believing lists use binary search by default", "Thinking mutable lists can be dictionary keys"],
        rubric=[
            RubricCriterion(
                id="complexity_comparison",
                description="Contrasts average O(1) hash lookup with O(N) linear list scan",
                max_marks=2.5,
                evidence_guide="Full marks for O(1) vs O(N) complexity distinction.",
            ),
            RubricCriterion(
                id="hashability_requirements",
                description="States that objects must be hashable with immutable hash value and __eq__",
                max_marks=2.5,
                evidence_guide="Full marks for __hash__, __eq__, and immutability.",
            ),
        ],
        reference_answer=(
            "Sets and dictionaries are implemented using hash tables. When checking `x in s`, Python hashes `x` via `hash(x)` to find "
            "its bucket directly in average O(1) constant time. In contrast, lists are contiguous arrays requiring sequential linear "
            "scanning taking O(N) time.\n"
            "Requirements for set elements and dict keys:\n"
            "1. The object must be hashable, implementing `__hash__()` returning an integer.\n"
            "2. It must implement `__eq__()` for equality comparison in case of hash collisions.\n"
            "3. If two objects compare equal, their hash values must be identical.\n"
            "4. The hash value must never change during the object's lifetime (requiring immutability)."
        ),
    ),

    Question(
        id="py-int-007",
        topic="Scope & LEGB Rule",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text="Explain Python's LEGB scope resolution rule. How does the `nonlocal` keyword differ from `global` in nested functions?",
        expected_concepts=[
            "LEGB order: Local -> Enclosing (closure) -> Global (module) -> Built-in",
            "`global` binds a variable name to the top-level module scope",
            "`nonlocal` binds a variable name to the nearest enclosing non-global scope (used in closures)",
            "Without nonlocal, assigning inside an inner function creates a new local variable",
        ],
        common_misconceptions=["Thinking nonlocal can bind to the global module scope if enclosing scope doesn't have it"],
        rubric=[
            RubricCriterion(
                id="legb_explanation",
                description="Clearly defines Local, Enclosing, Global, Built-in lookup hierarchy",
                max_marks=2.5,
                evidence_guide="Full marks for all four tiers in correct order.",
            ),
            RubricCriterion(
                id="nonlocal_vs_global",
                description="Contrasts nonlocal (enclosing closure scope) with global (module level scope)",
                max_marks=2.5,
                evidence_guide="Full marks for distinguishing enclosing frame vs module scope.",
            ),
        ],
        reference_answer=(
            "The LEGB rule defines Python's variable lookup resolution order:\n"
            "1. Local: Inside current function or lambda.\n"
            "2. Enclosing: Inside enclosing outer/closure functions (from innermost to outermost).\n"
            "3. Global: Module-level variables.\n"
            "4. Built-in: Python built-in namespace (`len`, `range`, `Exception`).\n\n"
            "Difference between `global` and `nonlocal`:\n"
            "- `global` declares that an assignment targets the module-level scope.\n"
            "- `nonlocal` declares that an assignment targets a variable in the nearest enclosing function scope, "
            "enabling closures to mutate outer function state without affecting global namespace."
        ),
    ),

    Question(
        id="py-int-008",
        topic="Sorting & Lambdas",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CODE_WRITING,
        text=(
            "Given a list of employee dictionaries `employees = [{'name': 'Alice', 'dept': 'Eng', 'salary': 120000}, ...]`, "
            "write code to sort the list primarily by `dept` alphabetically ascending, and secondarily by `salary` descending. "
            "Use `sorted()` or `.sort()` with a key function."
        ),
        expected_concepts=[
            "Using `sorted()` with a custom `key` lambda or function",
            "Returning a tuple from the key function for multi-criterion sorting: `(emp['dept'], -emp['salary'])`",
            "Inverting numerical order with negative sign `-emp['salary']`",
        ],
        common_misconceptions=["Calling sort twice without understanding Timsort stability, or failing to reverse salary"],
        rubric=[
            RubricCriterion(
                id="key_function_tuple",
                description="Uses key lambda returning tuple for primary and secondary sorting",
                max_marks=3.0,
                evidence_guide="Full marks for (emp['dept'], -emp['salary']) tuple key.",
            ),
            RubricCriterion(
                id="descending_numerical_sort",
                description="Correctly handles descending salary via negation or stable secondary sort",
                max_marks=2.0,
                evidence_guide="Full marks for -emp['salary'] or two-pass stable sort.",
            ),
        ],
        reference_answer=(
            "sorted_employees = sorted(\n"
            "    employees,\n"
            "    key=lambda emp: (emp['dept'], -emp['salary'])\n"
            ")\n"
            "# The key returns a tuple: primary department ascending, secondary negated salary for descending."
        ),
    ),

    Question(
        id="py-int-009",
        topic="Built-in Sequence Functions",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.PRACTICAL,
        text=(
            "Explain what `zip()` and `enumerate()` do in Python. What happens when `zip()` is used on iterables "
            "of unequal lengths in Python 3.10+, and how can you handle unequal lengths safely?"
        ),
        expected_concepts=[
            "`enumerate(iterable, start=0)` yields pairs of `(index, item)` during iteration",
            "`zip(*iterables)` aggregates corresponding elements from each iterable into tuples",
            "By default, `zip()` stops when the shortest iterable is exhausted, silently truncating longer iterables",
            "Python 3.10 added `zip(..., strict=True)` which raises `ValueError` if lengths differ",
            "`itertools.zip_longest(*iterables, fillvalue=None)` pads shorter iterables with a fill value",
        ],
        common_misconceptions=["Believing zip raises an error by default when lengths differ"],
        rubric=[
            RubricCriterion(
                id="zip_enumerate_definitions",
                description="Accurately defines enumerate (index-item pairs) and zip (tuple aggregation)",
                max_marks=2.0,
                evidence_guide="Full marks for basic mechanisms.",
            ),
            RubricCriterion(
                id="unequal_length_truncation",
                description="Explains default truncation to shortest iterable",
                max_marks=1.5,
                evidence_guide="Full marks for shortest-iterable truncation behavior.",
            ),
            RubricCriterion(
                id="strict_and_zip_longest",
                description="Cites zip(strict=True) or itertools.zip_longest",
                max_marks=1.5,
                evidence_guide="Full marks for zip_longest or strict=True.",
            ),
        ],
        reference_answer=(
            "- `enumerate(iterable, start=0)`: Yields pairs of (index, element), eliminating manual index counters.\n"
            "- `zip(*iterables)`: Pairs up corresponding elements from each iterable as tuples until the shortest iterable ends.\n"
            "When iterables have unequal lengths:\n"
            "1. Default behavior silently truncates at the length of the shortest iterable, which can mask bugs.\n"
            "2. Python 3.10+ introduced `strict=True`: `zip(a, b, strict=True)` raises `ValueError` if lengths differ.\n"
            "3. `itertools.zip_longest(a, b, fillvalue=None)` iterates until the longest iterable finishes, padding missing values."
        ),
    ),

    Question(
        id="py-int-010",
        topic="Time & Space Complexity",
        competency="Python Intermediate",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.CONCEPTUAL,
        text=(
            "Compare the time complexity of `list.append(x)` versus `list.insert(0, x)` in Python. "
            "If an algorithm requires frequent insertions and removals from both ends of a sequence, what data structure should you use and why?"
        ),
        expected_concepts=[
            "`list.append(x)` is amortized O(1) constant time",
            "`list.insert(0, x)` is O(N) linear time because all existing elements must be shifted in memory",
            "Use `collections.deque` (double-ended queue) for O(1) append and pop from both left and right ends",
            "`deque` is implemented as a doubly linked list of fixed-size blocks",
        ],
        common_misconceptions=["Thinking list.insert(0, x) is O(1)", "Suggesting reversing the list on every insertion"],
        rubric=[
            RubricCriterion(
                id="complexity_comparison",
                description="Contrasts amortized O(1) append with O(N) shift for insert(0)",
                max_marks=2.5,
                evidence_guide="Full marks for O(1) amortized vs O(N) element shift.",
            ),
            RubricCriterion(
                id="collections_deque",
                description="Recommends collections.deque for O(1) operations at both ends",
                max_marks=2.5,
                evidence_guide="Full marks for identifying deque and its O(1) appendleft/popleft.",
            ),
        ],
        reference_answer=(
            "In CPython, a list is a dynamic array of contiguous pointers.\n"
            "- `list.append(x)`: Appends to the end in amortized O(1) time because pre-allocated memory slots accommodate new items.\n"
            "- `list.insert(0, x)`: Requires shifting all N existing pointers one index to the right, taking O(N) linear time.\n"
            "If you need frequent additions or removals from both ends, use `collections.deque`.\n"
            "`deque` supports O(1) `append`, `appendleft`, `pop`, and `popleft` implemented as a doubly-linked list of blocks."
        ),
    ),

    Question(
        id="py-adv-007",
        topic="Python Data Model & Sequences",
        competency="Advanced Python Concepts",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.CODE_WRITING,
        text=(
            "Implement a minimal custom immutable sequence class `StepRange` that represents a range with a step. "
            "Implement `__init__(self, start, stop, step=1)`, `__len__(self)`, `__getitem__(self, index)`, "
            "and `__repr__(self)`. Support negative indexing in `__getitem__` and raise `IndexError` on out-of-range access."
        ),
        expected_concepts=[
            "Calculating length in `__len__`: `max(0, (stop - start + step - 1) // step)`",
            "Handling negative index: `if index < 0: index += length`",
            "Raising `IndexError` when `index < 0 or index >= length`",
            "Computing element in O(1): `self.start + index * self.step` without storing elements in memory",
        ],
        common_misconceptions=["Generating a full list in memory inside __init__ rather than O(1) computation"],
        rubric=[
            RubricCriterion(
                id="len_and_element_math",
                description="Correctly calculates sequence length and computes item at index in O(1)",
                max_marks=2.5,
                evidence_guide="Full marks for O(1) calculation without allocating list.",
            ),
            RubricCriterion(
                id="negative_index_and_bounds",
                description="Handles negative indices and raises IndexError for out of bounds",
                max_marks=2.0,
                evidence_guide="Full marks for index normalization and IndexError.",
            ),
            RubricCriterion(
                id="repr_implementation",
                description="Implements informative __repr__",
                max_marks=0.5,
                evidence_guide="Awarded for clean __repr__.",
            ),
        ],
        reference_answer=(
            "class StepRange:\n"
            "    def __init__(self, start, stop, step=1):\n"
            "        if step == 0: raise ValueError('step cannot be 0')\n"
            "        self.start = start\n"
            "        self.stop = stop\n"
            "        self.step = step\n"
            "        self._len = max(0, (stop - start + (step - (1 if step > 0 else -1))) // step)\n\n"
            "    def __len__(self):\n"
            "        return self._len\n\n"
            "    def __getitem__(self, index):\n"
            "        if index < 0:\n"
            "            index += self._len\n"
            "        if index < 0 or index >= self._len:\n"
            "            raise IndexError('Index out of range')\n"
            "        return self.start + index * self.step\n\n"
            "    def __repr__(self):\n"
            "        return f'StepRange({self.start}, {self.stop}, {self.step})'\n"
        ),
    ),

    Question(
        id="py-adv-008",
        topic="Dataclasses & Slots",
        competency="Memory & Performance",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.CONCEPTUAL,
        text=(
            "What is the purpose of `__slots__` in Python classes? How does `@dataclass(slots=True)` "
            "(Python 3.10+) improve both memory footprint and attribute access speed?"
        ),
        expected_concepts=[
            "By default, Python instances store attributes in a dynamic `__dict__`, which incurs significant memory overhead",
            "`__slots__` tells Python not to create a per-instance `__dict__`, instead allocating a fixed array of descriptor pointers",
            "Memory savings: Can reduce memory usage by 40-70% for millions of small objects",
            "Attribute access is slightly faster via fixed C-level offsets",
            "`@dataclass(slots=True)` automatically generates `__slots__` for declared fields",
        ],
        common_misconceptions=["Thinking __slots__ prevents subclassing completely", "Believing __slots__ is only for immutability"],
        rubric=[
            RubricCriterion(
                id="dict_elimination_and_memory",
                description="Explains how __slots__ eliminates instance __dict__ and reduces memory footprint",
                max_marks=2.5,
                evidence_guide="Full marks for instance __dict__ elimination and memory reduction explanation.",
            ),
            RubricCriterion(
                id="dataclass_slots_integration",
                description="Explains @dataclass(slots=True) automated slot generation and performance benefits",
                max_marks=2.5,
                evidence_guide="Full marks for explaining slots=True convenience and fixed descriptor access.",
            ),
        ],
        reference_answer=(
            "By default, each Python object instance holds an internal `__dict__` dictionary to allow dynamic attribute assignment. "
            "Dictionaries have substantial memory overhead (around 100-150 bytes per instance).\n"
            "`__slots__` reserves space for a fixed set of attributes at the class level and eliminates the per-instance `__dict__` "
            "(and `__weakref__` unless specified).\n"
            "Benefits:\n"
            "1. Massive memory savings: For applications instantiating millions of records (e.g. data points, AST nodes), memory drops by 40-70%.\n"
            "2. Faster attribute access: Reads and writes bypass dictionary hash lookups and access fixed descriptor offsets directly in C.\n"
            "3. `@dataclass(slots=True)` (Python 3.10+) automatically builds `__slots__` from class type annotations without manual boilerplate."
        ),
    ),

    Question(
        id="py-adv-009",
        topic="Context Manager Implementation",
        competency="Advanced Python Concepts",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.CODE_WRITING,
        text=(
            "Implement a context manager `Timer` that measures the elapsed execution time of a code block. "
            "It must store `elapsed` as a float (in seconds). Implement it as a class using `__enter__` and `__exit__`. "
            "Ensure `__exit__` handles exceptions gracefully without suppressing them."
        ),
        expected_concepts=[
            "Implementing `__enter__(self)`: records `start_time = time.perf_counter()`, returns self",
            "Implementing `__exit__(self, exc_type, exc_val, exc_tb)`: records `elapsed = time.perf_counter() - start_time`",
            "Returning False (or None) from `__exit__` so that any raised exception is propagated rather than suppressed",
            "Using `time.perf_counter()` for high-precision benchmarking",
        ],
        common_misconceptions=["Returning True from __exit__, which suppresses all exceptions inside the with-block"],
        rubric=[
            RubricCriterion(
                id="enter_exit_timing",
                description="Records start time in __enter__ and computes elapsed in __exit__ using perf_counter",
                max_marks=2.5,
                evidence_guide="Full marks for time measurement across __enter__ and __exit__.",
            ),
            RubricCriterion(
                id="exception_propagation",
                description="Properly propagates exceptions by returning False/None from __exit__",
                max_marks=2.0,
                evidence_guide="Full marks for exc_type, exc_val, exc_tb parameters and returning False/None.",
            ),
            RubricCriterion(
                id="return_self",
                description="__enter__ returns self so target can be bound via 'as'",
                max_marks=0.5,
                evidence_guide="Awarded for returning self in __enter__.",
            ),
        ],
        reference_answer=(
            "import time\n\n"
            "class Timer:\n"
            "    def __init__(self):\n"
            "        self.elapsed = 0.0\n"
            "        self._start = None\n\n"
            "    def __enter__(self):\n"
            "        self._start = time.perf_counter()\n"
            "        return self\n\n"
            "    def __exit__(self, exc_type, exc_val, exc_tb):\n"
            "        self.elapsed = time.perf_counter() - self._start\n"
            "        return False  # Do not suppress exceptions\n"
        ),
    ),

    Question(
        id="py-adv-010",
        topic="Asyncio & Coroutines",
        competency="Concurrency & Asyncio",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.PRACTICAL,
        text=(
            "Explain the difference between a synchronous blocking function and an `async def` coroutine in Python. "
            "What happens if you execute a CPU-bound blocking call (like `time.sleep(5)` or heavy calculation) "
            "inside an asyncio coroutine, and how should such work be delegated to avoid freezing the event loop?"
        ),
        expected_concepts=[
            "An `async def` defines a coroutine that yields control back to the event loop upon `await`",
            "Calling a blocking function like `time.sleep()` freezes the entire single-threaded event loop, stalling all concurrent coroutines",
            "Non-blocking sleep must use `await asyncio.sleep(5)`",
            "CPU-bound or blocking legacy code must be offloaded to a thread or process pool via `asyncio.to_thread()` or `loop.run_in_executor()`",
        ],
        common_misconceptions=["Thinking async def automatically runs code in parallel threads"],
        rubric=[
            RubricCriterion(
                id="coroutine_vs_blocking",
                description="Explains cooperative multitasking vs blocking event loop execution",
                max_marks=2.5,
                evidence_guide="Full marks for explaining that blocking calls freeze the single-threaded event loop.",
            ),
            RubricCriterion(
                id="delegation_solution",
                description="Explains asyncio.to_thread() or loop.run_in_executor() with ThreadPool/ProcessPool",
                max_marks=2.5,
                evidence_guide="Full marks for citing asyncio.to_thread or run_in_executor.",
            ),
        ],
        reference_answer=(
            "In asyncio, concurrency is cooperative and runs on a single OS thread. When a coroutine reaches an `await`, "
            "it suspends itself and allows the event loop to run other scheduled tasks.\n"
            "Consequence of blocking calls:\n"
            "If you call a synchronous blocking function (e.g. `time.sleep(5)`, `requests.get()`, or heavy CPU computation), "
            "it does not yield control. It blocks the OS thread entirely, which completely freezes the event loop and delays all other coroutines.\n"
            "Remedies:\n"
            "1. Use native async equivalents: e.g. `await asyncio.sleep(5)` or `httpx.AsyncClient`.\n"
            "2. Offload blocking work: Use `asyncio.to_thread(func, *args)` (Python 3.9+) or `loop.run_in_executor(None, func)` "
            "to run blocking I/O on a ThreadPoolExecutor, or `ProcessPoolExecutor` for CPU-intensive calculations."
        ),
    ),
]
# Load Role Specialized Questions (Java, C++, Data Analyst, Data Engineer, ML, AI/ML, Software Engineer)
try:
    from backend.role_questions import ROLE_SPECIALIZED_QUESTIONS
    for _sq in ROLE_SPECIALIZED_QUESTIONS:
        if _sq.track != "fullstack" and _sq.id not in [q.id for q in QUESTION_BANK]:
            QUESTION_BANK.append(_sq)
except ImportError:
    pass


def get_question_by_id(question_id: str) -> Optional[Question]:
    """Retrieve a question by its unique ID."""
    for q in QUESTION_BANK:
        if q.id == question_id:
            return q
    return None


def get_all_questions() -> List[Question]:
    """Return all questions in the bank."""
    return list(QUESTION_BANK)


def get_questions_by_difficulty(level: DifficultyLevel) -> List[Question]:
    """Retrieve questions filtered by difficulty."""
    return [q for q in QUESTION_BANK if q.difficulty == level]


def get_questions_by_competency(competency: str) -> List[Question]:
    """Retrieve questions filtered by competency."""
    return [q for q in QUESTION_BANK if q.competency.lower() == competency.lower()]


def get_all_topics() -> List[str]:
    """Get unique list of all topics in question bank."""
    return sorted(list({q.topic for q in QUESTION_BANK}))


def get_all_competencies() -> List[str]:
    """Get unique list of all competencies in question bank."""
    return sorted(list({q.competency for q in QUESTION_BANK}))
