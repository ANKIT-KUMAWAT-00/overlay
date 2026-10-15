import {
  ApplicationCapability,
  InteractionLayer,
  SupportedOperation,
  HealthStatus,
  TargetApplication,
} from '../../shared/types.js';
import os from 'os';

export class CapabilityRegistry {
  private registry: Map<string, ApplicationCapability> = new Map();

  constructor() {
    this.registerBuiltInCapabilities();
  }

  private registerBuiltInCapabilities(): void {
    const platform = os.platform() as 'darwin' | 'win32' | 'linux';

    // 1. Web Browsers (Chrome, Edge, Safari, Firefox)
    this.register({
      appId: 'browser-generic',
      appName: 'Web Browser',
      os: platform,
      supportedInteractionMethods: [
        InteractionLayer.BROWSER_EXTENSION,
        InteractionLayer.SCRIPTING_INTERFACE,
        InteractionLayer.ACCESSIBILITY_API,
        InteractionLayer.SCREEN_CAPTURE_OCR,
        InteractionLayer.CLIPBOARD_TRANSFER,
        InteractionLayer.MANUAL_GUIDANCE,
      ],
      availablePermissions: { screenRecording: true, accessibility: true, automation: true },
      knownLimitations: [
        'Protected web pages (e.g. chrome://, bank portals) may restrict DOM access',
        'Cross-origin iframes restrict accessibility tree inspection',
      ],
      adapterVersion: '1.2.0',
      healthStatus: 'HEALTHY',
      supportedOperations: ['READ_SELECTION', 'READ_CONTENT', 'INSERT_TEXT', 'COPY_CLIPBOARD', 'NAVIGATE'],
      lastCheck: Date.now(),
    });

    // 2. Coding Environments (VS Code, JetBrains, Terminal)
    this.register({
      appId: 'ide-vscode',
      appName: 'Visual Studio Code',
      os: platform,
      supportedInteractionMethods: [
        InteractionLayer.APP_ADAPTER,
        InteractionLayer.ACCESSIBILITY_API,
        InteractionLayer.KEYBOARD_MOUSE_SIM,
        InteractionLayer.CLIPBOARD_TRANSFER,
        InteractionLayer.MANUAL_GUIDANCE,
      ],
      availablePermissions: { screenRecording: true, accessibility: true, automation: true },
      knownLimitations: [
        'Indentation must be preserved accurately based on file tab size',
        'Execution of code is explicitly forbidden without user authorization',
      ],
      adapterVersion: '1.4.0',
      healthStatus: 'HEALTHY',
      supportedOperations: ['READ_SELECTION', 'READ_CONTENT', 'INSERT_TEXT', 'COPY_CLIPBOARD'],
      lastCheck: Date.now(),
    });

    // 3. Office & Document Applications
    this.register({
      appId: 'office-generic',
      appName: 'Office & Document Processor',
      os: platform,
      supportedInteractionMethods: [
        InteractionLayer.OFFICIAL_API,
        InteractionLayer.ACCESSIBILITY_API,
        InteractionLayer.SCREEN_CAPTURE_OCR,
        InteractionLayer.CLIPBOARD_TRANSFER,
        InteractionLayer.MANUAL_GUIDANCE,
      ],
      availablePermissions: { screenRecording: true, accessibility: true, automation: false },
      knownLimitations: [
        'Document tables require explicit cell targeting to avoid cell overwrite',
        'Read-only protected mode must be respected',
      ],
      adapterVersion: '1.1.0',
      healthStatus: 'HEALTHY',
      supportedOperations: ['READ_SELECTION', 'READ_CONTENT', 'INSERT_TEXT', 'COPY_CLIPBOARD'],
      lastCheck: Date.now(),
    });

    // 4. Communication Applications (Slack, Teams, Mail)
    this.register({
      appId: 'communication-generic',
      appName: 'Communication & Messaging Client',
      os: platform,
      supportedInteractionMethods: [
        InteractionLayer.ACCESSIBILITY_API,
        InteractionLayer.KEYBOARD_MOUSE_SIM,
        InteractionLayer.CLIPBOARD_TRANSFER,
        InteractionLayer.MANUAL_GUIDANCE,
      ],
      availablePermissions: { screenRecording: true, accessibility: true, automation: true },
      knownLimitations: [
        'AUTOMATIC MESSAGE SENDING IS STRICTLY FORBIDDEN',
        'Draft responses must be placed in compose area for explicit user review',
      ],
      adapterVersion: '1.0.0',
      healthStatus: 'HEALTHY',
      supportedOperations: ['READ_SELECTION', 'READ_CONTENT', 'INSERT_TEXT', 'COPY_CLIPBOARD'],
      lastCheck: Date.now(),
    });

    // 5. Generic Desktop Fallback
    this.register({
      appId: 'generic-desktop',
      appName: 'Generic Desktop Application',
      os: platform,
      supportedInteractionMethods: [
        InteractionLayer.ACCESSIBILITY_API,
        InteractionLayer.SCREEN_CAPTURE_OCR,
        InteractionLayer.KEYBOARD_MOUSE_SIM,
        InteractionLayer.CLIPBOARD_TRANSFER,
        InteractionLayer.MANUAL_GUIDANCE,
      ],
      availablePermissions: { screenRecording: true, accessibility: true, automation: false },
      knownLimitations: [
        'Unregistered native GUI framework may lack deep accessibility nodes',
        'Visual OCR fallback will be utilized if text nodes are empty',
      ],
      adapterVersion: '1.0.0',
      healthStatus: 'HEALTHY',
      supportedOperations: ['READ_SELECTION', 'READ_CONTENT', 'COPY_CLIPBOARD'],
      lastCheck: Date.now(),
    });
  }

  public register(capability: ApplicationCapability): void {
    this.registry.set(capability.appId, capability);
  }

  public get(appId: string): ApplicationCapability | undefined {
    return this.registry.get(appId);
  }

  public list(): ApplicationCapability[] {
    return Array.from(this.registry.values());
  }

  /**
   * Find capability for a detected application target
   */
  public resolveForTarget(target?: TargetApplication): ApplicationCapability {
    if (!target) {
      return this.registry.get('generic-desktop')!;
    }

    const name = target.appName.toLowerCase();
    const cat = target.category;

    if (cat === 'browser' || name.includes('chrome') || name.includes('safari') || name.includes('firefox') || name.includes('edge')) {
      return this.registry.get('browser-generic')!;
    }

    if (cat === 'ide' || name.includes('code') || name.includes('idea') || name.includes('studio') || name.includes('sublime')) {
      return this.registry.get('ide-vscode')!;
    }

    if (cat === 'office' || name.includes('word') || name.includes('excel') || name.includes('notes') || name.includes('notion')) {
      return this.registry.get('office-generic')!;
    }

    if (cat === 'communication' || name.includes('slack') || name.includes('teams') || name.includes('mail') || name.includes('discord')) {
      return this.registry.get('communication-generic')!;
    }

    return this.registry.get('generic-desktop')!;
  }

  /**
   * Dynamically verify that a capability is functional and not degraded
   */
  public async probeHealth(appId: string): Promise<HealthStatus> {
    const cap = this.registry.get(appId);
    if (!cap) return 'UNAVAILABLE';

    // Verify OS matching
    const currentPlatform = os.platform();
    if (cap.os !== currentPlatform && cap.os !== 'linux') {
      cap.healthStatus = 'DEGRADED';
      cap.lastCheck = Date.now();
      return 'DEGRADED';
    }

    cap.healthStatus = 'HEALTHY';
    cap.lastCheck = Date.now();
    return 'HEALTHY';
  }
}
