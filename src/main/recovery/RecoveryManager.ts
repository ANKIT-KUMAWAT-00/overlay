import {
  ErrorCategory,
  StructuredResult,
  CaptureMethod,
  DeliveryMethod,
} from '../../shared/types.js';
import { AssistantError } from '../../shared/errors.js';
import { RETRY_POLICY } from '../../shared/constants.js';

export interface RecoveryPlan {
  shouldRetry: boolean;
  delayMs: number;
  fallbackMethod?: string;
  actionDescription: string;
  isTerminal: boolean;
}

export class RecoveryManager {
  private retryCounts: Map<string, number> = new Map();

  /**
   * Classify any raw error into a well-defined ErrorCategory
   */
  public classifyError(error: unknown): ErrorCategory {
    if (error instanceof AssistantError) {
      return error.category;
    }

    if (error instanceof Error) {
      const msg = error.message.toLowerCase();
      if (msg.includes('network') || msg.includes('econnrefused') || msg.includes('fetch failed')) {
        return 'NETWORK_ERROR';
      }
      if (msg.includes('timeout') || msg.includes('etimedout')) {
        return 'TIMEOUT';
      }
      if (msg.includes('rate') || msg.includes('429') || msg.includes('quota') || msg.includes('resource_exhausted')) {
        return 'RATE_LIMIT';
      }
      if (msg.includes('permission') || msg.includes('access denied') || msg.includes('eacces')) {
        return 'PERMISSION_DENIED';
      }
      if (msg.includes('not found') || msg.includes('target')) {
        return 'TARGET_NOT_FOUND';
      }
      if (msg.includes('focus') || msg.includes('window changed')) {
        return 'FOCUS_CHANGED';
      }
      if (msg.includes('abort') || msg.includes('cancel')) {
        return 'CANCELLED';
      }
      if (msg.includes('json') || msg.includes('syntax') || msg.includes('parse')) {
        return 'INVALID_RESPONSE';
      }
      if (msg.includes('ocr') || msg.includes('tesseract')) {
        return 'OCR_FAILED';
      }
      if (msg.includes('empty') || msg.includes('capture')) {
        return 'CAPTURE_FAILED';
      }
    }

    return 'PERMANENT_FAILURE';
  }

  /**
   * Determine whether an error is eligible for automated retry.
   * Crucial safety rule: Operations that may have caused external side effects are NOT retried.
   */
  public isRetryable(category: ErrorCategory, hasPartialSideEffects: boolean): boolean {
    if (hasPartialSideEffects) {
      // Never blindly retry if an external side effect (e.g. partial keystrokes or partial form input) may have occurred!
      return false;
    }

    switch (category) {
      case 'NETWORK_ERROR':
      case 'TIMEOUT':
      case 'RATE_LIMIT':
      case 'CAPTURE_FAILED':
      case 'OCR_FAILED':
      case 'INVALID_RESPONSE':
        return true;
      case 'PERMISSION_DENIED':
      case 'INVALID_CONFIGURATION':
      case 'UNSUPPORTED_OPERATION':
      case 'TARGET_NOT_FOUND':
      case 'FOCUS_CHANGED':
      case 'PARTIAL_COMPLETION':
      case 'DUPLICATE_ACTION':
      case 'CANCELLED':
      case 'PERMANENT_FAILURE':
      default:
        return false;
    }
  }

  /**
   * Calculate bounded exponential backoff with jitter
   */
  public getBackoffDelay(attempt: number): number {
    const baseDelay = RETRY_POLICY.INITIAL_DELAY_MS * Math.pow(RETRY_POLICY.BACKOFF_MULTIPLIER, attempt);
    const jitter = Math.random() * 200;
    return Math.min(Math.round(baseDelay + jitter), RETRY_POLICY.MAX_DELAY_MS);
  }

  /**
   * Get fallback methods for Question Capture subsystem
   * Selected text -> accessibility -> adapter -> clipboard -> region OCR -> screen OCR -> manual entry
   */
  public getNextCaptureFallback(currentMethod: CaptureMethod): CaptureMethod | null {
    const sequence: CaptureMethod[] = [
      'selected_text',
      'accessibility',
      'adapter',
      'clipboard',
      'region_ocr',
      'screen_ocr',
      'document',
      'manual',
    ];
    const currentIndex = sequence.indexOf(currentMethod);
    if (currentIndex >= 0 && currentIndex < sequence.length - 1) {
      return sequence[currentIndex + 1];
    }
    return null;
  }

  /**
   * Get fallback methods for Answer Delivery subsystem
   * App API -> editor integration -> accessibility insertion -> keyboard simulation -> clipboard copy -> answer window
   */
  public getNextDeliveryFallback(currentMethod: DeliveryMethod): DeliveryMethod | null {
    const sequence: DeliveryMethod[] = [
      'app_api',
      'editor_integration',
      'accessibility_insertion',
      'keyboard_simulation',
      'clipboard_copy',
      'answer_window',
    ];
    const currentIndex = sequence.indexOf(currentMethod);
    if (currentIndex >= 0 && currentIndex < sequence.length - 1) {
      return sequence[currentIndex + 1];
    }
    return null;
  }

  /**
   * Build an actionable recovery plan for a failed operation
   */
  public planRecovery(
    taskId: string,
    operationName: string,
    error: unknown,
    hasPartialSideEffects = false,
    currentMethod?: string
  ): RecoveryPlan {
    const category = this.classifyError(error);
    const retryKey = `${taskId}:${operationName}`;
    const currentAttempt = this.retryCounts.get(retryKey) || 0;

    const canRetry = this.isRetryable(category, hasPartialSideEffects);

    if (canRetry && currentAttempt < RETRY_POLICY.MAX_ATTEMPTS) {
      const nextAttempt = currentAttempt + 1;
      this.retryCounts.set(retryKey, nextAttempt);
      const delay = this.getBackoffDelay(currentAttempt);

      return {
        shouldRetry: true,
        delayMs: delay,
        actionDescription: `Transient failure (${category}). Retrying attempt ${nextAttempt}/${RETRY_POLICY.MAX_ATTEMPTS} in ${delay}ms`,
        isTerminal: false,
      };
    }

    // Retries exhausted or non-retryable error: Discover fallbacks
    let fallbackMethod: string | undefined;

    if (operationName === 'CAPTURE' && currentMethod) {
      const next = this.getNextCaptureFallback(currentMethod as CaptureMethod);
      if (next) fallbackMethod = next;
    } else if (operationName === 'DELIVERY' && currentMethod) {
      const next = this.getNextDeliveryFallback(currentMethod as DeliveryMethod);
      if (next) fallbackMethod = next;
    }

    if (fallbackMethod) {
      return {
        shouldRetry: false,
        delayMs: 0,
        fallbackMethod,
        actionDescription: `Switching to safer alternative fallback method: ${fallbackMethod}`,
        isTerminal: false,
      };
    }

    // Exhausted all recoveries
    return {
      shouldRetry: false,
      delayMs: 0,
      actionDescription: `Recovery exhausted for ${operationName} (${category}). Preserving completed work and awaiting user review.`,
      isTerminal: true,
    };
  }

  /**
   * Create a structured result for an operation
   */
  public createStructuredResult<T = unknown>(params: {
    taskId: string;
    operationName: string;
    status: 'SUCCESS' | 'FAILED' | 'RECOVERED' | 'CANCELLED';
    error?: unknown;
    hasPartialSideEffects?: boolean;
    availableFallbackMethods?: string[];
    recoveryAction?: string;
    verificationStatus?: 'VERIFIED' | 'UNVERIFIED' | 'NOT_APPLICABLE';
    payload?: T;
  }): StructuredResult<T> {
    const failureCategory = params.error ? this.classifyError(params.error) : undefined;
    const retryEligibility = failureCategory
      ? this.isRetryable(failureCategory, params.hasPartialSideEffects ?? false)
      : false;

    return {
      taskId: params.taskId,
      operationName: params.operationName,
      status: params.status,
      failureCategory,
      retryEligibility,
      availableFallbackMethods: params.availableFallbackMethods || [],
      partialSideEffects: params.hasPartialSideEffects ?? false,
      recoveryAction: params.recoveryAction,
      verificationStatus: params.verificationStatus || 'NOT_APPLICABLE',
      payload: params.payload,
      error: params.error instanceof Error ? params.error.message : params.error ? String(params.error) : undefined,
    };
  }

  /**
   * Reset retry count for a specific task operation
   */
  public clearTask(taskId: string): void {
    for (const key of this.retryCounts.keys()) {
      if (key.startsWith(`${taskId}:`)) {
        this.retryCounts.delete(key);
      }
    }
  }
}
