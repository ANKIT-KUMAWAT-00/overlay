import {
  CaptureMethod,
  CaptureOptions,
  TargetApplication,
} from '../../shared/types.js';
import { ApplicationInteractionEngine } from '../interaction/ApplicationInteractionEngine.js';
import { SecurityManager } from '../security/SecurityManager.js';
import { OcrService } from './OcrService.js';
import { CaptureFailedError, PermissionDeniedError } from '../../shared/errors.js';
import { exec } from 'child_process';
import util from 'util';
import os from 'os';
import path from 'path';
import fs from 'fs/promises';

const execAsync = util.promisify(exec);

export interface CaptureResult {
  text: string;
  methodUsed: CaptureMethod;
  targetApp?: TargetApplication;
  uncertainExtraction: boolean;
  sanitizationFlags: string[];
}

export class QuestionCaptureEngine {
  private interactionEngine: ApplicationInteractionEngine;
  private securityManager: SecurityManager;
  private ocrService: OcrService;

  constructor(
    interactionEngine?: ApplicationInteractionEngine,
    securityManager?: SecurityManager,
    ocrService?: OcrService
  ) {
    this.interactionEngine = interactionEngine || new ApplicationInteractionEngine();
    this.securityManager = securityManager || new SecurityManager();
    this.ocrService = ocrService || new OcrService();
  }

  /**
   * Capture question using specified preferred method or automatic fallback cascade
   */
  public async captureQuestion(options?: CaptureOptions): Promise<CaptureResult> {
    const target = await this.interactionEngine.getActiveTarget();
    const preferredMethod = options?.preferredMethod || 'selected_text';

    // Sequence of capture methods to try
    const methodsToTry: CaptureMethod[] = [
      preferredMethod,
      'selected_text',
      'accessibility',
      'adapter',
      'clipboard',
      'screen_ocr',
    ];

    // Deduplicate sequence
    const uniqueMethods = Array.from(new Set(methodsToTry));

    let lastError: unknown = null;

    for (const method of uniqueMethods) {
      try {
        const rawText = await this.executeCaptureMethod(method, target, options);
        if (rawText && rawText.trim().length > 0) {
          // Process and sanitize captured content
          const { sanitizedText, injectionDetected, flags } = this.securityManager.sanitizeCapturedContent(rawText);

          return {
            text: sanitizedText,
            methodUsed: method,
            targetApp: target,
            uncertainExtraction: injectionDetected || sanitizedText.trim().length < 15,
            sanitizationFlags: flags,
          };
        }
      } catch (err) {
        lastError = err;
        // Continue to next available method in fallback matrix
      }
    }

    if (options?.allowManualFallback) {
      return {
        text: '',
        methodUsed: 'manual',
        targetApp: target,
        uncertainExtraction: true,
        sanitizationFlags: [],
      };
    }

    throw new CaptureFailedError(
      `All capture methods failed. Last error: ${lastError instanceof Error ? lastError.message : 'No text content found'}`,
      lastError
    );
  }

  private async executeCaptureMethod(
    method: CaptureMethod,
    target: TargetApplication,
    options?: CaptureOptions
  ): Promise<string | null> {
    switch (method) {
      case 'selected_text':
        return await this.interactionEngine.readSelection(target);

      case 'accessibility':
      case 'adapter': {
        const adapter = this.interactionEngine.resolveAdapter(target);
        const sel = await adapter.readSelection(target);
        if (sel) return sel;
        return await adapter.readContent(target);
      }

      case 'clipboard': {
        const electron = await import('electron').catch(() => null);
        if (electron?.clipboard) {
          const text = electron.clipboard.readText();
          if (text && text.trim().length > 0) {
            return text.trim();
          }
        }
        return null;
      }

      case 'region_ocr':
      case 'screen_ocr':
        return await this.captureScreenOcr(options?.region);

      case 'manual':
      case 'document':
      default:
        return null;
    }
  }

  /**
   * Take a screenshot of screen or region and run OCR
   */
  public async captureScreenOcr(region?: { x: number; y: number; width: number; height: number }): Promise<string> {
    const platform = os.platform();
    const tempDir = os.tmpdir();
    const screenshotPath = path.join(tempDir, `assistant_ocr_${Date.now()}.png`);

    try {
      if (platform === 'darwin') {
        // macOS screencapture
        let cmd = `screencapture -x -C "${screenshotPath}"`;
        if (region) {
          cmd = `screencapture -x -R${Math.round(region.x)},${Math.round(region.y)},${Math.round(region.width)},${Math.round(region.height)} "${screenshotPath}"`;
        }

        await execAsync(cmd, { timeout: 6000 });
      } else {
        // Fallback or electron desktopCapturer in native mode
        throw new Error('Screen capture not supported directly without desktopCapturer in this environment');
      }

      // Check if file exists
      const buffer = await fs.readFile(screenshotPath);
      const text = await this.ocrService.extractTextFromImage(buffer);
      return text;
    } catch (err: any) {
      if (err.message?.includes('permission')) {
        throw new PermissionDeniedError('screenRecording');
      }
      throw err;
    } finally {
      // Always cleanup screenshot file to avoid retaining screenshots unnecessarily
      try {
        await fs.unlink(screenshotPath);
      } catch {
        // Ignore
      }
    }
  }
}
