/**
 * AUTHORITATIVE scoring - runs only in Cloud Functions.
 * The browser sends only {questionId -> displayed choice indexes}. Any client "score" is ignored.
 * Displayed indexes are mapped back to original indexes using the server-stored permutation.
 */
export function scoreAttempt(args) {
    const { attempt, config, questions, responses } = args;
    if (attempt.uid !== args.callerUid)
        return { ok: false, error: 'wrong_owner' };
    if (attempt.status !== 'in_progress')
        return { ok: false, error: 'attempt_not_in_progress' };
    // 60s grace for network latency.
    if (attempt.expiresAt && args.nowMs > attempt.expiresAt + 60_000)
        return { ok: false, error: 'attempt_expired' };
    const served = new Map(attempt.servedQuestions.map((s) => [s.questionId, s.choiceOrder]));
    for (const qid of Object.keys(responses))
        if (!served.has(qid))
            return { ok: false, error: 'unknown_question' };
    let marks = 0;
    const perQuestion = {};
    for (const [qid, order] of served) {
        const q = questions.get(qid);
        if (!q)
            return { ok: false, error: 'unknown_question' };
        const displayed = responses[qid] ?? [];
        if (displayed.some((i) => !Number.isInteger(i) || i < 0 || i >= order.length))
            return { ok: false, error: 'invalid_choice' };
        const chosenOriginal = [...new Set(displayed.map((i) => order[i]))].sort();
        const correct = [...q.correctChoiceIndexes].sort();
        const isCorrect = chosenOriginal.length === correct.length && chosenOriginal.every((v, i) => v === correct[i]);
        perQuestion[qid] = isCorrect;
        if (isCorrect)
            marks += config.marksPerQuestion;
        else if (displayed.length > 0)
            marks -= config.negativeMarks;
    }
    const maxMarks = served.size * config.marksPerQuestion;
    marks = Math.max(0, marks);
    const scorePercent = maxMarks === 0 ? 0 : Math.round((marks / maxMarks) * 10000) / 100;
    return { ok: true, result: { marks, maxMarks, scorePercent, passed: scorePercent >= config.passPercent, perQuestion } };
}
/** Can the candidate start another attempt? */
export function canStartAttempt(args) {
    const { config, previous, nowMs } = args;
    if (previous.some((a) => a.status === 'in_progress'))
        return { ok: false, reason: 'attempt_in_progress' };
    if (previous.some((a) => a.passed))
        return { ok: false, reason: 'already_passed' };
    const done = previous.filter((a) => a.status !== 'in_progress');
    if (config.maxAttempts > 0 && done.length >= config.maxAttempts)
        return { ok: false, reason: 'max_attempts_reached' };
    if (done.length === 0)
        return { ok: true };
    const last = Math.max(...done.map((a) => a.submittedAt ?? 0));
    const retryAt = last + config.retakeCooldownHours * 3_600_000;
    if (nowMs < retryAt)
        return { ok: false, reason: 'cooldown_active', retryAt };
    return { ok: true };
}
/** Server-side Fisher-Yates using an injected random source (crypto in production). */
export function shuffle(arr, rand) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(rand() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}
//# sourceMappingURL=scoring.js.map