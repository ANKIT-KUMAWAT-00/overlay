"""
Core orchestration, application intelligence, and recovery subsystems for OmniAssist.
"""

from .application_detector import ApplicationDetector, AppCategory, DetectedApplication
from .capability_registry import CapabilityRegistry, AppCapabilities
from .recovery_manager import RecoveryManager, ErrorCategory, RecoveryAction
from .orchestrator import AssistantOrchestrator

__all__ = [
    "ApplicationDetector",
    "AppCategory",
    "DetectedApplication",
    "CapabilityRegistry",
    "AppCapabilities",
    "RecoveryManager",
    "ErrorCategory",
    "RecoveryAction",
    "AssistantOrchestrator",
]
