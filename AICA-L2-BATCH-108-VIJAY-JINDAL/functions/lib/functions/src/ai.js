import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';
import { REGION, GEMINI_API_KEY } from './config.js';
import { safeLog } from './log.js';
export class GeminiProvider {
    name = 'gemini';
    async improveSummary(args) {
        const prompt = `You are a professional resume writing assistant for the Indian banking and debt collection recruitment industry.
Improve the following candidate professional summary to make it professional, ATS-friendly, and grammatically clean.

CRITICAL RULES:
1. Do NOT invent any employers, years of experience, certifications, or achievements.
2. Keep the summary under 100 words.
3. Highlight ethics, borrower respect, and collection skills.
4. Return ONLY the polished summary text, with no introductory text or markdown formatting.

Candidate Role: ${args.role}
Candidate Headline: ${args.headline}
Skills: ${args.skills.join(', ')}
Draft Summary: "${args.draftSummary}"`;
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${args.apiKey}`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: prompt }] }],
                generationConfig: { maxOutputTokens: 250, temperature: 0.3 },
            }),
        });
        if (!response.ok) {
            const errText = await response.text();
            safeLog('error', 'Gemini API call failed', { status: response.status, body: errText });
            throw new Error('AI provider error');
        }
        const data = (await response.json());
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
        if (!text)
            throw new Error('Empty response from AI provider');
        return text;
    }
}
export const aiImproveResumeSummary = onCall({ region: REGION, secrets: [GEMINI_API_KEY], maxInstances: 10 }, async (req) => {
    const uid = req.auth?.uid;
    if (!uid)
        throw new HttpsError('unauthenticated', 'sign_in_required');
    const input = req.data;
    if (!input?.consentGiven) {
        throw new HttpsError('permission-denied', 'ai_consent_required');
    }
    if (!input.draftSummary?.trim()) {
        throw new HttpsError('invalid-argument', 'summary_required');
    }
    const db = getFirestore();
    // 1. Check Owner Admin AI settings
    const settingsSnap = await db.doc('settings_private/ai').get();
    const settings = settingsSnap.data() ?? {};
    if (settings.enabled !== true) {
        throw new HttpsError('failed-precondition', 'ai_disabled_by_admin');
    }
    // 2. Check Daily Limit per candidate (Cost control)
    const today = new Date().toISOString().slice(0, 10);
    const usageRef = db.doc(`ai_usage/${today}_${uid}`);
    const usageSnap = await usageRef.get();
    const count = usageSnap.data()?.count ?? 0;
    const perCandidateLimit = settings.perCandidateDailyLimit || 5;
    if (count >= perCandidateLimit) {
        throw new HttpsError('resource-exhausted', 'daily_limit_reached');
    }
    // 3. Get Secret Key
    let apiKey = '';
    try {
        apiKey = GEMINI_API_KEY.value();
    }
    catch {
        apiKey = process.env.GEMINI_API_KEY || '';
    }
    if (!apiKey) {
        throw new HttpsError('unavailable', 'ai_service_unconfigured');
    }
    // 4. Execute AI provider with minimized data
    const provider = new GeminiProvider();
    try {
        const suggested = await provider.improveSummary({
            headline: input.headline ? input.headline.slice(0, 100) : '',
            draftSummary: input.draftSummary.slice(0, 500),
            role: input.role ? input.role.slice(0, 50) : 'Collection Specialist',
            skills: (input.skills ?? []).slice(0, 10).map((s) => s.slice(0, 30)),
            apiKey,
        });
        // Increment usage count
        await usageRef.set({
            uid,
            date: today,
            count: FieldValue.increment(1),
            lastUsedAt: FieldValue.serverTimestamp(),
        }, { merge: true });
        return {
            original: input.draftSummary,
            suggested,
        };
    }
    catch (err) {
        safeLog('error', 'AI improvement error', { uid });
        throw new HttpsError('internal', 'Failed to generate AI suggestion. Please try again later.');
    }
});
//# sourceMappingURL=ai.js.map