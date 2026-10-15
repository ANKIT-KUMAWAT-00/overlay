import { app, ipcMain } from 'electron';
import { StateMachine } from './state/StateMachine.js';
import { RecoveryManager } from './recovery/RecoveryManager.js';
import { SecurityManager } from './security/SecurityManager.js';
import { ShortcutManager } from './shortcuts/ShortcutManager.js';
import { TrayManager } from './tray/TrayManager.js';
import { WindowManager } from './window/WindowManager.js';
import { ApplicationInteractionEngine } from './interaction/ApplicationInteractionEngine.js';
import { QuestionCaptureEngine } from './capture/QuestionCaptureEngine.js';
import { GeminiAnswerEngine } from './ai/GeminiAnswerEngine.js';
import { AnswerValidationEngine } from './validation/AnswerValidationEngine.js';
import { AnswerDeliveryEngine } from './delivery/AnswerDeliveryEngine.js';
import { CaptureOptions, DeliveryMethod } from '../shared/types.js';

class DesktopAssistantApplication {
  private stateMachine: StateMachine;
  private recoveryManager: RecoveryManager;
  private securityManager: SecurityManager;
  private interactionEngine: ApplicationInteractionEngine;
  private captureEngine: QuestionCaptureEngine;
  private geminiEngine: GeminiAnswerEngine;
  private validationEngine: AnswerValidationEngine;
  private deliveryEngine: AnswerDeliveryEngine;
  private windowManager: WindowManager;
  private shortcutManager: ShortcutManager;
  private trayManager: TrayManager;

  constructor() {
    this.stateMachine = new StateMachine();
    this.recoveryManager = new RecoveryManager();
    this.securityManager = new SecurityManager();
    this.interactionEngine = new ApplicationInteractionEngine();
    this.captureEngine = new QuestionCaptureEngine(this.interactionEngine, this.securityManager);
    this.geminiEngine = new GeminiAnswerEngine(this.securityManager.getApiKey());
    this.validationEngine = new AnswerValidationEngine();
    this.deliveryEngine = new AnswerDeliveryEngine(this.interactionEngine);
    this.windowManager = new WindowManager();

    this.shortcutManager = new ShortcutManager({
      onActivate: () => this.handleGlobalActivation(),
      onDeliverAnswer: () => this.handleGlobalInsertion(),
      onCancel: () => this.handleCancel(),
    });

    this.trayManager = new TrayManager({
      onToggleWindow: () => this.windowManager.toggle(),
      onActivateWorkflow: () => this.handleGlobalActivation(),
      onOpenSettings: () => {
        this.windowManager.show();
        this.windowManager.sendToRenderer('assistant:openSettings', null);
      },
      onQuit: () => app.quit(),
    });

    this.setupStateMachineListeners();
    this.setupIpcHandlers();
  }

  public async init(): Promise<void> {
    await app.whenReady();

    this.windowManager.createMainWindow();
    this.trayManager.init();
    const shortcutStatus = this.shortcutManager.registerAll();

    console.log('[UniversalAssistant] Application initialized.');
    console.log(`[UniversalAssistant] Global Activation Shortcut: ${shortcutStatus.activationShortcut} (Registered: ${shortcutStatus.activationRegistered})`);
    console.log(`[UniversalAssistant] Answer Insertion Shortcut: ${shortcutStatus.insertionShortcut} (Registered: ${shortcutStatus.insertionRegistered})`);
    if (shortcutStatus.error) {
      console.warn(`[UniversalAssistant] Shortcut warning: ${shortcutStatus.error}`);
    }

    app.on('will-quit', () => {
      this.shortcutManager.unregisterAll();
      this.trayManager.destroy();
    });

    app.on('activate', () => {
      this.windowManager.show();
    });
  }

  private setupStateMachineListeners(): void {
    this.stateMachine.on('stateChange', (context) => {
      this.trayManager.updateMenu(context.state);
      this.windowManager.sendToRenderer('assistant:stateChanged', context);
    });
  }

  private setupIpcHandlers(): void {
    ipcMain.handle('assistant:getState', () => {
      return this.stateMachine.getContext();
    });

    ipcMain.handle('assistant:getSettings', () => {
      return this.securityManager.getSettings();
    });

    ipcMain.handle('assistant:updateSettings', (_event, partial) => {
      const updated = this.securityManager.updateSettings(partial);
      if (this.securityManager.getApiKey()) {
        this.geminiEngine.setApiKey(this.securityManager.getApiKey()!);
      }
      this.shortcutManager.updateShortcuts(updated.activationShortcut, updated.insertionShortcut);
      return updated;
    });

    ipcMain.handle('assistant:triggerActivation', (_event, options?: CaptureOptions) => {
      return this.startInteractionWorkflow(options);
    });

    ipcMain.handle('assistant:cancelTask', () => {
      this.handleCancel();
    });

    ipcMain.handle('assistant:deliverAnswer', (_event, preferredMethod?: DeliveryMethod) => {
      return this.executeDelivery(preferredMethod);
    });

    ipcMain.handle('assistant:copyAnswer', async (_event, text: string) => {
      const electron = await import('electron');
      electron.clipboard.writeText(text);
      return true;
    });

    ipcMain.handle('assistant:submitManualQuestion', (_event, question: string) => {
      return this.processManualQuestion(question);
    });

    ipcMain.handle('assistant:checkPermissions', async () => {
      return await this.securityManager.checkPermissions();
    });

    ipcMain.on('assistant:hideWindow', () => {
      this.windowManager.hide();
    });

    ipcMain.on('assistant:closeApp', () => {
      app.quit();
    });
  }

  /**
   * Main interaction workflow triggered by shortcut or button
   */
  public async handleGlobalActivation(options?: CaptureOptions): Promise<void> {
    this.windowManager.show();
    await this.startInteractionWorkflow(options);
  }

  public async startInteractionWorkflow(options?: CaptureOptions): Promise<void> {
    const context = this.stateMachine.startNewTask();
    const taskId = context.taskId;
    const abortSignal = this.stateMachine.getAbortSignal();

    try {
      // 1. CAPTURING STAGE
      this.stateMachine.transition('CAPTURING', taskId, {
        message: 'Capturing active context and question from target application',
      });

      let questionText = '';
      let capturedVia = options?.preferredMethod || 'selected_text';
      let targetApp = await this.interactionEngine.getActiveTarget();

      try {
        const captureResult = await this.captureEngine.captureQuestion(options);
        questionText = captureResult.text;
        capturedVia = captureResult.methodUsed;
        if (captureResult.targetApp) targetApp = captureResult.targetApp;
      } catch (captureErr) {
        // Recovery for capture failure
        this.stateMachine.transition('CAPTURE_RECOVERY', taskId, {
          message: 'Preferred capture failed, evaluating alternatives',
          error: String(captureErr),
        });

        const plan = this.recoveryManager.planRecovery(taskId, 'CAPTURE', captureErr, false, capturedVia);
        if (plan.fallbackMethod) {
          try {
            const fallbackResult = await this.captureEngine.captureQuestion({
              ...options,
              preferredMethod: plan.fallbackMethod as any,
            });
            questionText = fallbackResult.text;
            capturedVia = fallbackResult.methodUsed;
          } catch (fallbackErr) {
            this.stateMachine.transition('FAILED', taskId, {
              message: 'All automated capture methods failed. Please enter your question manually.',
              error: String(fallbackErr),
              updates: { targetApp },
            });
            return;
          }
        } else {
          this.stateMachine.transition('FAILED', taskId, {
            message: 'Question capture failed. Please type your query.',
            error: String(captureErr),
            updates: { targetApp },
          });
          return;
        }
      }

      if (!questionText || questionText.trim().length === 0) {
        this.stateMachine.transition('READY', taskId, {
          message: 'No text was selected. Ready for manual input.',
          updates: { targetApp, questionText: '', capturedVia: 'manual' },
        });
        return;
      }

      // 2. GENERATING STAGE
      await this.runGenerationWorkflow(taskId, questionText, targetApp, capturedVia, abortSignal);
    } catch (err: any) {
      if (abortSignal.aborted) {
        this.stateMachine.transition('CANCELLED', taskId, { message: 'Task cancelled' });
      } else {
        const category = this.recoveryManager.classifyError(err);
        this.stateMachine.transition('FAILED', taskId, {
          message: `Interaction failed: ${err.message}`,
          error: err.message,
          errorCategory: category,
        });
      }
    }
  }

  public async processManualQuestion(question: string): Promise<void> {
    const context = this.stateMachine.getContext();
    const taskId = context.taskId;
    const abortSignal = this.stateMachine.getAbortSignal();
    const targetApp = context.targetApp || (await this.interactionEngine.getActiveTarget());

    await this.runGenerationWorkflow(taskId, question, targetApp, 'manual', abortSignal);
  }

  private async runGenerationWorkflow(
    taskId: string,
    questionText: string,
    targetApp: any,
    capturedVia: any,
    abortSignal: AbortSignal
  ): Promise<void> {
    const format = this.geminiEngine.detectQuestionFormat(questionText, targetApp.category);

    this.stateMachine.transition('GENERATING', taskId, {
      message: `Analyzing question with Gemini (${this.securityManager.getSettings().modelName})`,
      updates: {
        questionText,
        capturedVia,
        questionFormat: format,
        targetApp,
      },
    });

    let rawAnswer = '';
    try {
      const response = await this.geminiEngine.generateAnswer({
        taskId,
        question: questionText,
        targetAppCategory: targetApp.category,
        targetAppName: targetApp.appName,
        modelOverride: this.securityManager.getSettings().modelName,
        abortSignal,
      });
      rawAnswer = response.answer;
    } catch (genErr) {
      const plan = this.recoveryManager.planRecovery(taskId, 'GENERATION', genErr);
      if (plan.shouldRetry) {
        this.stateMachine.transition('GENERATION_RECOVERY', taskId, {
          message: plan.actionDescription,
        });
        await new Promise((r) => setTimeout(r, plan.delayMs));
        const retryResponse = await this.geminiEngine.generateAnswer({
          taskId,
          question: questionText,
          targetAppCategory: targetApp.category,
          targetAppName: targetApp.appName,
          abortSignal,
        });
        rawAnswer = retryResponse.answer;
      } else {
        throw genErr;
      }
    }

    // 3. VALIDATING STAGE
    this.stateMachine.transition('VALIDATING', taskId, {
      message: 'Validating answer formatting, syntax, and completeness',
      updates: { generatedAnswer: rawAnswer },
    });

    let finalAnswer = rawAnswer;
    const validation = this.validationEngine.validate(rawAnswer, format);

    if (validation.requiresCorrection) {
      // Attempt bounded correction
      this.stateMachine.transition('GENERATION_RECOVERY', taskId, {
        message: 'Validation detected syntax issues. Requesting automated correction...',
      });

      try {
        const issuesSummary = validation.issues.map((i) => i.message).join('; ');
        const corrected = await this.geminiEngine.requestCorrection(
          taskId,
          questionText,
          rawAnswer,
          issuesSummary,
          abortSignal
        );
        const secondValidation = this.validationEngine.validate(corrected.answer, format);
        finalAnswer = secondValidation.cleanedOutput || corrected.answer;
      } catch {
        // If correction fails, preserve original answer for user inspection
        finalAnswer = rawAnswer;
      }
    } else if (validation.cleanedOutput) {
      finalAnswer = validation.cleanedOutput;
    }

    // 4. READY STAGE
    this.stateMachine.transition('READY', taskId, {
      message: 'Answer ready. Press Insertion key or click Insert to place into target.',
      updates: {
        generatedAnswer: rawAnswer,
        validatedAnswer: finalAnswer,
      },
    });
  }

  /**
   * Global Insertion triggered via configured insertion shortcut
   */
  public async handleGlobalInsertion(): Promise<void> {
    const context = this.stateMachine.getContext();
    if (context.state !== 'READY') {
      return;
    }
    await this.executeDelivery();
  }

  public async executeDelivery(preferredMethod?: DeliveryMethod): Promise<void> {
    const context = this.stateMachine.getContext();
    const taskId = context.taskId;
    const answer = context.validatedAnswer || context.generatedAnswer;

    if (!answer) {
      return;
    }

    this.stateMachine.transition('DELIVERING', taskId, {
      message: 'Delivering answer into target application',
    });

    try {
      const outcome = await this.deliveryEngine.deliverAnswer({
        taskId,
        answer,
        targetApp: context.targetApp,
        preferredMethod,
      });

      this.stateMachine.transition('COMPLETED', taskId, {
        message: outcome.instructionToUser || 'Answer successfully delivered.',
        updates: {
          deliveredVia: outcome.methodUsed,
          deliveryVerified: outcome.verification.verified,
        },
      });
    } catch (deliveryErr: any) {
      const category = this.recoveryManager.classifyError(deliveryErr);
      this.stateMachine.transition('DELIVERY_RECOVERY', taskId, {
        message: `Direct delivery encountered: ${deliveryErr.message}. Falling back to clipboard.`,
        error: deliveryErr.message,
        errorCategory: category,
      });

      // Prepare clipboard fallback
      const electron = await import('electron');
      electron.clipboard.writeText(answer);

      this.stateMachine.transition('COMPLETED', taskId, {
        message: `Answer copied to clipboard (${deliveryErr.message}). Press Paste in your application.`,
        updates: {
          deliveredVia: 'clipboard_copy',
          deliveryVerified: true,
        },
      });
    }
  }

  public handleCancel(): void {
    this.stateMachine.cancel();
  }
}

// Start Desktop Assistant
const assistantApp = new DesktopAssistantApplication();
assistantApp.init().catch((err) => {
  console.error('[UniversalAssistant] Fatal error during initialization:', err);
});
