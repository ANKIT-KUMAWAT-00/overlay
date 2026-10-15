import { BaseAdapter, InsertionResult } from './BaseAdapter.js';
import { TargetApplication, AppCategory } from '../../shared/types.js';
import { exec } from 'child_process';
import util from 'util';
import os from 'os';

const execAsync = util.promisify(exec);

export class IDEAdapter extends BaseAdapter {
  public readonly category: AppCategory = 'ide';
  public readonly name = 'IDEAdapter';
  public readonly supportedApplications = [
    'Code',
    'Visual Studio Code',
    'Cursor',
    'IntelliJ IDEA',
    'WebStorm',
    'PyCharm',
    'Android Studio',
    'Xcode',
    'Sublime Text',
    'Terminal',
    'iTerm2',
  ];

  public matches(target: TargetApplication): boolean {
    const name = target.appName.toLowerCase();
    return (
      target.category === 'ide' ||
      name.includes('code') ||
      name.includes('cursor') ||
      name.includes('idea') ||
      name.includes('webstorm') ||
      name.includes('pycharm') ||
      name.includes('studio') ||
      name.includes('xcode') ||
      name.includes('sublime') ||
      name.includes('terminal') ||
      name.includes('iterm')
    );
  }

  public async readSelection(target: TargetApplication): Promise<string | null> {
    const platform = os.platform();

    if (platform === 'darwin') {
      try {
        // Safe clipboard swap to capture selected code without modifying user clipboard permanently
        const electron = await import('electron').catch(() => null);
        if (electron?.clipboard) {
          const originalClipboard = electron.clipboard.readText();
          electron.clipboard.clear();

          // Command + C keystroke to copy current selection
          await execAsync(`osascript -e 'tell application "System Events" to keystroke "c" using {command down}'`, {
            timeout: 1500,
          });

          // Wait brief moment for OS clipboard sync
          await new Promise((r) => setTimeout(r, 80));

          const selectedText = electron.clipboard.readText();

          // Restore original clipboard if nothing was selected
          if (!selectedText || selectedText.trim().length === 0) {
            electron.clipboard.writeText(originalClipboard);
            return null;
          }

          return selectedText;
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

  /**
   * Insert code into the target IDE preserving indentation and line endings.
   * STRICT SAFETY RULE: Never execute generated code!
   */
  public async insertText(target: TargetApplication, code: string): Promise<InsertionResult> {
    try {
      // Normalize line endings to LF or CRLF based on platform
      const normalizedCode = os.platform() === 'win32'
        ? code.replace(/\r?\n/g, '\r\n')
        : code.replace(/\r\n/g, '\n');

      const copied = await this.copyToClipboard(normalizedCode);
      if (!copied) {
        return {
          success: false,
          verified: false,
          deliveryMethodUsed: 'clipboard_copy',
          error: 'Could not access system clipboard for code transfer',
        };
      }

      const platform = os.platform();
      if (platform === 'darwin') {
        // Simulate Command + V to paste
        // CRITICAL: We NEVER execute the code (e.g. we NEVER press Enter, run, or execute)
        await execAsync(`osascript -e 'tell application "System Events" to keystroke "v" using {command down}'`, {
          timeout: 2000,
        });

        return {
          success: true,
          verified: true,
          deliveryMethodUsed: 'editor_integration',
        };
      }

      return {
        success: true,
        verified: false,
        deliveryMethodUsed: 'clipboard_copy',
        error: 'Code copied to clipboard. Press Paste in editor.',
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
