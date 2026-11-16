import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scoreAttempt, canStartAttempt, shuffle, type Attempt } from '../src/index.js';

const questions = new Map([
  ['q1', { questionId: 'q1', correctChoiceIndexes: [0] }],
  ['q2', { questionId: 'q2', correctChoiceIndexes: [2] }],
  ['q3', { questionId: 'q3', correctChoiceIndexes: [1, 3] }],
  ['q4', { questionId: 'q4', correctChoiceIndexes: [3] }],
]);
// Served with shuffled choices: displayed index i shows original choice order[i]
const attempt: Attempt = {
  attemptId: 'a1', uid: 'u1', assessmentId: 'x', courseId: 'c', startedAt: 0, expiresAt: 1_000_000, status: 'in_progress',
  servedQuestions: [
    { questionId: 'q1', choiceOrder: [3, 2, 1, 0] },
    { questionId: 'q2', choiceOrder: [0, 1, 2, 3] },
    { questionId: 'q3', choiceOrder: [1, 0, 3, 2] },
    { questionId: 'q4', choiceOrder: [3, 0, 1, 2] },
  ],
};
const config = { passPercent: 60, marksPerQuestion: 1, negativeMarks: 0 };

test('scores using server-side choice permutation', () => {
  const r = scoreAttempt({ attempt, callerUid: 'u1', nowMs: 10, config, questions,
    responses: { q1: [3], q2: [2], q3: [0, 2], q4: [1] } });
  assert.ok(r.ok);
  if (r.ok) { assert.equal(r.result.marks, 3); assert.equal(r.result.scorePercent, 75); assert.equal(r.result.passed, true); assert.equal(r.result.perQuestion.q4, false); }
});

test('scoring tampering: extra fields, foreign questions, out-of-range choices, other user, resubmission', () => {
  // client-supplied score is simply not an input; unknown question IDs are rejected
  assert.deepEqual(scoreAttempt({ attempt, callerUid: 'u1', nowMs: 10, config, questions, responses: { qX: [0] } }), { ok: false, error: 'unknown_question' });
  assert.deepEqual(scoreAttempt({ attempt, callerUid: 'u1', nowMs: 10, config, questions, responses: { q1: [9] } }), { ok: false, error: 'invalid_choice' });
  assert.deepEqual(scoreAttempt({ attempt, callerUid: 'u1', nowMs: 10, config, questions, responses: { q1: [-1] } }), { ok: false, error: 'invalid_choice' });
  assert.deepEqual(scoreAttempt({ attempt, callerUid: 'attacker', nowMs: 10, config, questions, responses: {} }), { ok: false, error: 'wrong_owner' });
  assert.deepEqual(scoreAttempt({ attempt: { ...attempt, status: 'submitted' }, callerUid: 'u1', nowMs: 10, config, questions, responses: {} }), { ok: false, error: 'attempt_not_in_progress' });
  assert.deepEqual(scoreAttempt({ attempt, callerUid: 'u1', nowMs: 2_000_000, config, questions, responses: {} }), { ok: false, error: 'attempt_expired' });
});

test('selecting every choice does not game multi-answer or single-answer questions', () => {
  const r = scoreAttempt({ attempt, callerUid: 'u1', nowMs: 10, config, questions,
    responses: { q1: [0, 1, 2, 3], q2: [0, 1, 2, 3], q3: [0, 1, 2, 3], q4: [0, 1, 2, 3] } });
  assert.ok(r.ok);
  if (r.ok) assert.equal(r.result.marks, 0);
});

test('negative marking never drops below zero', () => {
  const r = scoreAttempt({ attempt, callerUid: 'u1', nowMs: 10, config: { ...config, negativeMarks: 1 }, questions,
    responses: { q1: [0], q2: [0], q3: [0], q4: [0] } });
  assert.ok(r.ok);
  if (r.ok) assert.equal(r.result.marks, 0);
});

test('attempt limits, cooldown and already-passed', () => {
  const cfg = { maxAttempts: 2, retakeCooldownHours: 24 };
  assert.deepEqual(canStartAttempt({ config: cfg, previous: [], nowMs: 0 }), { ok: true });
  const h = 3_600_000;
  assert.equal((canStartAttempt({ config: cfg, previous: [{ status: 'submitted', submittedAt: 0, passed: false }], nowMs: 1 * h }) as { reason: string }).reason, 'cooldown_active');
  assert.deepEqual(canStartAttempt({ config: cfg, previous: [{ status: 'submitted', submittedAt: 0, passed: false }], nowMs: 25 * h }), { ok: true });
  assert.equal((canStartAttempt({ config: cfg, previous: [{ status: 'submitted', submittedAt: 0, passed: false }, { status: 'submitted', submittedAt: 0, passed: false }], nowMs: 99 * h }) as { reason: string }).reason, 'max_attempts_reached');
  assert.equal((canStartAttempt({ config: cfg, previous: [{ status: 'submitted', submittedAt: 0, passed: true }], nowMs: 99 * h }) as { reason: string }).reason, 'already_passed');
});

test('shuffle is a permutation', () => {
  const s = shuffle([1, 2, 3, 4, 5], Math.random);
  assert.deepEqual([...s].sort(), [1, 2, 3, 4, 5]);
});
