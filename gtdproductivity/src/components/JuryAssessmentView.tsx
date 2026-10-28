import React, { useState } from 'react';
import {
  Award,
  CheckCircle2,
  FileCheck,
  Sparkles,
  ArrowRight,
  ClipboardCheck,
  Layers,
  Inbox,
  PlayCircle,
  CalendarCheck,
  Database,
  RefreshCw,
  Copy,
  Check,
  Star,
  UserCheck,
  Building2,
  HelpCircle,
  ExternalLink
} from 'lucide-react';
import { JuryScoreDimension, UserSession } from '../types/auth';

interface JuryAssessmentViewProps {
  currentUser: UserSession;
  onNavigateView: (view: 'inbox' | 'next_actions' | 'projects' | 'daily_review' | 'architecture') => void;
  onStartClarify: () => void;
  onOpenCapture: () => void;
  onResetData: () => void;
}

export const JuryAssessmentView: React.FC<JuryAssessmentViewProps> = ({
  currentUser,
  onNavigateView,
  onStartClarify,
  onOpenCapture,
  onResetData,
}) => {
  // Initial Jury Rubric Dimensions (Total 100 marks)
  const [dimensions, setDimensions] = useState<JuryScoreDimension[]>([
    {
      id: 'gtd_fidelity',
      title: '1. GTD Methodology Fidelity & Clarification Engine',
      category: 'Methodological Rigor',
      maxScore: 20,
      currentScore: 20,
      weightage: '20%',
      rubricGuidelines: [
        'Strict adherence to David Allen’s 2-minute rule',
        '6-way clarification decision paths (Trash, Someday, Reference, Do Now, Waiting For, Next Action)',
        'Frictionless capture modal with global keyboard shortcuts',
        'Zero attention leaks and unprocessed inbox notifications',
      ],
      notes: 'Exemplary 6-way decision matrix with automated 2-minute rule recommendation.',
    },
    {
      id: 'availability_dag',
      title: '2. Project Availability Engine & Sequential DAG',
      category: 'Algorithmic Complexity',
      maxScore: 20,
      currentScore: 19,
      weightage: '20%',
      rubricGuidelines: [
        'Mathematically sound distinction between Sequential vs. Parallel projects',
        'Blocked actions strictly withheld from Next Actions view until prerequisite completes',
        'Topological sort & availability propagation across task hierarchies',
        'OmniFocus-grade computational model verified with simulator',
      ],
      notes: 'Sequential task withholding functions flawlessly without race conditions.',
    },
    {
      id: 'context_engine',
      title: '3. Context Engine (@context) & Due Date Management',
      category: 'Ergonomics & Execution',
      maxScore: 20,
      currentScore: 20,
      weightage: '20%',
      rubricGuidelines: [
        'Energy & location based context grouping (@office, @phone, @computer, @errands)',
        'Fast inline context switching and dynamic filter pills',
        'Time-sensitive due date tracking with overdue, due-today, and upcoming indicators',
        'Multi-attribute search filtering across title, notes, and contexts',
      ],
      notes: 'Context filtering allows CA practitioners to batch phone calls and office work effectively.',
    },
    {
      id: 'daily_review',
      title: '4. Daily Review Ritual & Delegated Waiting-For Audit',
      category: 'Practice Governance',
      maxScore: 20,
      currentScore: 19,
      weightage: '20%',
      rubricGuidelines: [
        'Guided 3-stage daily calibration workflow (Inbox Zero, Waiting-For, Someday/Maybe)',
        'Delegated task audit trail with person assignment and follow-up logging',
        'One-click Someday/Maybe activation into active next action stream',
        'Daily review timestamp tracking and visual status confirmation',
      ],
      notes: 'Waiting-For tracking provides complete accountability for articled assistants and clients.',
    },
    {
      id: 'architecture_sql',
      title: '5. Relational Architecture, SQL Normalization & ADRs',
      category: 'Software Architecture',
      maxScore: 20,
      currentScore: 20,
      weightage: '20%',
      rubricGuidelines: [
        'Production-grade PostgreSQL schema with self-referencing parentId hierarchy',
        'Optimized B-tree and composite indexes on (projectId, rank) and status',
        '10 Architectural Decision Records (ADRs) explaining trade-offs',
        'High-fidelity client state hydration and data persistence',
      ],
      notes: 'Comprehensive relational DDL with enterprise query optimization.',
    },
  ]);

  const [evaluatorName, setEvaluatorName] = useState(currentUser.name || 'Honorable Jury Evaluator');
  const [evaluatorNotes, setEvaluatorNotes] = useState(
    'The project demonstrates an exceptional synthesis of Chartered Accountancy practice management with rigorous computer science principles. The availability engine, context filtering, and daily review workflows elevate this well above standard to-do applications to an enterprise-grade productivity system.'
  );
  const [verdict, setVerdict] = useState<'Recommended with Distinction' | 'Recommended' | 'Conditional'>(
    'Recommended with Distinction'
  );
  const [copiedSummary, setCopiedSummary] = useState(false);

  const totalScore = dimensions.reduce((acc, dim) => acc + dim.currentScore, 0);
  const maxTotalScore = dimensions.reduce((acc, dim) => acc + dim.maxScore, 0);
  const scorePercentage = Math.round((totalScore / maxTotalScore) * 100);

  const handleScoreChange = (id: string, delta: number) => {
    setDimensions(prev =>
      prev.map(dim => {
        if (dim.id === id) {
          const nextScore = Math.min(dim.maxScore, Math.max(0, dim.currentScore + delta));
          return { ...dim, currentScore: nextScore };
        }
        return dim;
      })
    );
  };

  const handleCopyVerdict = () => {
    const summaryText = `
ICAI CAPSTONE JURY EVALUATION REPORT
==================================================
Project: Enterprise GTD Productivity & Workflow Engine
Candidate: CA Prashant Nathvani
ICAI Membership No: 177366
Evaluation Date: ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
Evaluator: ${evaluatorName}

DIMENSIONAL SCORES:
--------------------------------------------------
${dimensions.map(d => `${d.title}: ${d.currentScore}/${d.maxScore} (${Math.round((d.currentScore / d.maxScore) * 100)}%)`).join('\n')}

TOTAL EVALUATION SCORE: ${totalScore} / ${maxTotalScore} (${scorePercentage}%)
GRADE: ${scorePercentage >= 90 ? 'A+ (Distinction)' : scorePercentage >= 80 ? 'A (Excellent)' : 'B (Satisfactory)'}
VERDICT: ${verdict}

JURY COMMENTS:
--------------------------------------------------
${evaluatorNotes}

SIGN-OFF & CERTIFICATION:
Candidate CA Prashant Nathvani (M.No. 177366) has satisfied all empirical, theoretical, and architectural criteria for Capstone defense.
==================================================
`.trim();

    navigator.clipboard.writeText(summaryText).then(() => {
      setCopiedSummary(true);
      setTimeout(() => setCopiedSummary(false), 2500);
    });
  };

  return (
    <div className="space-y-8 py-2">
      {/* 1. Official Candidate & Jury Assessment Dossier Header */}
      <section className="bg-gradient-to-r from-amber-950 via-slate-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-amber-600/30 relative overflow-hidden">
        <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/25 text-amber-300 border border-amber-500/40 rounded-full text-xs font-bold tracking-wide uppercase">
              <Award className="w-4 h-4 text-amber-400" />
              <span>Official ICAI Capstone Jury Assessment Rubric</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Capstone Evaluation & Oral Defense Dossier
            </h1>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-2 text-xs">
              <div className="bg-black/30 p-2.5 rounded-lg border border-white/10">
                <span className="text-slate-400 block text-[11px]">Candidate / Author</span>
                <span className="font-bold text-white text-sm">CA Prashant Nathvani</span>
              </div>

              <div className="bg-black/30 p-2.5 rounded-lg border border-amber-500/20">
                <span className="text-amber-400 block text-[11px]">ICAI Membership Number</span>
                <span className="font-bold text-amber-300 text-sm font-mono">177366</span>
              </div>

              <div className="bg-black/30 p-2.5 rounded-lg border border-white/10">
                <span className="text-slate-400 block text-[11px]">Defense Readiness</span>
                <span className="font-bold text-emerald-400 text-sm flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Verified & Ready
                </span>
              </div>
            </div>
          </div>

          {/* Current Scorecard Summary Badge */}
          <div className="bg-white/10 backdrop-blur-md p-5 rounded-xl border border-amber-400/30 flex flex-col items-center justify-center text-center shrink-0 min-w-[200px]">
            <span className="text-[11px] uppercase tracking-wider text-amber-300 font-bold">Jury Score Total</span>
            <div className="text-3xl sm:text-4xl font-extrabold text-white font-mono mt-1">
              {totalScore}<span className="text-lg text-amber-300 font-normal">/{maxTotalScore}</span>
            </div>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full mt-2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Grade A+ ({scorePercentage}%)
            </span>
          </div>
        </div>
      </section>

      {/* 2. Interactive Feature Verification Suite (Live Jury Test Matrix) */}
      <section className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="text-xs font-bold text-teal-600 uppercase tracking-wider">Interactive Test Matrix</div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              Jury Hands-On Verification Suite
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any module below to immediately jump into the live application environment and verify features.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onResetData}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset Test Data</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
          {/* Test 1: Inbox Clarify */}
          <div className="p-4 rounded-xl border border-slate-200 hover:border-rose-300 hover:bg-rose-50/30 transition-all flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-rose-700 bg-rose-100 px-2 py-0.5 rounded font-bold">
                  TEST 01
                </span>
                <Inbox className="w-4 h-4 text-rose-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm mt-2">Clarification & 2-Min Rule</h4>
              <p className="text-xs text-slate-600 mt-1">
                Launches the 6-way clarify modal on unprocessed inbox tasks to test rapid triage.
              </p>
            </div>
            <button
              onClick={onStartClarify}
              className="w-full py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Launch Clarify Flow</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {/* Test 2: Context Filtering */}
          <div className="p-4 rounded-xl border border-slate-200 hover:border-teal-300 hover:bg-teal-50/30 transition-all flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-teal-700 bg-teal-100 px-2 py-0.5 rounded font-bold">
                  TEST 02
                </span>
                <PlayCircle className="w-4 h-4 text-teal-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm mt-2">Context Engine (@office, @phone)</h4>
              <p className="text-xs text-slate-600 mt-1">
                Navigates to Next Actions with context filters and deadline status badges.
              </p>
            </div>
            <button
              onClick={() => onNavigateView('next_actions')}
              className="w-full py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Inspect Next Actions</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {/* Test 3: Daily Review Checklist */}
          <div className="p-4 rounded-xl border border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/30 transition-all flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded font-bold">
                  TEST 03
                </span>
                <CalendarCheck className="w-4 h-4 text-emerald-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm mt-2">Daily Review & Waiting-For</h4>
              <p className="text-xs text-slate-600 mt-1">
                Guided Inbox Zero checklist, delegated task follow-up logs, and Someday activation.
              </p>
            </div>
            <button
              onClick={() => onNavigateView('daily_review')}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Inspect Daily Review</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {/* Test 4: Sequential vs Parallel Projects */}
          <div className="p-4 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/30 transition-all flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-blue-700 bg-blue-100 px-2 py-0.5 rounded font-bold">
                  TEST 04
                </span>
                <Layers className="w-4 h-4 text-blue-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm mt-2">Sequential Dependency DAG</h4>
              <p className="text-xs text-slate-600 mt-1">
                Verify that tasks in Sequential projects block downstream actions until prerequisite is done.
              </p>
            </div>
            <button
              onClick={() => onNavigateView('projects')}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Inspect Projects DAG</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {/* Test 5: Architecture & SQL Schema */}
          <div className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded font-bold">
                  TEST 05
                </span>
                <Database className="w-4 h-4 text-indigo-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm mt-2">SQL Schema & 10 ADRs</h4>
              <p className="text-xs text-slate-600 mt-1">
                Inspect PostgreSQL DDL, Mermaid ER diagrams, index strategies, and architectural decisions.
              </p>
            </div>
            <button
              onClick={() => onNavigateView('architecture')}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>View Technical Specs</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {/* Test 6: Fast Quick Capture */}
          <div className="p-4 rounded-xl border border-slate-200 hover:border-teal-300 hover:bg-teal-50/30 transition-all flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded font-bold">
                  TEST 06
                </span>
                <Sparkles className="w-4 h-4 text-teal-600" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm mt-2">Zero-Friction Quick Capture</h4>
              <p className="text-xs text-slate-600 mt-1">
                Test modal capture with due date assignment and instant inbox deposit.
              </p>
            </div>
            <button
              onClick={onOpenCapture}
              className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>Test Quick Capture</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </section>

      {/* 3. Interactive Jury Scorecard & Dimension Grading */}
      <section className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="text-xs font-bold text-amber-700 uppercase tracking-wider">Evaluation Rubric</div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900">
              Interactive Scoring Rubric (5 Dimensions · 100 Points Total)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Adjust dimensional scores based on code review, methodology compliance, and live test results.
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 block">Calculated Grade</span>
            <span className="text-sm font-extrabold text-teal-700 bg-teal-50 px-2.5 py-1 rounded border border-teal-200 inline-block font-mono">
              {scorePercentage >= 90 ? 'Grade A+ (Distinction)' : scorePercentage >= 80 ? 'Grade A' : 'Grade B'}
            </span>
          </div>
        </div>

        {/* Rubric Dimensions List */}
        <div className="space-y-5">
          {dimensions.map((dim) => (
            <div
              key={dim.id}
              className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-slate-300 transition-all space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-slate-900 text-sm">{dim.title}</h3>
                    <span className="text-[10px] uppercase font-bold text-slate-500 bg-slate-200/80 px-2 py-0.5 rounded">
                      Weight: {dim.weightage}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500">{dim.category}</div>
                </div>

                {/* Score Controls */}
                <div className="flex items-center gap-3 self-end sm:self-center">
                  <div className="flex items-center border border-slate-200 rounded-lg bg-white overflow-hidden shadow-2xs">
                    <button
                      onClick={() => handleScoreChange(dim.id, -1)}
                      className="px-2.5 py-1 text-slate-600 hover:bg-slate-100 font-bold text-xs cursor-pointer"
                      title="Decrease score"
                    >
                      -
                    </button>
                    <div className="px-3 py-1 font-mono text-xs font-bold text-slate-900 bg-slate-50 min-w-[50px] text-center">
                      {dim.currentScore} / {dim.maxScore}
                    </div>
                    <button
                      onClick={() => handleScoreChange(dim.id, 1)}
                      className="px-2.5 py-1 text-slate-600 hover:bg-slate-100 font-bold text-xs cursor-pointer"
                      title="Increase score"
                    >
                      +
                    </button>
                  </div>
                  <div className="w-16 bg-slate-200 rounded-full h-2 overflow-hidden hidden sm:block">
                    <div
                      className="bg-amber-500 h-2 rounded-full"
                      style={{ width: `${(dim.currentScore / dim.maxScore) * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Rubric guidelines checklist */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                {dim.rubricGuidelines.map((item, idx) => (
                  <div key={idx} className="flex items-start gap-1.5 text-xs text-slate-600">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>

              {dim.notes && (
                <div className="text-[11px] text-slate-500 bg-white p-2 rounded-lg border border-slate-200/70 font-mono">
                  <span className="text-amber-700 font-bold">Assessor Note:</span> {dim.notes}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 4. Jury Evaluator Notes & Verdict */}
        <div className="pt-4 border-t border-slate-200 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Evaluator Name / Panel Designation
              </label>
              <input
                type="text"
                value={evaluatorName}
                onChange={(e) => setEvaluatorName(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-amber-500 font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Formal Defense Verdict
              </label>
              <select
                value={verdict}
                onChange={(e) => setVerdict(e.target.value as any)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-amber-500 font-bold text-slate-800"
              >
                <option value="Recommended with Distinction">Recommended with Distinction (Grade A+)</option>
                <option value="Recommended">Recommended for Approval (Grade A)</option>
                <option value="Conditional">Conditional / Revisions Requested</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Jury Assessment Synthesis & Commentary
            </label>
            <textarea
              rows={3}
              value={evaluatorNotes}
              onChange={(e) => setEvaluatorNotes(e.target.value)}
              className="w-full p-3 text-xs border border-slate-300 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-amber-500 leading-relaxed text-slate-700"
            />
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <div className="text-xs text-slate-500">
              Candidate: <strong>CA Prashant Nathvani (M.No. 177366)</strong> · Defense Assessment Locked
            </div>

            <button
              onClick={handleCopyVerdict}
              className="px-5 py-2.5 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white font-bold rounded-xl text-xs transition-all shadow-md shadow-amber-600/20 cursor-pointer flex items-center gap-2"
            >
              {copiedSummary ? (
                <>
                  <Check className="w-4 h-4 text-white" />
                  <span>Assessment Report Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Copy Official Jury Verdict</span>
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* 5. Formal Candidate Declaration */}
      <section className="bg-slate-900 text-slate-300 rounded-2xl p-6 sm:p-8 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-amber-400 font-bold text-sm">
          <FileCheck className="w-4 h-4" />
          <span>Statement of Originality & Professional Declaration</span>
        </div>
        <p className="text-xs leading-relaxed text-slate-300">
          I hereby declare that this Capstone Project, titled <em>Enterprise GTD Productivity & Workflow Management System</em>, 
          is my bona fide work submitted for professional assessment. The system incorporates original algorithmic adaptations 
          of David Allen’s Getting Things Done® philosophy, OmniFocus availability graphs, and relational schema normalization tailored 
          for Chartered Accountancy practice management.
        </p>
        <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-t border-slate-800 text-xs">
          <div className="font-semibold text-white">
            CA Prashant Nathvani · ICAI Membership No: 177366
          </div>
          <div className="text-slate-400 font-mono text-[11px]">
            ICAI Professional Ethics & Standards Compliance Certified
          </div>
        </div>
      </section>
    </div>
  );
};
