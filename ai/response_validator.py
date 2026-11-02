"""
Multi-stage response validation, syntax checking, truncation detection, and bounded correction.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

from ai.provider import OutputFormat
from logging_service.logger import get_logger

logger = get_logger("ai.response_validator")

# Regex to detect unwanted introductory pleasantries
INTRO_CHATTER_REGEX = re.compile(
    r"^(?:sure(?: thing)?[!.,]?|here(?: is|'s) (?:the |your )?(?:code|json|answer|solution|result)[:\s]*|certainly[!.,]?|okay,?\s*)",
    re.IGNORECASE,
)

# Markdown code fence regex
CODE_FENCE_REGEX = re.compile(r"^```(?:[a-zA-Z0-9_\-\.\+#]+)?\n([\s\S]*?)\n```$", re.MULTILINE)


@dataclass
class ValidationResult:
    """Outcome of response validation and auto-correction."""
    is_valid: bool
    raw_text: str
    corrected_text: str
    is_truncated: bool = False
    has_syntax_errors: bool = False
    warnings: List[str] = field(default_factory=list)
    detected_format: OutputFormat = OutputFormat.THEORY


class ResponseValidator:
    """
    Validates syntax, catches truncation, and applies bounded auto-corrections.
    """

    def validate(
        self,
        text: str,
        expected_format: OutputFormat = OutputFormat.AUTO,
        finish_reason: str = "STOP",
    ) -> ValidationResult:
        if not text:
            return ValidationResult(
                is_valid=False,
                raw_text="",
                corrected_text="",
                is_truncated=True,
                warnings=["Empty response received from AI model."],
            )

        warnings: List[str] = []
        is_truncated = finish_reason == "MAX_TOKENS" or self._detect_truncation(text)
        if is_truncated:
            warnings.append("Response appears truncated or reached max token limit.")

        corrected = text.strip()

        # Step 1: Strip unwanted intro pleasantries for machine-readable formats
        if expected_format in (OutputFormat.CODE, OutputFormat.JSON, OutputFormat.SHORT_ANSWER):
            stripped_any = False
            while True:
                cleaned = INTRO_CHATTER_REGEX.sub("", corrected).strip()
                if cleaned == corrected:
                    break
                corrected = cleaned
                stripped_any = True
            if stripped_any:
                warnings.append("Stripped conversational introductory prefix.")

        # Step 2: Strip outer Markdown code fences or extract embedded code from analysis chatter
        if expected_format in (OutputFormat.CODE, OutputFormat.JSON) or (
            expected_format == OutputFormat.AUTO and "```" in corrected
        ):
            match = CODE_FENCE_REGEX.match(corrected)
            if match:
                corrected = match.group(1).strip()
                warnings.append("Extracted content from outer markdown code fences.")
            elif corrected.startswith("```") and corrected.endswith("```") and corrected.count("```") == 2:
                lines = corrected.splitlines()
                if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
                    corrected = "\n".join(lines[1:-1]).strip()
                    warnings.append("Extracted content from outer markdown code fences.")
            else:
                embedded_blocks = re.findall(r"```(?:[a-zA-Z0-9_\-\.\+#]+)?\n([\s\S]*?)\n```", corrected)
                if embedded_blocks:
                    largest_code = max(embedded_blocks, key=len).strip()
                    if (
                        expected_format in (OutputFormat.CODE, OutputFormat.JSON)
                        or any(
                            term in corrected.lower()
                            for term in (
                                "problem analysis",
                                "implementation",
                                "solution approach",
                                "complexity analysis",
                                "class solution",
                                "def ",
                                "function ",
                            )
                        )
                    ):
                        corrected = largest_code
                        warnings.append("Extracted pure solution code, stripping surrounding analysis and commentary.")

        # Step 3: Format-specific syntax checking
        has_syntax_errors = False
        if expected_format == OutputFormat.JSON:
            json_valid, json_err = self._validate_json(corrected)
            if not json_valid:
                has_syntax_errors = True
                warnings.append(f"JSON validation failed: {json_err}")
                # Attempt light correction if unclosed brace
                fixed_json = self._attempt_json_repair(corrected)
                if fixed_json:
                    corrected = fixed_json
                    has_syntax_errors = False
                    warnings.append("Auto-repaired incomplete JSON braces.")

        elif expected_format in (
            OutputFormat.CODE,
            OutputFormat.CODE_CPP,
            OutputFormat.CODE_PYTHON,
            OutputFormat.CODE_JAVA,
            OutputFormat.CODE_JS,
        ):
            if expected_format == OutputFormat.CODE_PYTHON or (
                expected_format == OutputFormat.CODE and self._looks_like_python(corrected)
            ):
                py_valid, py_err = self._validate_python(corrected)
                if not py_valid:
                    warnings.append(f"Python AST check notice: {py_err}")
            elif expected_format == OutputFormat.CODE_CPP or self._looks_like_cpp(corrected):
                cpp_valid, cpp_err = self._validate_cpp(corrected)
                if not cpp_valid:
                    warnings.append(f"C++ syntax check notice: {cpp_err}")

        # Step 4: Delimiter balance check
        balanced, delim_err = self._check_delimiter_balance(corrected)
        if not balanced:
            warnings.append(f"Delimiter notice: {delim_err}")

        is_valid = not has_syntax_errors and (not is_truncated or len(corrected) > 0)

        return ValidationResult(
            is_valid=is_valid,
            raw_text=text,
            corrected_text=corrected,
            is_truncated=is_truncated,
            has_syntax_errors=has_syntax_errors,
            warnings=warnings,
            detected_format=expected_format,
        )

    def _detect_truncation(self, text: str) -> bool:
        """Heuristics to detect whether text cut off abruptly mid-sentence or mid-expression."""
        t = text.strip()
        # Unclosed code block
        if t.count("```") % 2 != 0:
            return True
        # Ending with hanging operators or commas
        if t.endswith(("+", "-", "*", "/", "=", "->", "=>", "(", "[", "{", ",", "\\")):
            return True
        return False

    def _validate_json(self, text: str) -> tuple[bool, Optional[str]]:
        try:
            json.loads(text)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def _attempt_json_repair(self, text: str) -> Optional[str]:
        """Tries to balance missing trailing braces for truncated JSON."""
        open_curlies = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        candidate = text
        if open_brackets > 0:
            candidate += "]" * open_brackets
        if open_curlies > 0:
            candidate += "}" * open_curlies
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            return None

    def _looks_like_cpp(self, text: str) -> bool:
        """Determines if the snippet appears to be C++ code."""
        cpp_patterns = [
            r"#include\s*<",
            r"using\s+namespace\s+std",
            r"std::",
            r"class\s+\w+\s*\{?\s*public\s*:",
            r"int\s+main\s*\(",
            r"vector<",
            r"cout\s*<<",
            r"cin\s*>>",
            r"nullptr",
            r"template\s*<",
        ]
        return any(re.search(p, text) for p in cpp_patterns)

    def _looks_like_python(self, text: str) -> bool:
        """Determines if the snippet appears to be Python code, ensuring C++ is not misclassified."""
        if self._looks_like_cpp(text):
            return False
        # If semicolons end multiple lines and braces are present, it is not Python
        if re.search(r";\s*$", text, re.MULTILINE) and ("{" in text or "}" in text):
            return False
        return bool(re.search(r"^(?:import |from |def |class \w+[(:]|if __name__ ==)", text, re.MULTILINE))

    def _validate_cpp(self, text: str) -> tuple[bool, Optional[str]]:
        """Performs sanity validation for C++ code: checks balanced braces and basic syntax."""
        open_c = text.count("{")
        close_c = text.count("}")
        if open_c != close_c:
            return False, f"Unbalanced braces in C++ code: {open_c} '{{' vs {close_c} '}}'"
        return True, None

    def _validate_python(self, text: str) -> tuple[bool, Optional[str]]:
        try:
            ast.parse(text)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def _check_delimiter_balance(self, text: str) -> tuple[bool, Optional[str]]:
        stack = []
        pairs = {")": "(", "}": "{", "]": "["}
        # Ignore comments and quotes for simple check
        for char in text:
            if char in "({[":
                stack.append(char)
            elif char in ")}]":
                if not stack or stack[-1] != pairs[char]:
                    return False, f"Mismatched delimiter '{char}'"
                stack.pop()
        if stack:
            return False, f"Unclosed delimiters: {stack}"
        return True, None
