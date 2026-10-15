import tesseract from 'tesseract.js';
import fs from 'fs/promises';

export interface OcrEngine {
  name: string;
  recognizeText(imagePathOrBuffer: string | Buffer): Promise<string>;
}

export class TesseractOcrEngine implements OcrEngine {
  public readonly name = 'TesseractJS';

  public async recognizeText(imagePathOrBuffer: string | Buffer): Promise<string> {
    try {
      const result = await tesseract.recognize(imagePathOrBuffer, 'eng', {
        logger: () => {}, // Quiet
      });
      return result.data.text?.trim() || '';
    } catch (err: any) {
      throw new Error(`OCR processing failed: ${err.message}`);
    }
  }
}

export class OcrService {
  private engine: OcrEngine;

  constructor(engine?: OcrEngine) {
    this.engine = engine || new TesseractOcrEngine();
  }

  public setEngine(engine: OcrEngine): void {
    this.engine = engine;
  }

  public async extractTextFromImage(imagePathOrBuffer: string | Buffer): Promise<string> {
    const rawText = await this.engine.recognizeText(imagePathOrBuffer);
    return this.postProcessOcrText(rawText);
  }

  /**
   * Clean up OCR artifacts while preserving mathematical symbols and code indentation
   */
  private postProcessOcrText(text: string): string {
    if (!text) return '';

    return text
      // Normalize erratic carriage returns
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      // Fix common OCR math artifacts
      .replace(/(\d)\s*x\s*(\d)/g, '$1 * $2')
      // Remove trailing blank lines
      .trim();
  }
}
