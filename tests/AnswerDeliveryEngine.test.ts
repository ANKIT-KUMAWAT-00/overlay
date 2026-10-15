import { describe, it, expect, beforeEach } from 'vitest';
import { AnswerDeliveryEngine } from '../src/main/delivery/AnswerDeliveryEngine.js';
import { FocusChangedError, AssistantError } from '../src/shared/errors.js';
import { TargetApplication } from '../src/shared/types.js';

describe('AnswerDeliveryEngine', () => {
  let delivery: AnswerDeliveryEngine;

  beforeEach(() => {
    delivery = new AnswerDeliveryEngine();
  });

  it('detects target focus changes and raises FocusChangedError', async () => {
    const originalTarget: TargetApplication = {
      appName: 'Original App',
      windowTitle: 'Original Window',
      processId: 101,
      isFocused: true,
      category: 'ide',
    };

    // Mock getActiveTarget returning a different app
    (delivery as any).interactionEngine = {
      getActiveTarget: async () => ({
        appName: 'Different Browser Window',
        windowTitle: 'YouTube',
        processId: 202,
        isFocused: true,
        category: 'browser',
      }),
    };

    await expect(
      delivery.deliverAnswer({
        taskId: 'focus-check-task',
        answer: 'print("hello")',
        targetApp: originalTarget,
      })
    ).rejects.toThrow(FocusChangedError);
  });

  it('prevents duplicate delivery for the same task', async () => {
    const target: TargetApplication = {
      appName: 'Active Desktop Application',
      windowTitle: 'Active Window',
      processId: 0,
      isFocused: true,
      category: 'generic',
    };

    (delivery as any).interactionEngine = {
      getActiveTarget: async () => target,
      resolveAdapter: () => ({
        copyToClipboard: async () => true,
      }),
      insertAnswer: async () => ({ success: true, verified: true }),
    };

    const first = await delivery.deliverAnswer({
      taskId: 'dup-task-1',
      answer: 'answer 1',
      preferredMethod: 'clipboard_copy',
    });
    expect(first.delivered).toBe(true);

    // Duplicate call for dup-task-1 must throw duplicate action error
    await expect(
      delivery.deliverAnswer({
        taskId: 'dup-task-1',
        answer: 'answer 1',
      })
    ).rejects.toThrow(AssistantError);
  });

  it('automatically falls back to clipboard when direct insertion fails', async () => {
    const target: TargetApplication = {
      appName: 'Protected App',
      windowTitle: 'Doc',
      processId: 12,
      isFocused: true,
      category: 'generic',
    };

    (delivery as any).interactionEngine = {
      getActiveTarget: async () => target,
      resolveAdapter: () => ({
        copyToClipboard: async () => true,
        insertText: async () => ({ success: false, verified: false, error: 'Target field is read-only' }),
      }),
      insertAnswer: async () => ({ success: false, verified: false, error: 'Target field is read-only' }),
    };

    const outcome = await delivery.deliverAnswer({
      taskId: 'fallback-task',
      answer: 'generated content',
      preferredMethod: 'accessibility_insertion',
    });

    expect(outcome.delivered).toBe(true);
    expect(outcome.methodUsed).toBe('clipboard_copy');
    expect(outcome.clipboardReady).toBe(true);
  });
});
