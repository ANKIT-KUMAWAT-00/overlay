import { ErrorCategory } from './types.js';

export class AssistantError extends Error {
  public readonly category: ErrorCategory;
  public readonly retryable: boolean;
  public readonly partialSideEffects: boolean;
  public readonly recoveryAction?: string;
  public readonly originalError?: unknown;

  constructor(
    message: string,
    options: {
      category: ErrorCategory;
      retryable?: boolean;
      partialSideEffects?: boolean;
      recoveryAction?: string;
      originalError?: unknown;
    }
  ) {
    super(message);
    this.name = 'AssistantError';
    this.category = options.category;
    this.retryable = options.retryable ?? false;
    this.partialSideEffects = options.partialSideEffects ?? false;
    this.recoveryAction = options.recoveryAction;
    this.originalError = options.originalError;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class NetworkError extends AssistantError {
  constructor(message = 'Network connectivity failure while communicating with AI service', originalError?: unknown) {
    super(message, {
      category: 'NETWORK_ERROR',
      retryable: true,
      recoveryAction: 'Retry request with exponential backoff or switch to alternative network',
      originalError,
    });
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends AssistantError {
  constructor(operation: string, timeoutMs: number) {
    super(`Operation '${operation}' timed out after ${timeoutMs}ms`, {
      category: 'TIMEOUT',
      retryable: true,
      recoveryAction: 'Retry with increased timeout or simpler context',
    });
    this.name = 'TimeoutError';
  }
}

export class RateLimitError extends AssistantError {
  constructor(message = 'Gemini API rate limit exceeded', originalError?: unknown) {
    super(message, {
      category: 'RATE_LIMIT',
      retryable: true,
      recoveryAction: 'Wait for quota window reset or switch to fallback model',
      originalError,
    });
    this.name = 'RateLimitError';
  }
}

export class InvalidConfigurationError extends AssistantError {
  constructor(detail: string) {
    super(`Configuration error: ${detail}`, {
      category: 'INVALID_CONFIGURATION',
      retryable: false,
      recoveryAction: 'Open settings and configure valid API key and shortcuts',
    });
    this.name = 'InvalidConfigurationError';
  }
}

export class PermissionDeniedError extends AssistantError {
  constructor(permission: 'screenRecording' | 'accessibility' | 'automation') {
    super(`OS permission '${permission}' is not granted`, {
      category: 'PERMISSION_DENIED',
      retryable: false,
      recoveryAction: `Grant ${permission} permission in OS System Settings > Privacy & Security`,
    });
    this.name = 'PermissionDeniedError';
  }
}

export class CaptureFailedError extends AssistantError {
  constructor(reason: string, originalError?: unknown) {
    super(`Question capture failed: ${reason}`, {
      category: 'CAPTURE_FAILED',
      retryable: true,
      recoveryAction: 'Fall back to clipboard capture or manual input modal',
      originalError,
    });
    this.name = 'CaptureFailedError';
  }
}

export class TargetNotFoundError extends AssistantError {
  constructor(appName?: string) {
    super(`Target application '${appName || 'unknown'}' could not be identified or reached`, {
      category: 'TARGET_NOT_FOUND',
      retryable: false,
      recoveryAction: 'Activate the target window and trigger assistant again',
    });
    this.name = 'TargetNotFoundError';
  }
}

export class FocusChangedError extends AssistantError {
  constructor(originalApp: string, currentApp: string) {
    super(`Target application focus changed from '${originalApp}' to '${currentApp}'`, {
      category: 'FOCUS_CHANGED',
      retryable: false,
      recoveryAction: 'Refocus target application or copy answer to clipboard manually',
    });
    this.name = 'FocusChangedError';
  }
}

export class InvalidResponseError extends AssistantError {
  constructor(reason: string) {
    super(`AI answer validation failed: ${reason}`, {
      category: 'INVALID_RESPONSE',
      retryable: true,
      recoveryAction: 'Trigger bounded correction cycle with syntax feedback',
    });
    this.name = 'InvalidResponseError';
  }
}
