# End-to-End User Journey Map

1. **Trigger**: User presses `Option+Space` inside VS Code while viewing a LeetCode problem.
2. **Context Ingestion**: OmniAssist captures editor text and frontmost window title.
3. **Synthesis**: Gemini 2.5 synthesizes Python solution with clean type hints.
4. **Validation**: AST parser verifies syntax validity.
5. **HUD Preview**: Solution displays with green verified badge in floating HUD.
6. **Delivery**: User presses `Option+Enter`, pasting clean code into VS Code editor.
