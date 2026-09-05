# Application Adapter Interface Specification

Adapters represent target environments (browsers, editors, terminals) with declared capabilities:

```python
class ApplicationAdapter(ABC):
    @abstractmethod
    def can_handle(self, process_name: str, window_title: str) -> bool: ...

    @abstractmethod
    def get_capabilities(self) -> Set[AdapterCapability]: ...

    @abstractmethod
    def extract_context(self) -> Optional[CaptureContext]: ...

    @abstractmethod
    def insert_text(self, text: str) -> bool: ...
```

## Capability Flags
- `SUPPORTS_DIRECT_PASTE`
- `SUPPORTS_KEYSTROKE_SIMULATION`
- `SUPPORTS_ACCESSIBILITY_READ`
- `REQUIRES_CLIPBOARD_RESTORE`
