export type TaskState =
  | 'IDLE'
  | 'ACTIVATING'
  | 'CAPTURING'
  | 'CAPTURE_RECOVERY'
  | 'GENERATING'
  | 'GENERATION_RECOVERY'
  | 'VALIDATING'
  | 'READY'
  | 'DELIVERING'
  | 'DELIVERY_RECOVERY'
  | 'COMPLETED'
  | 'PAUSED'
  | 'CANCELLED'
  | 'FAILED';

export type ErrorCategory =
  | 'NETWORK_ERROR'
  | 'TIMEOUT'
  | 'RATE_LIMIT'
  | 'INVALID_CONFIGURATION'
  | 'PERMISSION_DENIED'
  | 'UNSUPPORTED_OPERATION'
  | 'CAPTURE_FAILED'
  | 'OCR_FAILED'
  | 'TARGET_NOT_FOUND'
  | 'FOCUS_CHANGED'
  | 'INVALID_RESPONSE'
  | 'PARTIAL_COMPLETION'
  | 'DUPLICATE_ACTION'
  | 'CANCELLED'
  | 'PERMANENT_FAILURE';

export enum InteractionLayer {
  OFFICIAL_API = 1,
  APP_ADAPTER = 2,
  BROWSER_EXTENSION = 3,
  ACCESSIBILITY_API = 4,
  DOM_INTERACTION = 5,
  SCRIPTING_INTERFACE = 6,
  SCREEN_CAPTURE_OCR = 7,
  KEYBOARD_MOUSE_SIM = 8,
  CLIPBOARD_TRANSFER = 9,
  MANUAL_GUIDANCE = 10,
}

export type CaptureMethod =
  | 'selected_text'
  | 'accessibility'
  | 'clipboard'
  | 'adapter'
  | 'region_ocr'
  | 'screen_ocr'
  | 'document'
  | 'manual';

export type DeliveryMethod =
  | 'app_api'
  | 'editor_integration'
  | 'accessibility_insertion'
  | 'keyboard_simulation'
  | 'clipboard_copy'
  | 'answer_window';

export type AnswerFormat =
  | 'code'
  | 'paragraph'
  | 'mcq'
  | 'sql'
  | 'json'
  | 'table'
  | 'math'
  | 'debug'
  | 'clarification';

export interface VerificationResult {
  verified: boolean;
  reason?: string;
  evidence?: string;
}

export interface StructuredResult<T = unknown> {
  taskId: string;
  operationName: string;
  status: 'SUCCESS' | 'FAILED' | 'RECOVERED' | 'CANCELLED';
  failureCategory?: ErrorCategory;
  retryEligibility: boolean;
  availableFallbackMethods: string[];
  partialSideEffects: boolean;
  recoveryAction?: string;
  verificationStatus: 'VERIFIED' | 'UNVERIFIED' | 'NOT_APPLICABLE';
  payload?: T;
  error?: string;
}

export type AppCategory = 'browser' | 'ide' | 'office' | 'communication' | 'generic';

export interface TargetApplication {
  bundleId?: string;
  appName: string;
  windowTitle: string;
  processId: number;
  isFocused: boolean;
  category: AppCategory;
  url?: string;
  filePath?: string;
}

export interface ApplicationPermissions {
  screenRecording: boolean;
  accessibility: boolean;
  automation: boolean;
}

export type HealthStatus = 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE';

export type SupportedOperation =
  | 'READ_SELECTION'
  | 'READ_CONTENT'
  | 'INSERT_TEXT'
  | 'COPY_CLIPBOARD'
  | 'NAVIGATE'
  | 'EXECUTE_WORKFLOW';

export interface ApplicationCapability {
  appId: string;
  appName: string;
  os: 'darwin' | 'win32' | 'linux';
  supportedInteractionMethods: InteractionLayer[];
  availablePermissions: ApplicationPermissions;
  knownLimitations: string[];
  adapterVersion: string;
  healthStatus: HealthStatus;
  supportedOperations: SupportedOperation[];
  lastCheck: number;
}

export interface AssistantSettings {
  geminiApiKey: string;
  modelName: string;
  activationShortcut: string;
  insertionShortcut: string;
  startupAtLogin: boolean;
  enableHistory: boolean;
  maxRetryAttempts: number;
  retryTimeoutMs: number;
  preferredCaptureMethod: CaptureMethod;
  preferredDeliveryMethod: DeliveryMethod;
  privacyMode: boolean;
}

export interface TaskStateEvent {
  state: TaskState;
  timestamp: number;
  message?: string;
  errorCategory?: ErrorCategory;
}

export interface TaskContext {
  taskId: string;
  state: TaskState;
  createdAt: number;
  updatedAt: number;
  targetApp?: TargetApplication;
  questionText?: string;
  capturedVia?: CaptureMethod;
  questionFormat?: AnswerFormat;
  codeLanguage?: string;
  generatedAnswer?: string;
  validatedAnswer?: string;
  deliveredVia?: DeliveryMethod;
  deliveryVerified?: boolean;
  error?: string;
  errorCategory?: ErrorCategory;
  history: TaskStateEvent[];
}

export interface CaptureOptions {
  preferredMethod?: CaptureMethod;
  region?: { x: number; y: number; width: number; height: number };
  allowManualFallback?: boolean;
  timeoutMs?: number;
}

export interface ValidationIssue {
  type: 'syntax' | 'truncation' | 'empty' | 'signature' | 'format';
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationResult {
  isValid: boolean;
  detectedFormat: AnswerFormat;
  issues: ValidationIssue[];
  cleanedOutput?: string;
  requiresCorrection: boolean;
}
