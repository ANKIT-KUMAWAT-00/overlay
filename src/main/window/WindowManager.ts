import { BrowserWindow, screen, app } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class WindowManager {
  private mainWindow: BrowserWindow | null = null;

  public createMainWindow(): BrowserWindow {
    if (this.mainWindow) {
      if (this.mainWindow.isMinimized()) this.mainWindow.restore();
      this.mainWindow.focus();
      return this.mainWindow;
    }

    const primaryDisplay = screen.getPrimaryDisplay();
    const { width, height } = primaryDisplay.workAreaSize;

    const winWidth = 640;
    const winHeight = 520;
    const x = Math.round((width - winWidth) / 2);
    const y = Math.round(height * 0.15); // Position floating slightly towards top-center like Spotlight/Raycast

    this.mainWindow = new BrowserWindow({
      width: winWidth,
      height: winHeight,
      x,
      y,
      frame: false,
      transparent: true,
      hasShadow: true,
      alwaysOnTop: true,
      skipTaskbar: false,
      resizable: true,
      minWidth: 500,
      minHeight: 400,
      webPreferences: {
        preload: path.join(app.getAppPath(), 'dist/preload/preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false,
      },
    });

    const htmlPath = path.join(app.getAppPath(), 'src/renderer/index.html');
    this.mainWindow.loadFile(htmlPath);

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    return this.mainWindow;
  }

  public getWindow(): BrowserWindow | null {
    return this.mainWindow;
  }

  public show(): void {
    if (!this.mainWindow) {
      this.createMainWindow();
    } else {
      this.mainWindow.show();
      this.mainWindow.focus();
    }
  }

  public hide(): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.hide();
    }
  }

  public toggle(): void {
    if (this.mainWindow && this.mainWindow.isVisible()) {
      this.hide();
    } else {
      this.show();
    }
  }

  public sendToRenderer(channel: string, data: any): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, data);
    }
  }
}
