import { describe, it, expect, beforeEach } from 'vitest';
import { StateMachine } from '../src/main/state/StateMachine.js';

describe('StateMachine', () => {
  let sm: StateMachine;

  beforeEach(() => {
    sm = new StateMachine();
  });

  it('initializes in IDLE state with a valid unique taskId', () => {
    const ctx = sm.getContext();
    expect(ctx.state).toBe('IDLE');
    expect(ctx.taskId).toBeDefined();
    expect(ctx.history.length).toBe(1);
    expect(ctx.history[0].state).toBe('IDLE');
  });

  it('starts a new task and transitions to ACTIVATING', () => {
    const ctx = sm.startNewTask();
    expect(ctx.state).toBe('ACTIVATING');
    expect(sm.getState()).toBe('ACTIVATING');
  });

  it('allows valid state progression: ACTIVATING -> CAPTURING -> GENERATING -> VALIDATING -> READY -> DELIVERING -> COMPLETED', () => {
    const ctx = sm.startNewTask();
    const taskId = ctx.taskId;

    expect(sm.transition('CAPTURING', taskId)).toBe(true);
    expect(sm.getState()).toBe('CAPTURING');

    expect(sm.transition('GENERATING', taskId, { updates: { questionText: 'Write binary search' } })).toBe(true);
    expect(sm.getState()).toBe('GENERATING');
    expect(sm.getContext().questionText).toBe('Write binary search');

    expect(sm.transition('VALIDATING', taskId, { updates: { generatedAnswer: 'def search(): pass' } })).toBe(true);
    expect(sm.getState()).toBe('VALIDATING');

    expect(sm.transition('READY', taskId)).toBe(true);
    expect(sm.getState()).toBe('READY');

    expect(sm.transition('DELIVERING', taskId)).toBe(true);
    expect(sm.getState()).toBe('DELIVERING');

    expect(sm.transition('COMPLETED', taskId)).toBe(true);
    expect(sm.getState()).toBe('COMPLETED');
  });

  it('rejects stale async tokens if taskId does not match current task', () => {
    const firstTask = sm.startNewTask();
    const firstTaskId = firstTask.taskId;

    // Start a newer task
    const secondTask = sm.startNewTask();
    const secondTaskId = secondTask.taskId;

    // Attempt transition using stale firstTaskId
    const success = sm.transition('CAPTURING', firstTaskId);
    expect(success).toBe(false);
    expect(sm.getTaskId()).toBe(secondTaskId);
  });

  it('rejects invalid state transitions according to formal state diagram', () => {
    const task = sm.startNewTask();
    // Cannot jump directly from ACTIVATING to COMPLETED
    const invalidJump = sm.transition('COMPLETED', task.taskId);
    expect(invalidJump).toBe(false);
    expect(sm.getState()).toBe('ACTIVATING');
  });

  it('preserves completed work (question, answer) during failure and recovery transitions', () => {
    const task = sm.startNewTask();
    const taskId = task.taskId;

    sm.transition('CAPTURING', taskId);
    sm.transition('GENERATING', taskId, { updates: { questionText: 'Reverse a linked list' } });
    sm.transition('VALIDATING', taskId, { updates: { generatedAnswer: 'class Node: pass' } });
    sm.transition('READY', taskId, { updates: { validatedAnswer: 'class Node: pass' } });

    // Delivery fails
    sm.transition('DELIVERY_RECOVERY', taskId, {
      message: 'Focus lost',
      error: 'FocusChangedError',
      errorCategory: 'FOCUS_CHANGED',
    });

    const ctx = sm.getContext();
    expect(ctx.state).toBe('DELIVERY_RECOVERY');
    // Crucial: completed question and answer must NOT be wiped out
    expect(ctx.questionText).toBe('Reverse a linked list');
    expect(ctx.validatedAnswer).toBe('class Node: pass');
  });

  it('aborts active AbortSignal upon cancellation', () => {
    const task = sm.startNewTask();
    const signal = sm.getAbortSignal();
    expect(signal.aborted).toBe(false);

    sm.cancel('User clicked cancel');
    expect(sm.getState()).toBe('CANCELLED');
    expect(signal.aborted).toBe(true);
  });
});
