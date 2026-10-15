import { BaseAdapter, InsertionResult } from './BaseAdapter.js';
import { TargetApplication, AppCategory } from '../../shared/types.js';
import { exec } from 'child_process';
import util from 'util';
import os from 'os';

const execAsync = util.promisify(exec);

export class CommunicationAdapter extends BaseAdapter {
  public readonly category: AppCategory = 'communication';
  public readonly name = 'CommunicationAdapter';
  public readonly supportedApplications = [
    'Slack',
    'Microsoft Teams',
    'Discord',
    'Mail',
    'Microsoft Outlook',
    'Telegram',
    'Messages',
  ];

  public matches(target: TargetApplication): boolean {
    const name = target.appName.toLowerCase();
    return (
      target.category === 'communication' ||
      name.includes('slack') ||
      name.includes('teams') ||
      name.includes('discord') ||
      name.includes('mail') ||
      name.includes('outlook') ||
      name.includes('telegram') ||
      name.includes('messages')
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

  /**
   * Insert drafted message into compose field for user review.
   * ABSOLUTE SAFETY RULE: NEVER press Return or Enter to send the message!
   */
  public async insertText(target: TargetApplication, draft: string): Promise<InsertionResult> {
    try {
      const copied = await this.copyToClipboard(draft);
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
        // Paste into compose box. NEVER press Enter!
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
        error: 'Draft reply copied to clipboard. Paste into chat box and review before sending.',
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
