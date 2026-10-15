export const DEFAULT_SHORTCUTS = {
  darwin: {
    activation: 'Command+Shift+Z',
    alternativeActivation: 'Alt+Shift+Z',
    insertion: 'Alt+Enter',
    cancel: 'Escape',
  },
  win32: {
    activation: 'Ctrl+Shift+Z',
    alternativeActivation: 'Alt+Shift+Z',
    insertion: 'Alt+Enter',
    cancel: 'Escape',
  },
  linux: {
    activation: 'Ctrl+Shift+Z',
    alternativeActivation: 'Alt+Shift+Z',
    insertion: 'Alt+Enter',
    cancel: 'Escape',
  },
};

export const GEMINI_MODELS = {
  DEFAULT: 'gemini-2.5-flash',
  PRO: 'gemini-2.5-pro',
  FAST_FALLBACK: 'gemini-2.0-flash',
  AVAILABLE: [
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-2.0-flash',
  ],
};

export const TIMEOUTS = {
  ACTIVATION_MS: 3000,
  CAPTURE_MS: 10000,
  OCR_MS: 15000,
  GENERATION_MS: 35000,
  VALIDATION_MS: 5000,
  DELIVERY_MS: 8000,
  CORRECTION_MS: 20000,
};

export const RETRY_POLICY = {
  MAX_ATTEMPTS: 3,
  INITIAL_DELAY_MS: 600,
  BACKOFF_MULTIPLIER: 1.8,
  MAX_DELAY_MS: 4000,
};

export const STORAGE_KEYS = {
  SETTINGS: 'assistant_settings_v1',
  TASK_HISTORY: 'assistant_task_history_v1',
};
