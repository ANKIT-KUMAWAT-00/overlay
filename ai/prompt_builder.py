"""
Dynamic system prompt construction, contextual assembly, and format specialization.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple
from ai.provider import OutputFormat
from security.privacy import PrivacyFilter
from logging_service.logger import get_logger

logger = get_logger("ai.prompt_builder")

CODE_KEYWORD_REGEX = re.compile(
    r"\b(code|coding|program|programming|function|class|def|import|sql|javascript|python|typescript|java|cpp|c\+\+|c#|golang|rust|html|css|algorithm|bug|fix|refactor|regex|leetcode|hackerrank|solver|solve|solution|implementation|sudoku|array|string|list|tree|graph|dp|backtrack|matrix)\b",
    re.IGNORECASE,
)
CPP_INDICATORS = re.compile(
    r"(\b(c\+\+|cpp|cplusplus|#include\s*<|std::|std::vector|vector<|cout|cin|nullptr)\b|class\s+\w+\s*\{?\s*public\s*:)",
    re.IGNORECASE,
)
PYTHON_INDICATORS = re.compile(
    r"\b(python|python3|def\s+\w+\s*\(|elif\s+|import\s+\w+|from\s+\w+\s+import|if\s+__name__\s*==)\b",
    re.IGNORECASE,
)
JAVA_INDICATORS = re.compile(
    r"\b(java|public\s+class|System\.out\.print|ArrayList<|HashMap<)\b",
    re.IGNORECASE,
)
JS_INDICATORS = re.compile(
    r"\b(javascript|typescript|const\s+\w+\s*=|let\s+\w+\s*=|console\.log|function\s+\w+\s*\(|=>)\b",
    re.IGNORECASE,
)
MCQ_KEYWORD_REGEX = re.compile(
    r"(\b(which of the following|choose the correct|select one|options?:|\([A-D]\)|[A-D]\))\b)",
    re.IGNORECASE,
)
JSON_KEYWORD_REGEX = re.compile(r"\b(json|schema|payload)\b", re.IGNORECASE)


class PromptBuilder:
    """
    Constructs high-precision system instructions and assembled prompts.
    """

    def __init__(self, privacy_filter: Optional[PrivacyFilter] = None) -> None:
        self.privacy_filter = privacy_filter or PrivacyFilter()

    def detect_format_intent(self, question: str) -> OutputFormat:
        """Heuristically infers output format preference if set to AUTO."""
        if not question:
            return OutputFormat.THEORY

        q_lower = question.lower()
        if MCQ_KEYWORD_REGEX.search(question):
            return OutputFormat.MULTIPLE_CHOICE
        if JSON_KEYWORD_REGEX.search(question):
            return OutputFormat.JSON

        # Specific language code intent
        if CPP_INDICATORS.search(question):
            return OutputFormat.CODE_CPP
        if JAVA_INDICATORS.search(question):
            return OutputFormat.CODE_JAVA
        if PYTHON_INDICATORS.search(question):
            return OutputFormat.CODE_PYTHON
        if JS_INDICATORS.search(question):
            return OutputFormat.CODE_JS
        if CODE_KEYWORD_REGEX.search(question):
            return OutputFormat.CODE

        if "in one sentence" in q_lower or "short answer" in q_lower:
            return OutputFormat.SHORT_ANSWER

        return OutputFormat.THEORY

    def build_system_instruction(self, format_preference: OutputFormat, target_app: Optional[str] = None) -> str:
        """Returns targeted system instruction for the chosen output format."""
        base_instruction = (
            "You are OmniAssist, a high-precision AI desktop assistant for developers and professionals. "
            "Your output is directly inserted into active applications via hotkeys. "
            "You MUST follow the requested format strictly."
        )

        app_context = f" The user is actively working in: {target_app}." if target_app else ""

        if format_preference in (
            OutputFormat.CODE,
            OutputFormat.CODE_CPP,
            OutputFormat.CODE_PYTHON,
            OutputFormat.CODE_JAVA,
            OutputFormat.CODE_JS,
        ):
            lang_directive = (
                "PROGRAMMING LANGUAGE DIRECTIVE: "
                "Detect the required programming language from the question, problem statement, editor stub, or screenshot. "
                "If C++ (cpp, c++, #include, std::, class Solution { public: ... }) is requested or provided, you MUST write C++ (modern C++17/C++20). "
                "If Java is requested or provided, you MUST write Java. "
                "If Python is requested or provided, you MUST write Python. "
                "If TypeScript / JavaScript, Go, Rust, or SQL is requested or provided, write that exact language. "
                "Do NOT default to Python when C++ or another language is asked for or present in the problem context. "
            )
            if format_preference == OutputFormat.CODE_CPP:
                lang_directive = (
                    "EXPLICIT LANGUAGE REQUIREMENT: Write the solution in modern, high-performance C++ (C++17/C++20). "
                    "Include necessary standard headers (<iostream>, <vector>, <algorithm>, etc.) and proper types. "
                )
            elif format_preference == OutputFormat.CODE_PYTHON:
                lang_directive = "EXPLICIT LANGUAGE REQUIREMENT: Write the solution in clean, idiomatic Python 3. "
            elif format_preference == OutputFormat.CODE_JAVA:
                lang_directive = "EXPLICIT LANGUAGE REQUIREMENT: Write the solution in clean, idiomatic Java. "
            elif format_preference == OutputFormat.CODE_JS:
                lang_directive = "EXPLICIT LANGUAGE REQUIREMENT: Write the solution in clean, modern JavaScript / TypeScript. "

            return (
                f"{base_instruction}{app_context} "
                f"{lang_directive}"
                "CRITICAL FORMAT RULE: The user needs direct raw code for immediate insertion and compilation/execution. "
                "Output ONLY the clean, valid, executable solution code. "
                "STRICTLY FORBIDDEN: Do NOT include conversational introductions, explanations, 'Problem Analysis', "
                "'Solution Approach', or 'Complexity Analysis' sections. "
                "Do NOT wrap in markdown fences or add commentary unless specifically requested. "
                "Provide ONLY the code itself with proper indentation and imports/includes."
            )

        if format_preference == OutputFormat.MULTIPLE_CHOICE:
            return (
                f"{base_instruction}{app_context} "
                "CRITICAL FORMAT RULE: Multiple-choice question detected. "
                "Output the correct option letter and text on the first line. "
                "On the second line, provide a single concise sentence explaining why."
            )

        if format_preference == OutputFormat.JSON:
            return (
                f"{base_instruction}{app_context} "
                "CRITICAL FORMAT RULE: Output ONLY a strictly valid, parseable JSON object or array. "
                "Do NOT wrap in markdown backticks or add introductory commentary."
            )

        if format_preference == OutputFormat.SHORT_ANSWER:
            return (
                f"{base_instruction}{app_context} "
                "CRITICAL FORMAT RULE: Return only the exact, direct answer. Be as concise as possible (1-2 sentences maximum)."
            )

        if format_preference == OutputFormat.PARAGRAPH:
            return (
                f"{base_instruction}{app_context} "
                "CRITICAL FORMAT RULE: Return a single, cohesive, well-composed paragraph answering the request."
            )

        # OutputFormat.THEORY or AUTO
        return (
            f"{base_instruction}{app_context} "
            "Provide a direct, accurate, and concise solution. "
            "If the problem is a coding or algorithm task, provide the complete working code directly without "
            "unnecessary introductory analysis essays, verbose problem breakdowns, or redundant complexity sections."
        )

    def assemble_user_prompt(
        self,
        question: str,
        context: Optional[str] = None,
        target_app: Optional[str] = None,
        format_preference: OutputFormat = OutputFormat.AUTO,
    ) -> Tuple[str, OutputFormat]:
        """
        Cleans and packages user prompt with sanitized context and inferred format.
        """
        # Determine format
        if format_preference == OutputFormat.AUTO:
            effective_format = self.detect_format_intent(question)
        else:
            effective_format = format_preference

        # Sanitize inputs
        clean_question, q_warns = self.privacy_filter.sanitize(question.strip())
        parts = []

        if context and context.strip():
            clean_context, _ = self.privacy_filter.sanitize(context.strip())
            parts.append(f"--- ACTIVE CONTEXT ---\n{clean_context}\n--- END CONTEXT ---\n")

        parts.append(f"QUESTION / REQUEST:\n{clean_question}")

        if effective_format == OutputFormat.CODE_CPP:
            parts.append("\n[Reminder: Provide direct, modern C++ code only, ready to compile and run]")
        elif effective_format == OutputFormat.CODE_PYTHON:
            parts.append("\n[Reminder: Provide direct Python code only, ready to run]")
        elif effective_format == OutputFormat.CODE_JAVA:
            parts.append("\n[Reminder: Provide direct Java code only, ready to compile and run]")
        elif effective_format == OutputFormat.CODE_JS:
            parts.append("\n[Reminder: Provide direct JavaScript/TypeScript code only, ready to run]")
        elif effective_format == OutputFormat.CODE:
            parts.append("\n[Reminder: Provide direct code in the problem's language, ready to run/compile]")
        elif effective_format == OutputFormat.JSON:
            parts.append("\n[Reminder: Return valid JSON only]")

        assembled_prompt = "\n".join(parts)
        return assembled_prompt, effective_format
