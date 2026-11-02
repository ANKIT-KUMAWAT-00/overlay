"""
Unit tests for AI prompt builder and response validation engine.
"""

import pytest
from ai.provider import OutputFormat, AIError
from ai.prompt_builder import PromptBuilder
from ai.response_validator import ResponseValidator


def test_ai_error_model():
    err = AIError(message="Auth failure", category="auth", retryable=False, status_code=401)
    assert err.category == "auth"
    assert not err.retryable
    assert err.status_code == 401


def test_prompt_builder_intent_detection():
    pb = PromptBuilder()

    assert pb.detect_format_intent("Write a function to sort an array") == OutputFormat.CODE
    assert pb.detect_format_intent("Write a Python function to sort an array") in (OutputFormat.CODE, OutputFormat.CODE_PYTHON)
    assert pb.detect_format_intent("Write a C++ solution using std::vector") in (OutputFormat.CODE, OutputFormat.CODE_CPP)
    assert pb.detect_format_intent("Which of the following is correct: (A) or (B)?") == OutputFormat.MULTIPLE_CHOICE
    assert pb.detect_format_intent("Return the user profile as a json schema") == OutputFormat.JSON
    assert pb.detect_format_intent("What is the capital of France in one sentence?") == OutputFormat.SHORT_ANSWER
    assert pb.detect_format_intent("Explain quantum entanglement in depth") == OutputFormat.THEORY


def test_prompt_builder_cpp_system_instruction():
    pb = PromptBuilder()
    sys_cpp = pb.build_system_instruction(OutputFormat.CODE_CPP, target_app="CLion")
    assert "C++" in sys_cpp
    assert "CLion" in sys_cpp
    assert "headers" in sys_cpp.lower()


def test_response_validator_cpp_code_does_not_fail_ast():
    validator = ResponseValidator()
    cpp_code = (
        "#include <iostream>\n"
        "#include <vector>\n"
        "using namespace std;\n\n"
        "class Solution {\n"
        "public:\n"
        "    int maxSubArray(vector<int>& nums) {\n"
        "        int maxSum = nums[0];\n"
        "        int curSum = 0;\n"
        "        for (int x : nums) {\n"
        "            curSum = max(x, curSum + x);\n"
        "            maxSum = max(maxSum, curSum);\n"
        "        }\n"
        "        return maxSum;\n"
        "    }\n"
        "};"
    )
    result = validator.validate(cpp_code, expected_format=OutputFormat.CODE)
    assert result.is_valid
    # Make sure it did NOT add a Python AST error notice
    assert not any("Python AST check notice" in w for w in result.warnings)



def test_prompt_builder_system_instruction():
    pb = PromptBuilder()
    sys_code = pb.build_system_instruction(OutputFormat.CODE, target_app="Cursor")
    assert "Cursor" in sys_code
    assert "raw code" in sys_code.lower()

    sys_mcq = pb.build_system_instruction(OutputFormat.MULTIPLE_CHOICE)
    assert "multiple-choice" in sys_mcq.lower()


def test_response_validator_code_fence_stripping():
    validator = ResponseValidator()
    raw = "```python\ndef add(a, b):\n    return a + b\n```"
    result = validator.validate(raw, expected_format=OutputFormat.CODE)

    assert result.is_valid
    assert result.corrected_text == "def add(a, b):\n    return a + b"
    assert "Extracted content from outer markdown code fences." in result.warnings


def test_response_validator_intro_pleasantry_stripping():
    validator = ResponseValidator()
    raw = "Sure! Here is your code:\nconst x = 10;"
    result = validator.validate(raw, expected_format=OutputFormat.CODE)

    assert result.is_valid
    assert result.corrected_text == "const x = 10;"


def test_response_validator_json_repair():
    validator = ResponseValidator()
    # Incomplete trailing brace
    raw = '{"status": "ok", "items": [1, 2, 3]'
    result = validator.validate(raw, expected_format=OutputFormat.JSON)

    assert result.is_valid
    assert result.corrected_text == '{"status": "ok", "items": [1, 2, 3]}'
    assert "Auto-repaired incomplete JSON braces." in result.warnings


def test_response_validator_truncation_detection():
    validator = ResponseValidator()
    raw = "def incomplete_func(a, b): return a +"
    result = validator.validate(raw, expected_format=OutputFormat.CODE)

    assert result.is_truncated


def test_response_validator_extracts_code_from_analysis_commentary():
    validator = ResponseValidator()
    raw = (
        "### Problem Analysis: 37. Sudoku Solver\n"
        "The task is to solve a 9x9 Sudoku puzzle...\n\n"
        "### Python Implementation\n"
        "```python\n"
        "class Solution:\n"
        "    def solveSudoku(self, board):\n"
        "        pass\n"
        "```\n\n"
        "### Complexity Analysis\n"
        "* Time Complexity: O(9^m)\n"
    )
    result = validator.validate(raw, expected_format=OutputFormat.CODE)
    assert result.is_valid
    assert result.corrected_text == "class Solution:\n    def solveSudoku(self, board):\n        pass"
    assert "Extracted pure solution code" in result.warnings[0]
