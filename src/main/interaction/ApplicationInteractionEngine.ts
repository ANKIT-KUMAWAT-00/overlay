import {
  TargetApplication,
  AppCategory,
  InteractionLayer,
  ApplicationCapability,
} from '../../shared/types.js';
import { CapabilityRegistry } from './CapabilityRegistry.js';
import { BaseAdapter, InsertionResult } from '../adapters/BaseAdapter.js';
import { BrowserAdapter } from '../adapters/BrowserAdapter.js';
import { IDEAdapter } from '../adapters/IDEAdapter.js';
import { OfficeAdapter } from '../adapters/OfficeAdapter.js';
import { CommunicationAdapter } from '../adapters/CommunicationAdapter.js';
import { GenericAdapter } from '../adapters/GenericAdapter.js';
import { exec } from 'child_process';
import util from 'util';
import os from 'os';

const execAsync = util.promisify(exec);

export class ApplicationInteractionEngine {
  private registry: CapabilityRegistry;
  private adapters: BaseAdapter[];
  private genericAdapter: GenericAdapter;

  constructor(registry?: CapabilityRegistry) {
    this.registry = registry || new CapabilityRegistry();
    this.genericAdapter = new GenericAdapter();
    this.adapters = [
      new BrowserAdapter(),
      new IDEAdapter(),
      new OfficeAdapter(),
      new CommunicationAdapter(),
      this.genericAdapter,
    ];
  }

  public getRegistry(): CapabilityRegistry {
    return this.registry;
  }

  /**
   * Detect current active focused application and window
   */
  public async getActiveTarget(): Promise<TargetApplication> {
    const platform = os.platform();

    if (platform === 'darwin') {
      try {
        const script = `
          tell application "System Events"
            set frontProc to first process whose frontmost is true
            set procName to name of frontProc
            set procBundle to bundle identifier of frontProc
            set winTitle to ""
            try
              set winTitle to name of front window of frontProc
            end try
            return procName & "|||" & procBundle & "|||" & winTitle
          end tell
        `;
        const { stdout } = await execAsync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 2000 });
        const parts = stdout.trim().split('|||');
        const appName = parts[0]?.trim() || 'Unknown Application';
        const bundleId = parts[1]?.trim() || '';
        const windowTitle = parts[2]?.trim() || '';

        const category = this.categorizeApplication(appName, bundleId);

        return {
          appName,
          bundleId,
          windowTitle,
          processId: 0,
          isFocused: true,
          category,
        };
      } catch {
        // Fallback
      }
    }

    // Windows or Linux fallback detection
    return {
      appName: 'Active Desktop Application',
      windowTitle: 'Active Window',
      processId: 0,
      isFocused: true,
      category: 'generic',
    };
  }

  private categorizeApplication(appName: string, bundleId: string): AppCategory {
    const combined = `${appName} ${bundleId}`.toLowerCase();
    if (combined.includes('chrome') || combined.includes('safari') || combined.includes('edge') || combined.includes('firefox') || combined.includes('browser')) {
      return 'browser';
    }
    if (combined.includes('code') || combined.includes('cursor') || combined.includes('idea') || combined.includes('terminal') || combined.includes('iterm') || combined.includes('xcode')) {
      return 'ide';
    }
    if (combined.includes('word') || combined.includes('excel') || combined.includes('powerpoint') || combined.includes('pages') || combined.includes('numbers') || combined.includes('notion') || combined.includes('obsidian') || combined.includes('acrobat')) {
      return 'office';
    }
    if (combined.includes('slack') || combined.includes('teams') || combined.includes('discord') || combined.includes('mail') || combined.includes('outlook') || combined.includes('telegram')) {
      return 'communication';
    }
    return 'generic';
  }

  /**
   * Find matching adapter for target
   */
  public resolveAdapter(target: TargetApplication): BaseAdapter {
    for (const adapter of this.adapters) {
      if (adapter !== this.genericAdapter && adapter.matches(target)) {
        return adapter;
      }
    }
    return this.genericAdapter;
  }

  /**
   * Discover capabilities and determine interaction layer order
   */
  public getCapabilities(target: TargetApplication): ApplicationCapability {
    return this.registry.resolveForTarget(target);
  }

  /**
   * Read selection through appropriate adapter
   */
  public async readSelection(target: TargetApplication): Promise<string | null> {
    const adapter = this.resolveAdapter(target);
    const text = await adapter.readSelection(target);
    if (text && text.trim().length > 0) {
      return text.trim();
    }
    // If specific adapter fails, try generic adapter fallback
    if (adapter !== this.genericAdapter) {
      return await this.genericAdapter.readSelection(target);
    }
    return null;
  }

  /**
   * Deliver answer through appropriate adapter
   */
  public async insertAnswer(target: TargetApplication, text: string): Promise<InsertionResult> {
    const adapter = this.resolveAdapter(target);
    const result = await adapter.insertText(target, text);

    if (!result.success && result.fallbackRecommended && adapter !== this.genericAdapter) {
      return await this.genericAdapter.insertText(target, text);
    }

    return result;
  }
}
