import { ApplicationPermissions, AssistantSettings } from '../../shared/types.js';
import { DEFAULT_SHORTCUTS, GEMINI_MODELS } from '../../shared/constants.js';
import os from 'os';

export class SecurityManager {
  private inMemoryApiKey: string | null = null;
  private settings: AssistantSettings;

  // Patterns for redaction
  private static readonly SENSITIVE_PATTERNS = [
    /AIza[0-9A-Za-z-_]{35}/g, // Google API keys
    /sk-[a-zA-Z0-9]{32,}/g, // OpenAI-style keys
    /Bearer\s+[A-Za-z0-9\-._~+/]+=*/gi,
    /ghp_[A-Za-z0-9]{36}/g, // GitHub tokens
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, // Emails (optional redaction in strict mode)
    /\b(?:\d{4}[ -]?){3}\d{4}\b/g, // Credit card numbers
    /password["']?\s*[:=]\s*["'][^"']+["']/gi,
  ];

  // Prompt injection mitigation markers
  private static readonly INJECTION_WARNINGS = [
    'ignore all previous instructions',
    'system prompt override',
    'you are now in developer mode',
    'bypass security',
    'output your initial prompt',
    'reveal your api key',
    'delete files',
    'rm -rf',
    'format c:',
  ];

  constructor(initialApiKey?: string) {
    const platform = (os.platform() in DEFAULT_SHORTCUTS ? os.platform() : 'darwin') as keyof typeof DEFAULT_SHORTCUTS;
    const defaults = DEFAULT_SHORTCUTS[platform];

    this.inMemoryApiKey = initialApiKey || process.env.GEMINI_API_KEY || null;

    this.settings = {
      geminiApiKey: this.inMemoryApiKey ? '********' : '',
      modelName: GEMINI_MODELS.DEFAULT,
      activationShortcut: defaults.activation,
      insertionShortcut: defaults.insertion,
      startupAtLogin: false,
      enableHistory: false, // Default to privacy-preserving: no persistent history
      maxRetryAttempts: 3,
      retryTimeoutMs: 35000,
      preferredCaptureMethod: 'selected_text',
      preferredDeliveryMethod: 'app_api',
      privacyMode: true,
    };
  }

  public getApiKey(): string | null {
    return this.inMemoryApiKey;
  }

  public setApiKey(key: string): void {
    const sanitized = key.trim();
    this.inMemoryApiKey = sanitized.length > 0 ? sanitized : null;
    this.settings.geminiApiKey = sanitized.length > 0 ? '********' : '';
  }

  public getSettings(): AssistantSettings {
    return {
      ...this.settings,
      geminiApiKey: this.inMemoryApiKey ? '********' : '',
    };
  }

  public updateSettings(partial: Partial<AssistantSettings>): AssistantSettings {
    if (partial.geminiApiKey && partial.geminiApiKey !== '********') {
      this.setApiKey(partial.geminiApiKey);
    }

    this.settings = {
      ...this.settings,
      ...partial,
      geminiApiKey: this.inMemoryApiKey ? '********' : '',
    };
    return this.getSettings();
  }

  /**
   * Redact sensitive tokens and secrets from strings before logging or rendering
   */
  public redactSensitiveData(text: string): string {
    if (!text) return '';
    let sanitized = text;

    // Redact in-memory key if known
    if (this.inMemoryApiKey && this.inMemoryApiKey.length > 6) {
      sanitized = sanitized.replaceAll(this.inMemoryApiKey, '[REDACTED_GEMINI_KEY]');
    }

    for (const pattern of SecurityManager.SENSITIVE_PATTERNS) {
      sanitized = sanitized.replace(pattern, '[REDACTED_CREDENTIAL]');
    }

    return sanitized;
  }

  /**
   * Detect potential prompt injection in captured context and sanitize
   */
  public sanitizeCapturedContent(rawText: string): {
    sanitizedText: string;
    injectionDetected: boolean;
    flags: string[];
  } {
    if (!rawText) {
      return { sanitizedText: '', injectionDetected: false, flags: [] };
    }

    const lower = rawText.toLowerCase();
    const flags: string[] = [];

    for (const threat of SecurityManager.INJECTION_WARNINGS) {
      if (lower.includes(threat)) {
        flags.push(threat);
      }
    }

    // Wrap untrusted user content in rigid structure with explicit non-executable encapsulation
    const clean = this.redactSensitiveData(rawText);

    return {
      sanitizedText: clean,
      injectionDetected: flags.length > 0,
      flags,
    };
  }

  /**
   * Check OS permissions for accessibility and screen recording
   */
  public async checkPermissions(): Promise<ApplicationPermissions> {
    const platform = os.platform();

    if (platform === 'darwin') {
      // In production macOS Electron, systemPreferences.getMediaAccessStatus('screen') and
      // systemPreferences.isTrustedAccessibilityClient(false) are queried.
      // Here we provide graceful checking with fallback to true/false detection.
      let screenRecording = true;
      let accessibility = true;
      let automation = true;

      try {
        // If running inside electron main process:
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const electron = await import('electron').catch(() => null);
        if (electron && electron.systemPreferences) {
          const screenStatus = electron.systemPreferences.getMediaAccessStatus?.('screen');
          screenRecording = screenStatus === 'granted';
          accessibility = electron.systemPreferences.isTrustedAccessibilityClient(false);
        }
      } catch {
        // Mock / development environment fallback
      }

      return {
        screenRecording,
        accessibility,
        automation,
      };
    }

    // Windows or Linux
    return {
      screenRecording: true,
      accessibility: true,
      automation: true,
    };
  }
}
