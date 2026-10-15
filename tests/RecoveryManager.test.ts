import { describe, it, expect, beforeEach } from 'vitest';
import { RecoveryManager } from '../src/main/recovery/RecoveryManager.js';
import { NetworkError, TimeoutError, RateLimitError, PermissionDeniedError, FocusChangedError } from '../src/shared/errors.js';

describe('RecoveryManager', () => {
  let rm: RecoveryManager;

  beforeEach(() => {
    rm = new RecoveryManager();
  });

  it('correctly classifies typed and raw errors into standard ErrorCategory values', () => {
    expect(rm.classifyError(new NetworkError())).toBe('NETWORK_ERROR');
    expect(rm.classifyError(new TimeoutError('capture', 5000))).toBe('TIMEOUT');
    expect(rm.classifyError(new RateLimitError())).toBe('RATE_LIMIT');
    expect(rm.classifyError(new PermissionDeniedError('screenRecording'))).toBe('PERMISSION_DENIED');
    expect(rm.classifyError(new FocusChangedError('Code', 'Chrome'))).toBe('FOCUS_CHANGED');

    // Raw error messages
    expect(rm.classifyError(new Error('fetch failed ECONNREFUSED'))).toBe('NETWORK_ERROR');
    expect(rm.classifyError(new Error('429 Resource has been exhausted (e.g. check quota)'))).toBe('RATE_LIMIT');
    expect(rm.classifyError(new Error('Tesseract failed to load lang'))).toBe('OCR_FAILED');
  });

  it('prohibits retries if partial side effects may have occurred', () => {
    // Even if error is transient (e.g. TIMEOUT), if side effects happened, retry must be blocked
    expect(rm.isRetryable('TIMEOUT', true)).toBe(false);
    expect(rm.isRetryable('TIMEOUT', false)).toBe(true);
    expect(rm.isRetryable('PERMISSION_DENIED', false)).toBe(false);
    expect(rm.isRetryable('FOCUS_CHANGED', false)).toBe(false);
  });

  it('calculates bounded exponential backoff with jitter', () => {
    const delay0 = rm.getBackoffDelay(0);
    const delay1 = rm.getBackoffDelay(1);
    const delay2 = rm.getBackoffDelay(2);

    expect(delay0).toBeGreaterThanOrEqual(600);
    expect(delay1).toBeGreaterThan(delay0 - 200);
    expect(delay2).toBeLessThanOrEqual(4000);
  });

  it('provides ordered capture fallbacks', () => {
    expect(rm.getNextCaptureFallback('selected_text')).toBe('accessibility');
    expect(rm.getNextCaptureFallback('accessibility')).toBe('adapter');
    expect(rm.getNextCaptureFallback('adapter')).toBe('clipboard');
    expect(rm.getNextCaptureFallback('clipboard')).toBe('region_ocr');
    expect(rm.getNextCaptureFallback('region_ocr')).toBe('screen_ocr');
    expect(rm.getNextCaptureFallback('screen_ocr')).toBe('document');
    expect(rm.getNextCaptureFallback('document')).toBe('manual');
    expect(rm.getNextCaptureFallback('manual')).toBeNull();
  });

  it('provides ordered delivery fallbacks', () => {
    expect(rm.getNextDeliveryFallback('app_api')).toBe('editor_integration');
    expect(rm.getNextDeliveryFallback('editor_integration')).toBe('accessibility_insertion');
    expect(rm.getNextDeliveryFallback('accessibility_insertion')).toBe('keyboard_simulation');
    expect(rm.getNextDeliveryFallback('keyboard_simulation')).toBe('clipboard_copy');
    expect(rm.getNextDeliveryFallback('clipboard_copy')).toBe('answer_window');
    expect(rm.getNextDeliveryFallback('answer_window')).toBeNull();
  });

  it('handles bounded retries and recovery exhaustion gracefully', () => {
    const taskId = 'task-test-123';
    const err = new NetworkError();

    // Attempts 1, 2, 3 should suggest retry
    const plan1 = rm.planRecovery(taskId, 'GENERATION', err);
    expect(plan1.shouldRetry).toBe(true);

    const plan2 = rm.planRecovery(taskId, 'GENERATION', err);
    expect(plan2.shouldRetry).toBe(true);

    const plan3 = rm.planRecovery(taskId, 'GENERATION', err);
    expect(plan3.shouldRetry).toBe(true);

    // Attempt 4 should exhaust retries and enter terminal state
    const plan4 = rm.planRecovery(taskId, 'GENERATION', err);
    expect(plan4.shouldRetry).toBe(false);
    expect(plan4.isTerminal).toBe(true);
    expect(plan4.actionDescription).toContain('Recovery exhausted');
  });
});
