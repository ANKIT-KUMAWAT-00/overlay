import { AnswerFormat, ValidationResult, ValidationIssue } from '../../shared/types.js';

export class AnswerValidationEngine {
  /**
   * Validate generated answer against expectations
   */
  public validate(
    answer: string,
    expectedFormat: AnswerFormat,
    options?: {
      targetLanguage?: string;
      requiredSignature?: string;
      maxLength?: number;
    }
  ): ValidationResult {
    const issues: ValidationIssue[] = [];

    // 1. Empty or whitespace check
    if (!answer || answer.trim().length === 0) {
      issues.push({
        type: 'empty',
        message: 'The generated response is empty.',
        severity: 'error',
      });
      return {
        isValid: false,
        detectedFormat: expectedFormat,
        issues,
        requiresCorrection: true,
      };
    }

    const trimmed = answer.trim();

    // 2. Unexpected Truncation check
    if (this.detectTruncation(trimmed)) {
      issues.push({
        type: 'truncation',
        message: 'The response appears to be truncated or cut off mid-sentence/mid-block.',
        severity: 'error',
      });
    }

    // 3. Format-specific validation
    let cleanedOutput: string | undefined = trimmed;

    switch (expectedFormat) {
      case 'json': {
        const jsonValidation = this.validateJson(trimmed);
        if (!jsonValidation.valid) {
          issues.push({
            type: 'syntax',
            message: `Invalid JSON syntax: ${jsonValidation.error}`,
            severity: 'error',
          });
        } else {
          cleanedOutput = jsonValidation.cleaned;
        }
        break;
      }

      case 'code': {
        const codeValidation = this.validateCode(trimmed, options?.targetLanguage, options?.requiredSignature);
        issues.push(...codeValidation.issues);
        cleanedOutput = codeValidation.cleanedCode;
        break;
      }

      case 'sql': {
        const sqlValidation = this.validateSql(trimmed);
        issues.push(...sqlValidation.issues);
        cleanedOutput = sqlValidation.cleanedSql;
        break;
      }

      case 'mcq': {
        const mcqIssues = this.validateMcq(trimmed);
        issues.push(...mcqIssues);
        break;
      }

      case 'paragraph':
      default: {
        if (options?.maxLength && trimmed.length > options.maxLength) {
          issues.push({
            type: 'format',
            message: `Output exceeds maximum specified length (${trimmed.length} > ${options.maxLength})`,
            severity: 'warning',
          });
        }
        break;
      }
    }

    const hasErrors = issues.some((i) => i.severity === 'error');

    return {
      isValid: !hasErrors,
      detectedFormat: expectedFormat,
      issues,
      cleanedOutput: hasErrors ? undefined : cleanedOutput,
      requiresCorrection: hasErrors,
    };
  }

  /**
   * Detect potential truncation indicators
   */
  private detectTruncation(text: string): boolean {
    const lastLines = text.split('\n').filter((l) => l.trim().length > 0);
    if (lastLines.length === 0) return false;
    const lastLine = lastLines[lastLines.length - 1].trim();

    // Dangling unfinished code operators or cut-off punctuation
    const trailingTokens = ['&&', '||', '=>', '...', '+', '-', '*', '/', ',', ':', 'def ', 'function '];
    for (const token of trailingTokens) {
      if (lastLine.endsWith(token)) return true;
    }

    // Unbalanced code fence
    const backtickCount = (text.match(/```/g) || []).length;
    if (backtickCount % 2 !== 0) return true;

    // Unbalanced brackets in non-trivial code
    if (text.includes('{') || text.includes('[')) {
      const openBraces = (text.match(/\{/g) || []).length;
      const closeBraces = (text.match(/\}/g) || []).length;
      const openBrackets = (text.match(/\[/g) || []).length;
      const closeBrackets = (text.match(/\]/g) || []).length;
      if (openBraces > closeBraces + 2 || openBrackets > closeBrackets + 2) {
        return true;
      }
    }

    return false;
  }

  /**
   * Validate JSON syntax
   */
  private validateJson(text: string): { valid: boolean; error?: string; cleaned?: string } {
    let clean = text;
    // Strip markdown fences if present
    if (clean.startsWith('```json')) clean = clean.slice(7);
    if (clean.startsWith('```')) clean = clean.slice(3);
    if (clean.endsWith('```')) clean = clean.slice(0, -3);
    clean = clean.trim();

    try {
      const parsed = JSON.parse(clean);
      return { valid: true, cleaned: JSON.stringify(parsed, null, 2) };
    } catch (err: any) {
      return { valid: false, error: err.message };
    }
  }

  /**
   * Validate Code syntax and signatures
   */
  private validateCode(
    text: string,
    targetLanguage?: string,
    requiredSignature?: string
  ): { issues: ValidationIssue[]; cleanedCode: string } {
    const issues: ValidationIssue[] = [];
    let cleaned = text;

    // Check if code was wrapped in markdown fences despite instructions
    const matchFence = /^```(?:\w+)?\n([\s\S]*?)\n```$/i.exec(text);
    if (matchFence) {
      cleaned = matchFence[1];
    }

    // Signature check
    if (requiredSignature && !cleaned.includes(requiredSignature)) {
      issues.push({
        type: 'signature',
        message: `Generated code does not contain required signature: '${requiredSignature}'`,
        severity: 'warning',
      });
    }

    // Common syntax check for JS/TS if node vm is available
    if (targetLanguage === 'javascript' || targetLanguage === 'typescript' || targetLanguage === 'js') {
      try {
        new Function(cleaned);
      } catch (syntaxErr: any) {
        // If it contains import/export it's a module, so standard Function might fail on export/import statements
        if (!cleaned.includes('import ') && !cleaned.includes('export ')) {
          issues.push({
            type: 'syntax',
            message: `JavaScript syntax check failed: ${syntaxErr.message}`,
            severity: 'error',
          });
        }
      }
    }

    return { issues, cleanedCode: cleaned };
  }

  /**
   * Validate SQL syntax basic heuristics
   */
  private validateSql(text: string): { issues: ValidationIssue[]; cleanedSql: string } {
    const issues: ValidationIssue[] = [];
    let cleaned = text;
    if (cleaned.startsWith('```sql')) cleaned = cleaned.slice(6);
    if (cleaned.startsWith('```')) cleaned = cleaned.slice(3);
    if (cleaned.endsWith('```')) cleaned = cleaned.slice(0, -3);
    cleaned = cleaned.trim();

    const sqlKeywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'WITH', 'DROP'];
    const firstWord = cleaned.split(/\s+/)[0]?.toUpperCase();
    if (!sqlKeywords.includes(firstWord)) {
      issues.push({
        type: 'syntax',
        message: `SQL statement does not begin with a standard SQL keyword (got '${firstWord}')`,
        severity: 'warning',
      });
    }

    return { issues, cleanedSql: cleaned };
  }

  /**
   * Validate MCQ answer
   */
  private validateMcq(text: string): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    // Should clearly start with or contain an option letter
    if (!/^[A-D]\b|^Option\s+[A-D]/i.test(text.trim()) && !/\b([A-D]\))\s+/i.test(text)) {
      issues.push({
        type: 'format',
        message: 'MCQ response does not clearly identify the selected option letter (A, B, C, or D).',
        severity: 'warning',
      });
    }
    return issues;
  }
}
