import { describe, it, expect, beforeEach } from 'vitest';
import { CapabilityRegistry } from '../src/main/interaction/CapabilityRegistry.js';
import { TargetApplication } from '../src/shared/types.js';

describe('CapabilityRegistry', () => {
  let registry: CapabilityRegistry;

  beforeEach(() => {
    registry = new CapabilityRegistry();
  });

  it('contains registered capabilities for all 5 core categories', () => {
    const list = registry.list();
    expect(list.length).toBeGreaterThanOrEqual(5);

    expect(registry.get('browser-generic')).toBeDefined();
    expect(registry.get('ide-vscode')).toBeDefined();
    expect(registry.get('office-generic')).toBeDefined();
    expect(registry.get('communication-generic')).toBeDefined();
    expect(registry.get('generic-desktop')).toBeDefined();
  });

  it('correctly maps application targets to their capability profile', () => {
    const chromeTarget: TargetApplication = {
      appName: 'Google Chrome',
      windowTitle: 'Google Search',
      processId: 10,
      isFocused: true,
      category: 'browser',
    };
    expect(registry.resolveForTarget(chromeTarget).appId).toBe('browser-generic');

    const vsCodeTarget: TargetApplication = {
      appName: 'Code',
      windowTitle: 'main.py - project',
      processId: 20,
      isFocused: true,
      category: 'ide',
    };
    expect(registry.resolveForTarget(vsCodeTarget).appId).toBe('ide-vscode');

    const slackTarget: TargetApplication = {
      appName: 'Slack',
      windowTitle: 'general - workspace',
      processId: 30,
      isFocused: true,
      category: 'communication',
    };
    expect(registry.resolveForTarget(slackTarget).appId).toBe('communication-generic');

    const unknownTarget: TargetApplication = {
      appName: 'CustomInternalTool',
      windowTitle: 'Dashboard',
      processId: 40,
      isFocused: true,
      category: 'generic',
    };
    expect(registry.resolveForTarget(unknownTarget).appId).toBe('generic-desktop');
  });

  it('successfully probes health status dynamically', async () => {
    const health = await registry.probeHealth('browser-generic');
    expect(health).toBe('HEALTHY');

    const missingHealth = await registry.probeHealth('non-existent-app');
    expect(missingHealth).toBe('UNAVAILABLE');
  });
});
