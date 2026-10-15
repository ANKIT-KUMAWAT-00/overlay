import { Tray, Menu, nativeImage, app } from 'electron';

export interface TrayCallbacks {
  onToggleWindow: () => void;
  onActivateWorkflow: () => void;
  onOpenSettings: () => void;
  onQuit: () => void;
}

export class TrayManager {
  private tray: Tray | null = null;
  private callbacks: TrayCallbacks;

  constructor(callbacks: TrayCallbacks) {
    this.callbacks = callbacks;
  }

  public init(): void {
    if (this.tray) return;

    // Create a 16x16 icon in memory (transparent PNG with neon circle)
    const icon = nativeImage.createEmpty();

    try {
      this.tray = new Tray(icon);
      this.tray.setToolTip('Universal AI Desktop Assistant');

      this.updateMenu('IDLE');

      this.tray.on('click', () => {
        this.callbacks.onToggleWindow();
      });
    } catch (err) {
      console.warn('[TrayManager] Failed to create system tray:', err);
    }
  }

  public updateMenu(statusText: string): void {
    if (!this.tray) return;

    const contextMenu = Menu.buildFromTemplate([
      {
        label: `Assistant Status: ${statusText}`,
        enabled: false,
      },
      { type: 'separator' },
      {
        label: 'Show Assistant HUD',
        click: () => this.callbacks.onToggleWindow(),
      },
      {
        label: 'Trigger AI Interaction (Command/Ctrl+Shift+Z)',
        click: () => this.callbacks.onActivateWorkflow(),
      },
      {
        label: 'Configure API Key & Settings...',
        click: () => this.callbacks.onOpenSettings(),
      },
      { type: 'separator' },
      {
        label: 'Quit Universal Assistant',
        click: () => this.callbacks.onQuit(),
      },
    ]);

    this.tray.setContextMenu(contextMenu);
  }

  public destroy(): void {
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }
}
