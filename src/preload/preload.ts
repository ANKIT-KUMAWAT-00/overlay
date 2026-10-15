import { contextBridge, ipcRenderer } from 'electron';
import { AssistantSettings, CaptureOptions, DeliveryMethod } from '../shared/types.js';

export interface AssistantApi {
  getState: () => Promise<any>;
  getSettings: () => Promise<AssistantSettings>;
  updateSettings: (settings: Partial<AssistantSettings>) => Promise<AssistantSettings>;
  triggerActivation: (options?: CaptureOptions) => Promise<any>;
  cancelTask: () => Promise<void>;
  deliverAnswer: (preferredMethod?: DeliveryMethod) => Promise<any>;
  copyAnswer: (text: string) => Promise<boolean>;
  submitManualQuestion: (question: string) => Promise<any>;
  checkPermissions: () => Promise<any>;
  hideWindow: () => void;
  closeApp: () => void;
  onStateChange: (callback: (state: any) => void) => () => void;
}

const api: AssistantApi = {
  getState: () => ipcRenderer.invoke('assistant:getState'),
  getSettings: () => ipcRenderer.invoke('assistant:getSettings'),
  updateSettings: (settings) => ipcRenderer.invoke('assistant:updateSettings', settings),
  triggerActivation: (options) => ipcRenderer.invoke('assistant:triggerActivation', options),
  cancelTask: () => ipcRenderer.invoke('assistant:cancelTask'),
  deliverAnswer: (method) => ipcRenderer.invoke('assistant:deliverAnswer', method),
  copyAnswer: (text) => ipcRenderer.invoke('assistant:copyAnswer', text),
  submitManualQuestion: (q) => ipcRenderer.invoke('assistant:submitManualQuestion', q),
  checkPermissions: () => ipcRenderer.invoke('assistant:checkPermissions'),
  hideWindow: () => ipcRenderer.send('assistant:hideWindow'),
  closeApp: () => ipcRenderer.send('assistant:closeApp'),
  onStateChange: (callback) => {
    const listener = (_event: any, state: any) => callback(state);
    ipcRenderer.on('assistant:stateChanged', listener);
    return () => ipcRenderer.removeListener('assistant:stateChanged', listener);
  },
};

contextBridge.exposeInMainWorld('assistantApi', api);
