"""
Unit tests for clipboard operations, target window verification, and answer delivery.
"""

import pytest
from delivery.clipboard_service import ClipboardService
from delivery.text_insertion import TextInsertionService, InsertionMethod
from delivery.answer_delivery import AnswerDeliveryCoordinator, DeliveryResult
from config.settings import AppSettings


def test_clipboard_service_copy_and_paste():
    clip = ClipboardService()
    test_content = "OmniAssist Clipboard Test 12345"
    success = clip.copy(test_content)
    if success:
        read_back = clip.paste()
        assert read_back == test_content


def test_text_insertion_methods():
    insertion = TextInsertionService()
    assert InsertionMethod.CLIPBOARD_PASTE.value == "clipboard_paste"
    assert InsertionMethod.SIMULATED_TYPING.value == "simulated_typing"
    # If the active window is OmniAssist itself, target verification should fail
    verified = insertion.verify_target_focus(expected_app_name="OmniAssist")
    assert not verified


def test_delivery_coordinator_empty_answer():
    coord = AnswerDeliveryCoordinator()
    result = coord.deliver("")
    assert isinstance(result, DeliveryResult)
    assert not result.success
    assert "empty" in (result.error_message or "").lower()


def test_delivery_coordinator_copy_flow():
    settings = AppSettings()
    settings.delivery.auto_copy_to_clipboard = True
    settings.delivery.auto_insert_to_active_app = False

    coord = AnswerDeliveryCoordinator(settings=settings)
    result = coord.deliver("Hello World Delivery", target_app="Terminal")
    assert isinstance(result, DeliveryResult)
    assert result.success
    assert result.copied_to_clipboard
    assert not result.inserted_to_app
