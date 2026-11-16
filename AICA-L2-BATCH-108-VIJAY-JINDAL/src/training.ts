import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';
import { randomBytes } from 'node:crypto';
import { REGION } from './config.js';
import { writeAudit } from './audit.js';
import { scoreAttempt, canStartAttempt, shuffle } from '../../shared/src/domain/scoring.js';
import { certificateEligibility } from '../../shared/src/domain/certificates.js';
import { newCertificateId } from '../../shared/src/ids.js';
import type {
  AssessmentConfig,
  Attempt,
  Question,
  PortalCertificate,
  PublicCertificateVerification,
} from '../../shared/src/models/training.js';
import type { CandidateCore } from '../../shared/src/models/candidate.js';

export const startAssessmentAttempt = onCall(
  { region: REGION, maxInstances: 20 },
  async (req) => {
    const uid = req.auth?.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'sign_in_required');

    const assessmentId = req.data?.assessmentId as string | undefined;
    if (!assessmentId) throw new HttpsError('invalid-argument', 'assessment_id_required');

    const db = getFirestore();
    const configSnap = await db.doc(`assessments/${assessmentId}`).get();
    if (!configSnap.exists) throw new HttpsError('not-found', 'assessment_not_found');

    const config = configSnap.data() as AssessmentConfig;

    // Check previous attempts
    const prevSnap = await db
      .collection('attempts')
      .where('uid', '==', uid)
      .where('assessmentId', '==', assessmentId)
      .get();

    const previous = prevSnap.docs.map((d) => d.data() as Attempt);
    const now = Date.now();
    const check = canStartAttempt({
      config: {
        maxAttempts: config.maxAttempts,
        retakeCooldownHours: config.retakeCooldownHours,
      },
      previous: previous.map((a) => ({
        status: a.status,
        submittedAt: a.submittedAt,
        passed: a.passed,
      })),
      nowMs: now,
    });

    if (!check.ok) {
      throw new HttpsError('failed-precondition', check.reason);
    }

    // Load questions
    const qIds = config.questionIds ?? [];
    if (qIds.length === 0) throw new HttpsError('failed-precondition', 'no_questions_configured');

    const qDocs = await Promise.all(qIds.map((id) => db.doc(`question_bank/${id}`).get()));
    const questions: Question[] = [];
    for (const qDoc of qDocs) {
      if (qDoc.exists) questions.push(qDoc.data() as Question);
    }

    // Randomize questions & choice order
    const rand = () => randomBytes(4).readUInt32LE(0) / 0xffffffff;
    const orderedQuestions = config.randomizeQuestions ? shuffle(questions, rand) : questions;

    const servedQuestions = orderedQuestions.map((q) => {
      const choiceCount = q.variants.en?.choices.length ?? 4;
      const choices = Array.from({ length: choiceCount }, (_, i) => i);
      const choiceOrder = config.randomizeChoices ? shuffle(choices, rand) : choices;
      return { questionId: q.questionId, choiceOrder };
    });

    const attemptId = `att_${Date.now()}_${randomBytes(4).toString('hex')}`;
    const expiresAt = config.timeLimitMinutes ? now + config.timeLimitMinutes * 60_000 : undefined;

    const attempt: Attempt = {
      attemptId,
      uid,
      assessmentId,
      courseId: config.courseId,
      startedAt: now,
      expiresAt,
      servedQuestions,
      status: 'in_progress',
    };

    await db.doc(`attempts/${attemptId}`).set(attempt);

    // Return questions with randomized choice orders but without correctChoiceIndexes
    const clientQuestions = orderedQuestions.map((q, idx) => {
      const order = servedQuestions[idx]!.choiceOrder;
      const variants: Question['variants'] = {};
      for (const [lang, val] of Object.entries(q.variants)) {
        if (val) {
          variants[lang as 'en' | 'hi' | 'pa'] = {
            stem: val.stem,
            choices: order.map((origIdx) => val.choices[origIdx] ?? ''),
            explanation: undefined, // Hidden until submitted
          };
        }
      }
      return {
        questionId: q.questionId,
        category: q.category,
        variants,
      };
    });

    return {
      attemptId,
      startedAt: now,
      expiresAt,
      timeLimitMinutes: config.timeLimitMinutes,
      questions: clientQuestions,
    };
  },
);

export const submitAssessmentAttempt = onCall(
  { region: REGION, maxInstances: 20 },
  async (req) => {
    const uid = req.auth?.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'sign_in_required');

    const attemptId = req.data?.attemptId as string | undefined;
    const responses = (req.data?.responses as Record<string, number[]>) ?? {};

    if (!attemptId) throw new HttpsError('invalid-argument', 'attempt_id_required');

    const db = getFirestore();
    const attemptRef = db.doc(`attempts/${attemptId}`);
    const attemptSnap = await attemptRef.get();
    if (!attemptSnap.exists) throw new HttpsError('not-found', 'attempt_not_found');

    const attempt = attemptSnap.data() as Attempt;
    if (attempt.uid !== uid) throw new HttpsError('permission-denied', 'wrong_owner');
    if (attempt.status !== 'in_progress') throw new HttpsError('failed-precondition', 'already_submitted');

    const configSnap = await db.doc(`assessments/${attempt.assessmentId}`).get();
    const config = configSnap.data() as AssessmentConfig;

    // Load actual answer keys from question_bank
    const qIds = attempt.servedQuestions.map((s) => s.questionId);
    const qSnaps = await Promise.all(qIds.map((id) => db.doc(`question_bank/${id}`).get()));
    const questionsMap = new Map<string, Pick<Question, 'questionId' | 'correctChoiceIndexes'>>();

    for (const qs of qSnaps) {
      if (qs.exists) {
        const q = qs.data() as Question;
        questionsMap.set(q.questionId, {
          questionId: q.questionId,
          correctChoiceIndexes: q.correctChoiceIndexes,
        });
      }
    }

    const now = Date.now();
    const scored = scoreAttempt({
      attempt,
      callerUid: uid,
      nowMs: now,
      config: {
        passPercent: config.passPercent,
        marksPerQuestion: config.marksPerQuestion,
        negativeMarks: config.negativeMarks,
      },
      questions: questionsMap,
      responses,
    });

    if (!scored.ok) {
      throw new HttpsError('failed-precondition', scored.error);
    }

    const { marks, maxMarks, scorePercent, passed, perQuestion } = scored.result;

    // Update attempt
    await attemptRef.update({
      responses,
      marks,
      maxMarks,
      scorePercent,
      passed,
      submittedAt: now,
      status: 'submitted',
    });

    let certificate: PortalCertificate | null = null;

    // Check certificate issuance eligibility if passed
    if (passed) {
      const candidateSnap = await db.doc(`candidates/${uid}`).get();
      const candidate = candidateSnap.data() as CandidateCore;
      const courseSnap = await db.doc(`courses/${attempt.courseId}`).get();
      const course = courseSnap.data();

      if (course?.certificateEnabled) {
        const certId = newCertificateId(new Date().getFullYear());
        const candidateName = candidate.fullName;
        const courseTitle = course.title?.en || 'Debt Collection Professional Training';

        certificate = {
          certificateId: certId,
          uid,
          candidateId: candidate.candidateId,
          candidateNameAtIssue: candidateName,
          courseId: attempt.courseId,
          courseTitleAtIssue: courseTitle,
          courseVersion: course.version ?? 1,
          scorePercent,
          grade: scorePercent >= 90 ? 'A+' : scorePercent >= 75 ? 'A' : 'Pass',
          issuedAt: now,
          attemptId,
          revoked: false,
          publicVerificationConsent: true,
        };

        const publicVerification: PublicCertificateVerification = {
          certificateId: certId,
          displayName: `${candidateName.split(' ')[0]} ${candidateName.split(' ').slice(1).map((n) => n[0] + '.').join(' ')}`.trim(),
          courseTitle,
          issuedOn: new Date(now).toISOString().slice(0, 10),
          valid: true,
          disclaimer: 'portal_training_not_iibf_dra',
        };

        const batch = db.batch();
        batch.set(db.doc(`certificates/${certId}`), certificate);
        batch.set(db.doc(`certificate_verification/${certId}`), publicVerification);
        await batch.commit();

        writeAudit({
          actorUid: uid,
          actorRole: 'system',
          action: 'certificate.issue',
          targetType: 'certificate',
          targetId: certId,
          meta: {
            courseId: attempt.courseId,
            scorePercent,
            candidateId: candidate.candidateId,
          },
        });
      }
    }

    return {
      success: true,
      marks,
      maxMarks,
      scorePercent,
      passed,
      perQuestion,
      certificate,
    };
  },
);
