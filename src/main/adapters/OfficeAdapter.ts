import { BaseAdapter, InsertionResult } from './BaseAdapter.js';
import { TargetApplication, AppCategory } from '../../shared/types.js';
import { exec } from 'child_process';
import util from 'util';
import os from 'os';

const execAsync = util.promisify(exec);

export class OfficeAdapter extends BaseAdapter {
  public readonly category: AppCategory = 'office';
  public readonly name = 'OfficeAdapter';
  public readonly supportedApplications = [
    'Microsoft Word',
    'Microsoft Excel',
    'Microsoft PowerPoint',
    'Pages',
    'Numbers',
    'Keynote',
    'Adobe Acrobat',
    'Notion',
    'Obsidian',
  ];

  public matches(target: TargetApplication): boolean {
    const name = target.appName.toLowerCase();
    return (
      target.category === 'office' ||
      name.includes('word') ||
      name.includes('excel') ||
      name.includes('powerpoint') ||
      name.includes('pages') ||
      name.includes('numbers') ||
      name.includes('keynote') ||
      name.includes('acrobat') ||
      name.includes('notion') ||
      name.includes('obsidian')
    );
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
        // Paste into current document selection without executing anything
        await execAsync(`osascript -e 'tell application "System Events" to keystroke "v" using {command down}'`, {
          timeout: 2000,
        });

        return {
          success: true,
          verified: true,
          deliveryMethodUsed: 'accessibility_insertion',
        };
      }

      return {
        success: true,
        verified: false,
        deliveryMethodUsed: 'clipboard_copy',
        error: 'Draft copied to clipboard. Press Paste in document.',
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
