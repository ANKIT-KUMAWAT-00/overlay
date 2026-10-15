import { TaskState, TaskContext, TaskStateEvent, ErrorCategory } from '../../shared/types.js';
import { EventEmitter } from 'events';
import crypto from 'crypto';

export type StateChangeListener = (context: Readonly<TaskContext>) => void;

export class StateMachine extends EventEmitter {
  private currentContext: TaskContext;
  private currentAbortController: AbortController | null = null;

  // Explicit valid state transitions
  private static readonly VALID_TRANSITIONS: Record<TaskState, TaskState[]> = {
    IDLE: ['ACTIVATING', 'PAUSED'],
    ACTIVATING: ['CAPTURING', 'FAILED', 'CANCELLED', 'IDLE'],
    CAPTURING: ['GENERATING', 'CAPTURE_RECOVERY', 'READY', 'FAILED', 'CANCELLED'],
    CAPTURE_RECOVERY: ['CAPTURING', 'GENERATING', 'FAILED', 'CANCELLED', 'READY'],
    GENERATING: ['VALIDATING', 'GENERATION_RECOVERY', 'FAILED', 'CANCELLED'],
    GENERATION_RECOVERY: ['GENERATING', 'VALIDATING', 'FAILED', 'CANCELLED'],
    VALIDATING: ['READY', 'GENERATION_RECOVERY', 'FAILED', 'CANCELLED'],
    READY: ['DELIVERING', 'DELIVERY_RECOVERY', 'COMPLETED', 'CANCELLED', 'IDLE', 'CAPTURING'],
    DELIVERING: ['COMPLETED', 'DELIVERY_RECOVERY', 'FAILED', 'CANCELLED'],
    DELIVERY_RECOVERY: ['DELIVERING', 'COMPLETED', 'FAILED', 'CANCELLED'],
    COMPLETED: ['IDLE', 'ACTIVATING'],
    PAUSED: ['IDLE', 'ACTIVATING'],
    CANCELLED: ['IDLE', 'ACTIVATING'],
    FAILED: ['IDLE', 'ACTIVATING', 'CAPTURING', 'GENERATING', 'DELIVERING'],
  };

  constructor() {
    super();
    this.currentContext = this.createInitialContext();
  }

  private createInitialContext(): TaskContext {
    const now = Date.now();
    return {
      taskId: crypto.randomUUID(),
      state: 'IDLE',
      createdAt: now,
      updatedAt: now,
      history: [{ state: 'IDLE', timestamp: now, message: 'Assistant initialized in IDLE state' }],
    };
  }

  public getContext(): Readonly<TaskContext> {
    return { ...this.currentContext };
  }

  public getState(): TaskState {
    return this.currentContext.state;
  }

  public getTaskId(): string {
    return this.currentContext.taskId;
  }

  public getAbortSignal(): AbortSignal {
    if (!this.currentAbortController) {
      this.currentAbortController = new AbortController();
    }
    return this.currentAbortController.signal;
  }

  public isCurrentTask(taskId: string): boolean {
    return this.currentContext.taskId === taskId;
  }

  /**
   * Starts a new task lifecycle, safely canceling any prior active task.
   */
  public startNewTask(): TaskContext {
    if (this.currentAbortController && !this.currentAbortController.signal.aborted) {
      this.currentAbortController.abort('New task started');
    }

    this.currentAbortController = new AbortController();
    const now = Date.now();
    this.currentContext = {
      taskId: crypto.randomUUID(),
      state: 'ACTIVATING',
      createdAt: now,
      updatedAt: now,
      history: [{ state: 'ACTIVATING', timestamp: now, message: 'New interaction activated' }],
    };

    this.emit('stateChange', this.getContext());
    return this.getContext();
  }

  /**
   * Transition to a new state with strict validation, task token verification,
   * and partial work preservation.
   */
  public transition(
    targetState: TaskState,
    taskId: string,
    metadata?: {
      message?: string;
      error?: string;
      errorCategory?: ErrorCategory;
      updates?: Partial<Omit<TaskContext, 'taskId' | 'state' | 'history' | 'createdAt'>>;
    }
  ): boolean {
    // 1. Stale token prevention: Reject transition if task ID does not match
    if (this.currentContext.taskId !== taskId) {
      console.warn(`[StateMachine] Rejected stale transition to ${targetState} for expired taskId: ${taskId} (current: ${this.currentContext.taskId})`);
      return false;
    }

    const currentState = this.currentContext.state;

    // 2. Allowed transitions check
    const allowed = StateMachine.VALID_TRANSITIONS[currentState] || [];
    if (!allowed.includes(targetState)) {
      console.error(`[StateMachine] Invalid state transition requested: ${currentState} -> ${targetState}`);
      return false;
    }

    const now = Date.now();
    const historyEvent: TaskStateEvent = {
      state: targetState,
      timestamp: now,
      message: metadata?.message,
      errorCategory: metadata?.errorCategory,
    };

    // 3. Update context while preserving existing completed work
    this.currentContext = {
      ...this.currentContext,
      ...(metadata?.updates || {}),
      state: targetState,
      updatedAt: now,
      error: metadata?.error ?? (targetState === 'FAILED' ? this.currentContext.error : undefined),
      errorCategory: metadata?.errorCategory ?? (targetState === 'FAILED' ? this.currentContext.errorCategory : undefined),
      history: [...this.currentContext.history, historyEvent],
    };

    // If terminal state, cancel controller
    if (targetState === 'CANCELLED' || targetState === 'COMPLETED' || targetState === 'FAILED') {
      if (this.currentAbortController && !this.currentAbortController.signal.aborted) {
        this.currentAbortController.abort(`Task entered terminal state ${targetState}`);
      }
    }

    this.emit('stateChange', this.getContext());
    return true;
  }

  /**
   * Explicitly cancel current task
   */
  public cancel(reason = 'User cancelled operation'): void {
    if (this.currentContext.state === 'IDLE' || this.currentContext.state === 'CANCELLED') {
      return;
    }
    this.transition('CANCELLED', this.currentContext.taskId, { message: reason });
  }

  /**
   * Reset back to IDLE
   */
  public resetToIdle(): void {
    const now = Date.now();
    this.currentContext = {
      ...this.currentContext,
      state: 'IDLE',
      updatedAt: now,
      history: [...this.currentContext.history, { state: 'IDLE', timestamp: now, message: 'Reset to IDLE' }],
    };
    this.emit('stateChange', this.getContext());
  }
}
