import { describe, it, expect, beforeEach } from 'vitest';
import { GeminiAnswerEngine } from '../src/main/ai/GeminiAnswerEngine.js';
import { InvalidConfigurationError, AssistantError } from '../src/shared/errors.js';

describe('GeminiAnswerEngine', () => {
  let engine: GeminiAnswerEngine;

  beforeEach(() => {
    engine = new GeminiAnswerEngine();
  });

  it('correctly infers output format from questions and context', () => {
    expect(engine.detectQuestionFormat('Which of the following is an immutable type?\nA) list\nB) tuple\nC) dict')).toBe('mcq');
    expect(engine.detectQuestionFormat('SELECT count(*) FROM orders GROUP BY user_id')).toBe('sql');
    expect(engine.detectQuestionFormat('Convert this schema to valid JSON')).toBe('json');
    expect(engine.detectQuestionFormat('TypeError: undefined is not a function at line 14')).toBe('debug');
    expect(engine.detectQuestionFormat('Write a function in typescript to reverse a string')).toBe('code');
    expect(engine.detectQuestionFormat('Explain the difference between TCP and UDP in 2 sentences')).toBe('paragraph');
    expect(engine.detectQuestionFormat('hi')).toBe('clarification');
  });

  it('rejects generation if API key is unconfigured', async () => {
    await expect(
      engine.generateAnswer({
        taskId: 'test-task',
        question: 'Solve two sum',
      })
    ).rejects.toThrow(InvalidConfigurationError);
  });

  it('prevents duplicate generation requests for the same taskId in-flight', async () => {
    engine.setApiKey('AIzaSyFakeKeyForTest1234567890abcdefghijklm');

    // Mock client generateContent
    (engine as any).client = {
      models: {
        generateContent: () => new Promise((resolve) => setTimeout(() => resolve({ text: 'Answer' }), 100)),
      },
    };

    const promise1 = engine.generateAnswer({ taskId: 'duplicate-check', question: 'q1' });
    // Second concurrent call with same taskId must be rejected as duplicate
    await expect(
      engine.generateAnswer({ taskId: 'duplicate-check', question: 'q1' })
    ).rejects.toThrow(AssistantError);

    await promise1;
  });

  it('respects AbortSignal cancellation', async () => {
    engine.setApiKey('AIzaSyFakeKeyForTest1234567890abcdefghijklm');

    const controller = new AbortController();
    controller.abort();

    await expect(
      engine.generateAnswer({
        taskId: 'cancel-test',
        question: 'test question',
        abortSignal: controller.signal,
      })
    ).rejects.toThrow();
  });
});
