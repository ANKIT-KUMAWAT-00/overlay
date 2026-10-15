import { TargetApplication, AppCategory } from '../../shared/types.js';

export interface InsertionResult {
  success: boolean;
  verified: boolean;
  deliveryMethodUsed: string;
  error?: string;
  fallbackRecommended?: boolean;
}

export abstract class BaseAdapter {
  public abstract readonly category: AppCategory;
  public abstract readonly name: string;
  public abstract readonly supportedApplications: string[];

  /**
   * Check if this adapter can handle the target application
   */
  public abstract matches(target: TargetApplication): boolean;

  /**
   * Extract currently selected text from target application
   */
  public abstract readSelection(target: TargetApplication): Promise<string | null>;

  /**
   * Read broader visible content from target application
   */
  public abstract readContent(target: TargetApplication): Promise<string | null>;

  /**
   * Safely insert generated text into target application field
   */
  public abstract insertText(target: TargetApplication, text: string): Promise<InsertionResult>;

  /**
   * Fallback method: copy text to clipboard and prompt user
   */
  public async copyToClipboard(text: string): Promise<boolean> {
    try {
      const electron = await import('electron').catch(() => null);
      if (electron?.clipboard) {
        electron.clipboard.writeText(text);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }
}
