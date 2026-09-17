"""Delimiter Balancing Algorithm."""

def check_delimiter_balance(text: str) -> bool:
    pairs = {')': '(', '}': '{', ']': '['}
    stack = []
    in_string = False
    quote_char = None

    for ch in text:
        if ch in ('"', "'") and not in_string:
            in_string = True
            quote_char = ch
        elif ch == quote_char and in_string:
            in_string = False
        elif not in_string:
            if ch in "({[":
                stack.append(ch)
            elif ch in ")}]":
                if not stack or stack[-1] != pairs[ch]:
                    return False
                stack.pop()
    return len(stack) == 0 and not in_string
