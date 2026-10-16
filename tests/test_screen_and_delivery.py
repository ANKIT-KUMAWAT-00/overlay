"""
Unit and integration tests for screen photo capture, multimodal vision dispatch, and Option+Enter delivery.
"""

import pytest
from unittest.mock import MagicMock, patch
from capture.question_capture import QuestionCaptureService, CaptureMethod, CapturedQuestion
from core.orchestrator import AssistantOrchestrator
from delivery.answer_delivery import AnswerDeliveryCoordinator, DeliveryResult
from ai.provider import AIResponse, OutputFormat


def test_smart_capture_defaults_to_vision_when_no_selection():
    """Verify SMART capture takes fullscreen screenshot when no text is selected."""
    mock_platform = MagicMock()
    mock_platform.get_active_app_info.return_value = {"app_name": "Google Chrome", "window_title": "Exam Tab"}
    mock_platform.get_selected_text_via_clipboard.return_value = None

    mock_screen = MagicMock()
    mock_screen.capture_fullscreen.return_value = MagicMock()
    mock_screen.image_to_bytes.return_value = b"\xff\xd8\xff\xe0mockjpegbytes"

    mock_acc = MagicMock()
    mock_acc.capture_focused_text.return_value = (None, "AXUnknown")

    service = QuestionCaptureService(
        screen_capture=mock_screen,
        accessibility=mock_acc,
    )
    service.platform = mock_platform

    captured = service.capture(method=CaptureMethod.SMART, include_vision=True)

    assert captured.has_content
    assert captured.method == CaptureMethod.FULLSCREEN_VISION
    assert captured.image_bytes == b"\xff\xd8\xff\xe0mockjpegbytes"
    assert captured.source_app == "Google Chrome"
    assert "screen" in captured.text.lower()


def test_orchestrator_handles_screen_image_bytes():
    """Verify orchestrator properly receives screen image bytes and dispatches to Gemini."""
    mock_ai = MagicMock()
    mock_ai.model_name = "gemini-3-flash-preview"
    mock_ai.generate_answer.return_value = AIResponse(
        text="Option (B) is the correct answer.",
        model="gemini-3-flash-preview",
        finish_reason="STOP",
        output_format=OutputFormat.SHORT_ANSWER,
        is_success=True,
    )

    orchestrator = AssistantOrchestrator(ai_provider=mock_ai)
    test_img = b"fakejpegdata"

    thread = orchestrator.run_interaction_async(
        method=CaptureMethod.FULLSCREEN_VISION,
        image_bytes=test_img,
        format_preference=OutputFormat.SHORT_ANSWER,
    )
    thread.join(timeout=5.0)

    # Verify AI provider was called with image bytes
    mock_ai.generate_answer.assert_called_once()
    call_kwargs = mock_ai.generate_answer.call_args[1]
    assert call_kwargs["image_bytes"] == test_img
    assert call_kwargs["image_mime_type"] == "image/jpeg"
    assert orchestrator.last_generated_answer == "Option (B) is the correct answer."


def test_force_insert_delivery_pastes_into_target():
    """Verify force_insert passes through focus verification and executes paste."""
    mock_platform = MagicMock()
    mock_platform.get_active_app_info.return_value = {"app_name": "Visual Studio Code", "window_title": "app.py"}
    mock_platform.insert_text.return_value = True

    mock_clip = MagicMock()
    mock_clip.copy.return_value = True

    coord = AnswerDeliveryCoordinator()
    coord.clipboard = mock_clip
    coord.insertion.platform = mock_platform
    coord.insertion.clipboard = mock_clip

    result = coord.deliver(
        answer_text="def solution(): return 42",
        target_app="Visual Studio Code",
        force_insert=True,
    )

    assert result.success
    assert result.inserted_to_app
    mock_platform.insert_text.assert_called_once()
