import { globalShortcut, app } from 'electron';
import { DEFAULT_SHORTCUTS } from '../../shared/constants.js';
import os from 'os';

export interface ShortcutCallbacks {
  onActivate: () => void;
  onDeliverAnswer: () => void;
  onCancel: () => void;
}

export interface ShortcutStatus {
  activationShortcut: string;
  activationRegistered: boolean;
  insertionShortcut: string;
  insertionRegistered: boolean;
  error?: string;
}

export class ShortcutManager {
  private activationKey: string;
  private alternativeActivationKey: string;
  private insertionKey: string;
  private callbacks: ShortcutCallbacks;
  private lastTriggerTime = 0;
  private debounceMs = 400; // Prevent duplicate rapid activation events

  constructor(callbacks: ShortcutCallbacks, customActivation?: string, customInsertion?: string) {
    this.callbacks = callbacks;
    const platform = (os.platform() in DEFAULT_SHORTCUTS ? os.platform() : 'darwin') as keyof typeof DEFAULT_SHORTCUTS;
    const defaults = DEFAULT_SHORTCUTS[platform];

    this.activationKey = customActivation || defaults.activation;
    this.alternativeActivationKey = defaults.alternativeActivation;
    this.insertionKey = customInsertion || defaults.insertion;
  }

  /**
   * Register global shortcuts with conflict detection and fallback alternatives
   */
  public registerAll(): ShortcutStatus {
    this.unregisterAll();

    let activationRegistered = false;
    let insertionRegistered = false;
    let error: string | undefined;

    // 1. Register Primary Activation Shortcut
    try {
      activationRegistered = globalShortcut.register(this.activationKey, () => {
        const now = Date.now();
        if (now - this.lastTriggerTime < this.debounceMs) {
          return; // Debounce rapid duplicate activations
        }
        this.lastTriggerTime = now;
        this.callbacks.onActivate();
      });

      if (!activationRegistered) {
        console.warn(`[ShortcutManager] Primary activation shortcut ${this.activationKey} failed to register (conflict). Trying alternative: ${this.alternativeActivationKey}`);
        activationRegistered = globalShortcut.register(this.alternativeActivationKey, () => {
          this.callbacks.onActivate();
        });
        if (activationRegistered) {
          this.activationKey = this.alternativeActivationKey;
        } else {
          error = `Shortcut conflict: Both ${this.activationKey} and ${this.alternativeActivationKey} are taken by another application.`;
        }
      }
    } catch (err: any) {
      error = `Shortcut registration exception: ${err.message}`;
    }

    // 2. Register Delivery Shortcut (Explicitly separate from activation)
    try {
      insertionRegistered = globalShortcut.register(this.insertionKey, () => {
        const now = Date.now();
        if (now - this.lastTriggerTime < this.debounceMs) {
          return;
        }
        this.lastTriggerTime = now;
        this.callbacks.onDeliverAnswer();
      });
    } catch (err: any) {
      console.warn(`[ShortcutManager] Failed to register insertion key ${this.insertionKey}: ${err.message}`);
    }

    return {
      activationShortcut: this.activationKey,
      activationRegistered,
      insertionShortcut: this.insertionKey,
      insertionRegistered,
      error,
    };
  }

  public unregisterAll(): void {
    try {
      globalShortcut.unregisterAll();
    } catch {
      // Ignored during cleanup
    }
  }

  public updateShortcuts(newActivation?: string, newInsertion?: string): ShortcutStatus {
    if (newActivation) this.activationKey = newActivation;
    if (newInsertion) this.insertionKey = newInsertion;
    return this.registerAll();
  }

  public getStatus(): ShortcutStatus {
    return {
      activationShortcut: this.activationKey,
      activationRegistered: globalShortcut.isRegistered(this.activationKey),
      insertionShortcut: this.insertionKey,
      insertionRegistered: globalShortcut.isRegistered(this.insertionKey),
    };
  }
}
