import { BaseAdapter, InsertionResult } from './BaseAdapter.js';
import { TargetApplication, AppCategory } from '../../shared/types.js';
import { exec } from 'child_process';
import util from 'util';
import os from 'os';

const execAsync = util.promisify(exec);

export class GenericAdapter extends BaseAdapter {
  public readonly category: AppCategory = 'generic';
  public readonly name = 'GenericDesktopAdapter';
  public readonly supportedApplications = ['*'];

  public matches(_target: TargetApplication): boolean {
    return true; // Universal fallback
  }

  public async readSelection(target: TargetApplication): Promise<string | null> {
    const platform = os.platform();

    if (platform === 'darwin') {
      try {
        const electron = await import('electron').catch(() => null);
        if (electron?.clipboard) {
          const original = electron.clipboard.readText();
          electron.clipboard.clear();

          await execAsync(`osascript -e 'tell application "System Events" to keystroke "c" using {command down}'`, {
            timeout: 1500,
          });

          await new Promise((r) => setTimeout(r, 80));
          const text = electron.clipboard.readText();

          if (!text || text.trim().length === 0) {
            electron.clipboard.writeText(original);
            return null;
          }
          return text;
        }
      } catch {
        // Fallback
      }
    }

    return null;
  }

  public async readContent(target: TargetApplication): Promise<string | null> {
    return target.windowTitle || null;
  }

  public async insertText(target: TargetApplication, text: string): Promise<InsertionResult> {
    try {
      const copied = await this.copyToClipboard(text);
      if (!copied) {
        return {
          success: false,
          verified: false,
          deliveryMethodUsed: 'clipboard_copy',
          error: 'Could not access clipboard',
        };
      }

      const platform = os.platform();
      if (platform === 'darwin') {
        await execAsync(`osascript -e 'tell application "System Events" to keystroke "v" using {command down}'`, {
          timeout: 2000,
        });

        return {
          success: true,
          verified: true,
          deliveryMethodUsed: 'keyboard_simulation',
        };
      }

      return {
        success: true,
        verified: false,
        deliveryMethodUsed: 'clipboard_copy',
        error: 'Answer copied to clipboard. Press Paste in target window.',
      };
    } catch (err: any) {
      return {
        success: false,
        verified: false,
        deliveryMethodUsed: 'clipboard_copy',
        error: err.message,
        fallbackRecommended: true,
      };
    }
  }
}
