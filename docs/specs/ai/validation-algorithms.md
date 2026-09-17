# Token Truncation & Delimiter Balancing Specification

## Delimiter Balance Invariant
All delivered source code must satisfy delimiter parity:
- Parentheses `()` count match
- Square brackets `[]` count match
- Curly braces `{}` count match
- Quotes `"` and `'` parity check (excluding escaped sequences)
