import { GoogleGenAI } from '@google/genai';
import {
  AnswerFormat,
  StructuredResult,
} from '../../shared/types.js';
import {
  NetworkError,
  TimeoutError,
  RateLimitError,
  InvalidConfigurationError,
  AssistantError,
} from '../../shared/errors.js';
import { GEMINI_MODELS, TIMEOUTS } from '../../shared/constants.js';

export interface GenerationRequest {
  taskId: string;
  question: string;
  targetAppCategory?: string;
  targetAppName?: string;
  preferredLanguage?: string;
  explanationMode?: boolean;
  modelOverride?: string;
  abortSignal?: AbortSignal;
}

export interface GenerationResponse {
  answer: string;
  detectedFormat: AnswerFormat;
  modelUsed: string;
  latencyMs: number;
}

export class GeminiAnswerEngine {
  private apiKey: string | null = null;
  private client: GoogleGenAI | null = null;
  private inFlightTasks: Set<string> = new Set();

  constructor(apiKey?: string | null) {
    if (apiKey) {
      this.setApiKey(apiKey);
    }
  }

  public setApiKey(key: string): void {
    this.apiKey = key.trim();
    if (this.apiKey.length > 0) {
      this.client = new GoogleGenAI({ apiKey: this.apiKey });
    } else {
      this.client = null;
    }
  }

  public hasValidKey(): boolean {
    return Boolean(this.apiKey && this.apiKey.length > 10);
  }

  /**
   * Intelligently infer the intended output format from question text and context
   */
  public detectQuestionFormat(question: string, targetCategory?: string): AnswerFormat {
    const q = question.toLowerCase();

    // MCQ Detection
    if (
      /\b([a-d]\)|\([a-d]\)|[a-d]\.)\s+[a-z0-9]/i.test(question) &&
      (q.includes('which of the following') || q.includes('select the correct') || q.includes('choose'))
    ) {
      return 'mcq';
    }

    // SQL Detection
    if (
      q.includes('select ') ||
      q.includes('insert into') ||
      q.includes('create table') ||
      q.includes('group by') ||
      q.includes('sql query')
    ) {
      return 'sql';
    }

    // JSON / Schema
    if (q.includes('json') && (q.includes('format') || q.includes('convert') || q.includes('schema'))) {
      return 'json';
    }

    // Debugging
    if (
      q.includes('error:') ||
      q.includes('exception:') ||
      q.includes('traceback') ||
      q.includes('undefined is not a function') ||
      q.includes('fix the bug')
    ) {
      return 'debug';
    }

    // Code
    if (
      targetCategory === 'ide' ||
      q.includes('write a function') ||
      q.includes('implement') ||
      q.includes('code in') ||
      q.includes('class ') ||
      q.includes('algorithm') ||
      q.includes('python') ||
      q.includes('typescript') ||
      q.includes('javascript') ||
      q.includes('c++') ||
      q.includes('java') ||
      q.includes('golang') ||
      q.includes('rust')
    ) {
      return 'code';
    }

    // Math
    if (
      q.includes('calculate') ||
      q.includes('solve for x') ||
      q.includes('integral') ||
      q.includes('derivative') ||
      q.includes('matrix')
    ) {
      return 'math';
    }

    // Clarification if extremely brief or ambiguous
    if (question.trim().length < 5 && !question.includes('?')) {
      return 'clarification';
    }

    return 'paragraph';
  }

  /**
   * Build targeted system prompt instruction respecting the output format
   */
  private buildSystemInstruction(format: AnswerFormat, targetCategory?: string, explanationMode = false): string {
    const baseDirectives = [
      'You are a high-performance Universal Desktop Assistant.',
      'Your job is to provide accurate, clean, production-grade answers directly into the user\'s workflow.',
      'CRITICAL: If the user needs code to be inserted into their editor, DO NOT surround the code with conversational commentary or Markdown fences unless specifically requested. Output pure, valid, formatted code ready for immediate insertion.',
    ];

    switch (format) {
      case 'code':
        return [
          ...baseDirectives,
          'FORMAT: RAW PRODUCTION CODE ONLY.',
          '- Follow the target language conventions, types, imports, and indentation.',
          '- Do NOT output markdown backticks (```) or introductory greetings unless explanationMode is explicitly requested.',
          explanationMode ? '- Append a brief 1-2 sentence technical explanation at the end in code comments.' : '- No conversational filler.',
        ].join('\n');

      case 'mcq':
        return [
          ...baseDirectives,
          'FORMAT: MULTIPLE CHOICE ANSWER.',
          '- State the correct option letter (e.g. "B") followed by the exact option text.',
          '- Provide a 1-sentence justification only if relevant.',
        ].join('\n');

      case 'sql':
        return [
          ...baseDirectives,
          'FORMAT: RAW SQL QUERY.',
          '- Output standardized SQL with standard uppercase keywords (SELECT, FROM, WHERE, JOIN).',
          '- No markdown fences, no conversational filler.',
        ].join('\n');

      case 'json':
        return [
          ...baseDirectives,
          'FORMAT: STRICT RAW JSON.',
          '- Must be valid parseable JSON conforming to RFC 8259.',
          '- Do NOT wrap in markdown fences.',
        ].join('\n');

      case 'debug':
        return [
          ...baseDirectives,
          'FORMAT: DEBUG FIX.',
          '- State the root cause in 1 concise sentence.',
          '- Provide the corrected code replacement directly.',
        ].join('\n');

      case 'clarification':
        return [
          ...baseDirectives,
          'FORMAT: CONCISE CLARIFICATION.',
          '- Ask exactly 1 or 2 targeted questions to clarify the missing requirement.',
          '- Do not invent requirements.',
        ].join('\n');

      case 'paragraph':
      default:
        return [
          ...baseDirectives,
          'FORMAT: CONCISE, PROFESSIONAL PROSE.',
          '- Respect tone, brevity, and structure.',
          '- Avoid redundant introductions (e.g. "Sure, here is your answer:"). Get straight to the point.',
        ].join('\n');
    }
  }

  /**
   * Generate answer using Gemini with timeouts, cancellation, duplicate prevention, and retries
   */
  public async generateAnswer(request: GenerationRequest): Promise<GenerationResponse> {
    if (!this.hasValidKey()) {
      throw new InvalidConfigurationError(
        'Gemini API key is not configured or is invalid. Please configure your API key in Settings.'
      );
    }

    // Duplicate request prevention
    if (this.inFlightTasks.has(request.taskId)) {
      throw new AssistantError(`Task ${request.taskId} is already in flight`, {
        category: 'DUPLICATE_ACTION',
        retryable: false,
      });
    }

    this.inFlightTasks.add(request.taskId);
    const startTime = Date.now();

    try {
      const format = this.detectQuestionFormat(request.question, request.targetAppCategory);
      const systemInstruction = this.buildSystemInstruction(
        format,
        request.targetAppCategory,
        request.explanationMode
      );

      const modelName = request.modelOverride || GEMINI_MODELS.DEFAULT;

      const answerText = await this.executeWithTimeout(
        async (signal) => {
          if (!this.client) {
            throw new InvalidConfigurationError('Gemini client uninitialized');
          }

          // Check if parent signal already aborted
          if (request.abortSignal?.aborted) {
            throw new AssistantError('Generation cancelled before start', {
              category: 'CANCELLED',
              retryable: false,
            });
          }

          // Use @google/genai SDK
          try {
            const response = await this.client.models.generateContent({
              model: modelName,
              contents: request.question,
              config: {
                systemInstruction,
                temperature: format === 'code' || format === 'json' || format === 'sql' ? 0.1 : 0.4,
              },
            });

            const text = (response as any).text ? String((response as any).text) : '';
            if (!text || text.trim().length === 0) {
              throw new AssistantError('Gemini returned an empty response', {
                category: 'INVALID_RESPONSE',
                retryable: true,
              });
            }

            return text;
          } catch (sdkErr: any) {
            // Map SDK errors
            const errMsg = sdkErr?.message || String(sdkErr);
            if (errMsg.includes('429') || errMsg.includes('quota') || errMsg.includes('RESOURCE_EXHAUSTED')) {
              throw new RateLimitError(errMsg, sdkErr);
            }
            if (errMsg.includes('API key') || errMsg.includes('unauthorized') || errMsg.includes('403')) {
              throw new InvalidConfigurationError(`Invalid Gemini API Key: ${errMsg}`);
            }
            if (errMsg.includes('fetch') || errMsg.includes('network') || errMsg.includes('ECONNREFUSED')) {
              throw new NetworkError(errMsg, sdkErr);
            }
            throw sdkErr;
          }
        },
        TIMEOUTS.GENERATION_MS,
        request.abortSignal
      );

      const latencyMs = Date.now() - startTime;

      return {
        answer: answerText.trim(),
        detectedFormat: format,
        modelUsed: modelName,
        latencyMs,
      };
    } finally {
      this.inFlightTasks.delete(request.taskId);
    }
  }

  /**
   * Request a bounded correction attempt when output validation fails
   */
  public async requestCorrection(
    taskId: string,
    originalQuestion: string,
    flawedAnswer: string,
    validationFeedback: string,
    abortSignal?: AbortSignal
  ): Promise<GenerationResponse> {
    const correctionPrompt = [
      'The previous generated response had validation issues:',
      `FEEDBACK: ${validationFeedback}`,
      '',
      `ORIGINAL QUESTION:`,
      originalQuestion,
      '',
      `PREVIOUS ATTEMPT:`,
      flawedAnswer,
      '',
      'Please produce the corrected, valid, syntax-compliant response strictly fixing the issues.',
    ].join('\n');

    return this.generateAnswer({
      taskId,
      question: correctionPrompt,
      abortSignal,
    });
  }

  /**
   * Helper to execute promise with explicit timeout and AbortSignal support
   */
  private async executeWithTimeout<T>(
    fn: (signal: AbortSignal) => Promise<T>,
    timeoutMs: number,
    parentSignal?: AbortSignal
  ): Promise<T> {
    const controller = new AbortController();

    if (parentSignal) {
      parentSignal.addEventListener('abort', () => controller.abort(parentSignal.reason), { once: true });
    }

    const timer = setTimeout(() => {
      controller.abort(new TimeoutError('Gemini API call', timeoutMs));
    }, timeoutMs);

    try {
      return await fn(controller.signal);
    } catch (err) {
      if (controller.signal.aborted && controller.signal.reason instanceof TimeoutError) {
        throw controller.signal.reason;
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }
}
