import { describe, it, expect, beforeEach } from 'vitest';
import { AnswerValidationEngine } from '../src/main/validation/AnswerValidationEngine.js';

describe('AnswerValidationEngine', () => {
  let val: AnswerValidationEngine;

  beforeEach(() => {
    val = new AnswerValidationEngine();
  });

  it('detects empty responses and flags them as requiring correction', () => {
    const res = val.validate('   ', 'code');
    expect(res.isValid).toBe(false);
    expect(res.requiresCorrection).toBe(true);
    expect(res.issues.some((i) => i.type === 'empty')).toBe(true);
  });

  it('detects unexpected truncation from unclosed brackets or trailing operators', () => {
    const truncatedCode = 'function calculateTotal(items) {\n  const sum = items.reduce((a, b) =>';
    const res = val.validate(truncatedCode, 'code');

    expect(res.isValid).toBe(false);
    expect(res.issues.some((i) => i.type === 'truncation')).toBe(true);
  });

  it('validates and auto-formats valid JSON responses', () => {
    const rawJson = '```json\n{"name": "test", "active": true}\n```';
    const res = val.validate(rawJson, 'json');

    expect(res.isValid).toBe(true);
    expect(res.cleanedOutput).toBe(JSON.stringify({ name: 'test', active: true }, null, 2));
  });

  it('catches invalid JSON syntax and requests correction', () => {
    const badJson = '{"name": "test", active: true,}';
    const res = val.validate(badJson, 'json');

    expect(res.isValid).toBe(false);
    expect(res.requiresCorrection).toBe(true);
    expect(res.issues.some((i) => i.type === 'syntax')).toBe(true);
  });

  it('validates code signatures and removes unrequested markdown fences for direct editor insertion', () => {
    const fencedCode = '```typescript\nfunction solveProblem(n: number): number {\n  return n * 2;\n}\n```';
    const res = val.validate(fencedCode, 'code', {
      requiredSignature: 'function solveProblem',
    });

    expect(res.isValid).toBe(true);
    // Verified that markdown code fences were stripped cleanly for editor insertion
    expect(res.cleanedOutput).not.toContain('```typescript');
    expect(res.cleanedOutput).toContain('function solveProblem(n: number): number');
  });

  it('warns when a required function signature is missing', () => {
    const code = 'function otherFunc() { return 1; }';
    const res = val.validate(code, 'code', {
      requiredSignature: 'function targetSignature',
    });

    expect(res.issues.some((i) => i.type === 'signature')).toBe(true);
  });

  it('validates SQL statements start with standard keywords', () => {
    const validSql = 'SELECT id, username FROM users WHERE active = 1;';
    const res = val.validate(validSql, 'sql');
    expect(res.isValid).toBe(true);

    const badSql = 'Here is your query: SELECT * FROM table;';
    const badRes = val.validate(badSql, 'sql');
    expect(badRes.issues.some((i) => i.type === 'syntax')).toBe(true);
  });
});
