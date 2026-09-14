"""Dynamic Intent Classifier."""
import re

CPP_PATTERN = re.compile(r"\b(std::|vector<|cout|cin|nullptr|#include|template<|auto&)\b")
PYTHON_PATTERN = re.compile(r"\b(def |import |class |self\.|lambda |elif |print\()\b")
SQL_PATTERN = re.compile(r"(?i)\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|JOIN|INSERT INTO)\b")

def detect_language_intent(prompt: str) -> str:
    if CPP_PATTERN.search(prompt):
        return "cpp"
    if PYTHON_PATTERN.search(prompt):
        return "python"
    if SQL_PATTERN.search(prompt):
        return "sql"
    return "text"
