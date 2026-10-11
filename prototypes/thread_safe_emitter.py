"""Thread Safe Signal Dispatcher Spec."""

class SignalBridge:
    def emit_token(self, chunk: str):
        pass

    def emit_complete(self, full_text: str):
        pass

    def emit_error(self, code: str, msg: str):
        pass
