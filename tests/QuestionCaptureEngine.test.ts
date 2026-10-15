import { describe, it, expect, beforeEach } from 'vitest';
import { QuestionCaptureEngine } from '../src/main/capture/QuestionCaptureEngine.js';
import { OcrService, OcrEngine } from '../src/main/capture/OcrService.js';
import { SecurityManager } from '../src/main/security/SecurityManager.js';
import { CaptureFailedError } from '../src/shared/errors.js';

class MockOcrEngine implements OcrEngine {
  public name = 'MockOcr';
  async recognizeText(_image: string | Buffer): Promise<string> {
    return 'Calculate 5 x 10 and print result';
  }
}

describe('QuestionCaptureEngine & OcrService', () => {
  let capture: QuestionCaptureEngine;
  let ocr: OcrService;

  beforeEach(() => {
    ocr = new OcrService(new MockOcrEngine());
    capture = new QuestionCaptureEngine(undefined, new SecurityManager(), ocr);
  });

  it('OcrService cleans math artifacts and trims whitespace', async () => {
    const text = await ocr.extractTextFromImage(Buffer.from('fake'));
    expect(text).toBe('Calculate 5 * 10 and print result');
  });

  it('allows manual fallback when automated capture methods find no selection', async () => {
    // Mock interactionEngine returning empty
    (capture as any).interactionEngine = {
      getActiveTarget: async () => ({
        appName: 'Finder',
        windowTitle: 'Desktop',
        processId: 1,
        isFocused: true,
        category: 'generic',
      }),
      readSelection: async () => null,
      resolveAdapter: () => ({
        readSelection: async () => null,
        readContent: async () => null,
      }),
    };

    // Mock captureScreenOcr throwing
    (capture as any).captureScreenOcr = async () => '';

    const result = await capture.captureQuestion({
      allowManualFallback: true,
      preferredMethod: 'selected_text',
    });

    expect(result.methodUsed).toBe('manual');
    expect(result.text).toBe('');
    expect(result.uncertainExtraction).toBe(true);
  });

  it('throws CaptureFailedError if automated capture fails and manual fallback is disabled', async () => {
    (capture as any).interactionEngine = {
      getActiveTarget: async () => ({
        appName: 'Unknown App',
        windowTitle: 'Window',
        processId: 1,
        isFocused: true,
        category: 'generic',
      }),
      readSelection: async () => null,
      resolveAdapter: () => ({
        readSelection: async () => null,
        readContent: async () => null,
      }),
    };

    (capture as any).captureScreenOcr = async () => {
      throw new Error('Screen capture permission denied');
    };

    await expect(
      capture.captureQuestion({
        allowManualFallback: false,
        preferredMethod: 'selected_text',
      })
    ).rejects.toThrow(CaptureFailedError);
  });
});
