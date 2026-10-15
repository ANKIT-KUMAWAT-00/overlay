import { describe, it, expect } from 'vitest';
import { BrowserAdapter } from '../src/main/adapters/BrowserAdapter.js';
import { IDEAdapter } from '../src/main/adapters/IDEAdapter.js';
import { OfficeAdapter } from '../src/main/adapters/OfficeAdapter.js';
import { CommunicationAdapter } from '../src/main/adapters/CommunicationAdapter.js';
import { GenericAdapter } from '../src/main/adapters/GenericAdapter.js';
import { TargetApplication } from '../src/shared/types.js';

describe('Application Adapters', () => {
  const browserTarget: TargetApplication = {
    appName: 'Google Chrome',
    windowTitle: 'GitHub - Pull Requests',
    processId: 10,
    isFocused: true,
    category: 'browser',
  };

  const ideTarget: TargetApplication = {
    appName: 'Visual Studio Code',
    windowTitle: 'engine.ts - workspace',
    processId: 20,
    isFocused: true,
    category: 'ide',
  };

  const officeTarget: TargetApplication = {
    appName: 'Microsoft Word',
    windowTitle: 'Q3_Report.docx',
    processId: 30,
    isFocused: true,
    category: 'office',
  };

  const commTarget: TargetApplication = {
    appName: 'Slack',
    windowTitle: 'engineering - team',
    processId: 40,
    isFocused: true,
    category: 'communication',
  };

  const genericTarget: TargetApplication = {
    appName: 'LegacyDatabaseClient',
    windowTitle: 'Query Tool',
    processId: 50,
    isFocused: true,
    category: 'generic',
  };

  it('BrowserAdapter matches browsers and rejects non-browsers', () => {
    const adapter = new BrowserAdapter();
    expect(adapter.matches(browserTarget)).toBe(true);
    expect(adapter.matches(ideTarget)).toBe(false);
  });

  it('IDEAdapter matches code editors and rejects non-editors', () => {
    const adapter = new IDEAdapter();
    expect(adapter.matches(ideTarget)).toBe(true);
    expect(adapter.matches(officeTarget)).toBe(false);
  });

  it('OfficeAdapter matches word processors and documents', () => {
    const adapter = new OfficeAdapter();
    expect(adapter.matches(officeTarget)).toBe(true);
    expect(adapter.matches(commTarget)).toBe(false);
  });

  it('CommunicationAdapter matches messaging clients', () => {
    const adapter = new CommunicationAdapter();
    expect(adapter.matches(commTarget)).toBe(true);
    expect(adapter.matches(browserTarget)).toBe(false);
  });

  it('GenericAdapter acts as universal fallback for unspecialized applications', () => {
    const adapter = new GenericAdapter();
    expect(adapter.matches(genericTarget)).toBe(true);
    expect(adapter.matches(ideTarget)).toBe(true); // matches anything as fallback
  });
});
