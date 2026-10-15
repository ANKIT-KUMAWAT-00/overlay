import { BaseAdapter, InsertionResult } from './BaseAdapter.js';
import { TargetApplication, AppCategory } from '../../shared/types.js';
import { exec } from 'child_process';
import util from 'util';
import os from 'os';

const execAsync = util.promisify(exec);

export class BrowserAdapter extends BaseAdapter {
  public readonly category: AppCategory = 'browser';
  public readonly name = 'BrowserAdapter';
  public readonly supportedApplications = ['Google Chrome', 'Microsoft Edge', 'Safari', 'Firefox', 'Arc', 'Brave'];

  public matches(target: TargetApplication): boolean {
    const name = target.appName.toLowerCase();
    return (
      target.category === 'browser' ||
      name.includes('chrome') ||
      name.includes('safari') ||
      name.includes('edge') ||
      name.includes('firefox') ||
      name.includes('arc') ||
      name.includes('brave')
    );
  }

  public async readSelection(target: TargetApplication): Promise<string | null> {
    const platform = os.platform();

    if (platform === 'darwin') {
      try {
        // macOS AppleScript to query active tab title & selected text if browser permits JavaScript/AppleScript
        const isChrome = target.appName.toLowerCase().includes('chrome');
        if (isChrome) {
          const script = `
            tell application "Google Chrome"
              if (count of windows) > 0 then
                set activeTab to active tab of front window
                set tabUrl to URL of activeTab
                set tabTitle to title of activeTab
                set selText to execute activeTab javascript "window.getSelection().toString()"
                return selText
              end if
            end tell
          `;
          const { stdout } = await execAsync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 3000 });
          if (stdout.trim().length > 0) return stdout.trim();
        }

        const isSafari = target.appName.toLowerCase().includes('safari');
        if (isSafari) {
          const script = `
            tell application "Safari"
              if (count of documents) > 0 then
                set docUrl to URL of front document
                set selText to do JavaScript "window.getSelection().toString()" in front document
                return selText
              end if
            end tell
          `;
          const { stdout } = await execAsync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 3000 });
          if (stdout.trim().length > 0) return stdout.trim();
        }
      } catch {
        // Fall back to accessibility or clipboard
      }
    }

    return null;
  }

  public async readContent(target: TargetApplication): Promise<string | null> {
    const platform = os.platform();

    if (platform === 'darwin') {
      try {
        const isChrome = target.appName.toLowerCase().includes('chrome');
        if (isChrome) {
          const script = `
            tell application "Google Chrome"
              if (count of windows) > 0 then
                set activeTab to active tab of front window
                return (title of activeTab) & linefeed & (URL of activeTab)
              end if
            end tell
          `;
          const { stdout } = await execAsync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 3000 });
          if (stdout.trim().length > 0) return stdout.trim();
        }
      } catch {
        // Ignored
      }
    }

    return target.windowTitle || null;
  }

  public async insertText(target: TargetApplication, text: string): Promise<InsertionResult> {
    // In web browsers, inserting text into web inputs requires care to avoid form auto-submission
    // We utilize clipboard paste simulation or fallback to clipboard
    try {
      const copied = await this.copyToClipboard(text);
      if (!copied) {
        return {
          success: false,
          verified: false,
          deliveryMethodUsed: 'clipboard_copy',
          error: 'Failed to access system clipboard',
          fallbackRecommended: true,
        };
      }

      const platform = os.platform();
      if (platform === 'darwin') {
        // Simulate Command + V keystroke into browser active focus
        // Strict safety rule: NEVER send Return/Enter key so forms are never auto-submitted!
        const script = `
          tell application "System Events"
            keystroke "v" using {command down}
          end tell
        `;
        await execAsync(`osascript -e '${script}'`, { timeout: 2000 });
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
        error: 'Answer copied to clipboard. Press Paste in the browser.',
      };
    } catch (err: any) {
      return {
        success: false,
        verified: false,
        deliveryMethodUsed: 'keyboard_simulation',
        error: err.message,
        fallbackRecommended: true,
      };
    }
  }
}
