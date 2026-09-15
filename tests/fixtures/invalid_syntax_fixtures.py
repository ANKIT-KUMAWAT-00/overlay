"""Test fixtures with invalid Python snippets."""
BROKEN_PYTHON_SNIPPETS = [
    "def unfinished_function(x:\n    return x + 1",
    "if x > 10\n    print('error')",
    "for i in range(10):\nprint(i)"
]
