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
    r"\b(code|function|class|def|import|sql|javascript|python|typescript|java|cpp|c\+\+|html|css|algorithm|bug|fix|refactor|regex)\b",
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
        if CODE_KEYWORD_REGEX.search(question):
            return OutputFormat.CODE
        if "in one sentence" in q_lower or "short answer" in q_lower:
            return OutputFormat.SHORT_ANSWER

        return OutputFormat.THEORY

    def build_system_instruction(self, format_preference: OutputFormat, target_app: Optional[str] = None) -> str:
        """Returns targeted system instruction for the chosen output format."""
        base_instruction = (
            "You are OmniAssist, a world-class AI desktop interaction assistant. "
            "You provide accurate, immediate solutions to computer tasks. "
            "Follow the requested format strictly."
        )

        app_context = f" The user is actively working in: {target_app}." if target_app else ""

        if format_preference == OutputFormat.CODE:
            return (
                f"{base_instruction}{app_context} "
                "CRITICAL FORMAT RULE: The user needs raw code for direct insertion. "
                "Output ONLY valid, executable code without conversational intros, explanations, or Markdown code fences "
                "unless specifically asked to format as Markdown. Preserve exact indentation and syntax."
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
            "Provide a clear, well-structured, precise explanation. "
            "Use bullet points or structured headers if helpful. Avoid unnecessary fluff."
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

        if effective_format == OutputFormat.CODE:
            parts.append("\n[Reminder: Provide direct code only, ready to run/paste]")
        elif effective_format == OutputFormat.JSON:
            parts.append("\n[Reminder: Return valid JSON only]")

        assembled_prompt = "\n".join(parts)
        return assembled_prompt, effective_format
