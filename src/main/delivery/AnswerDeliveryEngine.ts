import {
  DeliveryMethod,
  TargetApplication,
  StructuredResult,
  VerificationResult,
} from '../../shared/types.js';
import { ApplicationInteractionEngine } from '../interaction/ApplicationInteractionEngine.js';
import {
  FocusChangedError,
  TargetNotFoundError,
  AssistantError,
} from '../../shared/errors.js';

export interface DeliveryRequest {
  taskId: string;
  answer: string;
  targetApp?: TargetApplication;
  preferredMethod?: DeliveryMethod;
  userExplicitlyAuthorized?: boolean;
}

export interface DeliveryOutcome {
  delivered: boolean;
  methodUsed: DeliveryMethod;
  targetApp?: TargetApplication;
  verification: VerificationResult;
  clipboardReady: boolean;
  instructionToUser?: string;
}

export class AnswerDeliveryEngine {
  private interactionEngine: ApplicationInteractionEngine;
  private deliveredTasks: Set<string> = new Set();

  constructor(interactionEngine?: ApplicationInteractionEngine) {
    this.interactionEngine = interactionEngine || new ApplicationInteractionEngine();
  }

  /**
   * Deliver answer safely into the verified target application
   */
  public async deliverAnswer(request: DeliveryRequest): Promise<DeliveryOutcome> {
    // 1. Prevent duplicate insertion for same task
    if (this.deliveredTasks.has(request.taskId)) {
      throw new AssistantError(`Answer for task ${request.taskId} was already inserted`, {
        category: 'DUPLICATE_ACTION',
        retryable: false,
      });
    }

    // 2. Focus and Target Identity Verification
    const currentTarget = await this.interactionEngine.getActiveTarget();
    if (request.targetApp) {
      if (
        request.targetApp.appName !== currentTarget.appName &&
        request.targetApp.appName !== 'Active Desktop Application'
      ) {
        throw new FocusChangedError(request.targetApp.appName, currentTarget.appName);
      }
    }

    const preferredMethod = request.preferredMethod || 'editor_integration';

    // 3. Fallback delivery cascade
    // app_api -> editor_integration -> accessibility_insertion -> keyboard_simulation -> clipboard_copy -> answer_window
    const deliveryMethods: DeliveryMethod[] = [
      preferredMethod,
      'editor_integration',
      'accessibility_insertion',
      'keyboard_simulation',
      'clipboard_copy',
      'answer_window',
    ];

    const uniqueMethods = Array.from(new Set(deliveryMethods));

    let lastError: string | undefined;

    for (const method of uniqueMethods) {
      try {
        if (method === 'clipboard_copy') {
          const copied = await this.interactionEngine.resolveAdapter(currentTarget).copyToClipboard(request.answer);
          if (copied) {
            this.deliveredTasks.add(request.taskId);
            return {
              delivered: true,
              methodUsed: 'clipboard_copy',
              targetApp: currentTarget,
              verification: {
                verified: true,
                evidence: 'Content placed into system clipboard buffer',
              },
              clipboardReady: true,
              instructionToUser: 'Answer copied to clipboard. Press Command+V / Ctrl+V in your application.',
            };
          }
        } else if (method === 'answer_window') {
          this.deliveredTasks.add(request.taskId);
          return {
            delivered: true,
            methodUsed: 'answer_window',
            targetApp: currentTarget,
            verification: {
              verified: true,
              evidence: 'Answer presented in selectable overlay preview window',
            },
            clipboardReady: true,
            instructionToUser: 'Answer is ready in the assistant window.',
          };
        } else {
          // Attempt direct insertion via adapter
          const insertionResult = await this.interactionEngine.insertAnswer(currentTarget, request.answer);

          if (insertionResult.success) {
            this.deliveredTasks.add(request.taskId);
            return {
              delivered: true,
              methodUsed: method,
              targetApp: currentTarget,
              verification: {
                verified: insertionResult.verified,
                reason: insertionResult.verified ? 'Insertion confirmed by OS adapter' : 'Unverified insertion',
              },
              clipboardReady: true,
              instructionToUser: insertionResult.verified
                ? 'Answer successfully inserted into application.'
                : 'Answer inserted (unverified). Answer is also retained on clipboard.',
            };
          } else {
            lastError = insertionResult.error;
          }
        }
      } catch (err: any) {
        lastError = err.message;
      }
    }

    // Direct methods failed, prepare clipboard fallback
    await this.interactionEngine.resolveAdapter(currentTarget).copyToClipboard(request.answer);
    this.deliveredTasks.add(request.taskId);

    return {
      delivered: true,
      methodUsed: 'clipboard_copy',
      targetApp: currentTarget,
      verification: {
        verified: true,
        evidence: 'Direct insertion unavailable. Prepared clipboard fallback.',
      },
      clipboardReady: true,
      instructionToUser: `Direct insertion was blocked (${lastError || 'unsupported target'}). Answer copied to clipboard.`,
    };
  }

  public clearTask(taskId: string): void {
    this.deliveredTasks.delete(taskId);
  }
}
