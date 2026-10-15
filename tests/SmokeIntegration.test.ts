import { describe, it, expect } from 'vitest';
import { StateMachine } from '../src/main/state/StateMachine.js';
import { RecoveryManager } from '../src/main/recovery/RecoveryManager.js';
import { SecurityManager } from '../src/main/security/SecurityManager.js';
import { CapabilityRegistry } from '../src/main/interaction/CapabilityRegistry.js';
import { ApplicationInteractionEngine } from '../src/main/interaction/ApplicationInteractionEngine.js';
import { AnswerValidationEngine } from '../src/main/validation/AnswerValidationEngine.js';
import { GeminiAnswerEngine } from '../src/main/ai/GeminiAnswerEngine.js';
import { AnswerDeliveryEngine } from '../src/main/delivery/AnswerDeliveryEngine.js';

describe('End-to-End Core Workflow Integration Smoke Test', () => {
  it('runs an end-to-end simulated interaction pipeline from activation to delivery and completion', async () => {
    // 1. Initialize all core engines
    const stateMachine = new StateMachine();
    const recoveryManager = new RecoveryManager();
    const securityManager = new SecurityManager('AIzaSyMockKeyForSmokeTest1234567890abcdef');
    const capabilityRegistry = new CapabilityRegistry();
    const interactionEngine = new ApplicationInteractionEngine(capabilityRegistry);
    const validationEngine = new AnswerValidationEngine();
    const geminiEngine = new GeminiAnswerEngine(securityManager.getApiKey());
    const deliveryEngine = new AnswerDeliveryEngine(interactionEngine);

    // Mock clipboard access for headless test runner
    (interactionEngine.resolveAdapter as any) = () => ({
      copyToClipboard: async () => true,
      insertText: async () => ({ success: true, verified: true, deliveryMethodUsed: 'editor_integration' }),
    });

    // 2. Start Task (ACTIVATING)
    const task = stateMachine.startNewTask();
    const taskId = task.taskId;
    expect(stateMachine.getState()).toBe('ACTIVATING');

    // 3. CAPTURING
    stateMachine.transition('CAPTURING', taskId);
    expect(stateMachine.getState()).toBe('CAPTURING');

    // Simulate captured question
    const rawQuestion = 'Write a Python function to check if a string is a palindrome.';
    const sanitized = securityManager.sanitizeCapturedContent(rawQuestion);
    expect(sanitized.injectionDetected).toBe(false);

    // 4. GENERATING
    const detectedFormat = geminiEngine.detectQuestionFormat(sanitized.sanitizedText, 'ide');
    expect(detectedFormat).toBe('code');

    stateMachine.transition('GENERATING', taskId, {
      updates: {
        questionText: sanitized.sanitizedText,
        capturedVia: 'selected_text',
        questionFormat: detectedFormat,
      },
    });
    expect(stateMachine.getState()).toBe('GENERATING');

    // Simulate Gemini generation output
    const mockAnswer = 'def is_palindrome(s: str) -> bool:\n    clean = "".join(c.lower() for c in s if c.isalnum())\n    return clean == clean[::-1]';

    // 5. VALIDATING
    stateMachine.transition('VALIDATING', taskId, {
      updates: { generatedAnswer: mockAnswer },
    });
    expect(stateMachine.getState()).toBe('VALIDATING');

    const validation = validationEngine.validate(mockAnswer, detectedFormat, {
      requiredSignature: 'def is_palindrome',
    });
    expect(validation.isValid).toBe(true);

    // 6. READY
    stateMachine.transition('READY', taskId, {
      updates: { validatedAnswer: mockAnswer },
    });
    expect(stateMachine.getState()).toBe('READY');

    // 7. DELIVERING (Clipboard delivery simulation)
    stateMachine.transition('DELIVERING', taskId);
    expect(stateMachine.getState()).toBe('DELIVERING');

    const outcome = await deliveryEngine.deliverAnswer({
      taskId,
      answer: mockAnswer,
      preferredMethod: 'clipboard_copy',
    });
    expect(outcome.delivered).toBe(true);
    expect(outcome.clipboardReady).toBe(true);

    // 8. COMPLETED
    stateMachine.transition('COMPLETED', taskId, {
      updates: {
        deliveredVia: outcome.methodUsed,
        deliveryVerified: outcome.verification.verified,
      },
    });
    expect(stateMachine.getState()).toBe('COMPLETED');

    const finalCtx = stateMachine.getContext();
    expect(finalCtx.questionText).toBe(rawQuestion);
    expect(finalCtx.validatedAnswer).toBe(mockAnswer);
    expect(finalCtx.deliveredVia).toBe('clipboard_copy');
    expect(finalCtx.history.length).toBeGreaterThanOrEqual(6);
  });
});
