import pptxgen from 'pptxgenjs';

export interface CapstoneDeckMetadata {
  studentName: string;
  studentEmail: string;
  projectName: string;
  submissionDate: string;
  academicYear: string;
}

export const defaultDeckMetadata: CapstoneDeckMetadata = {
  studentName: 'Joydeep Datta',
  studentEmail: 'joydeep.datta@gmail.com',
  projectName: 'AI-Powered Indian Statutory Payroll & Tax Advisory Platform',
  submissionDate: new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
  academicYear: 'AY 2026–27',
};

/**
 * Generates an executive 10-slide PowerPoint deck for capstone submission.
 */
export async function generateCapstonePptx(metadata: CapstoneDeckMetadata = defaultDeckMetadata): Promise<void> {
  const pptx = new pptxgen();

  pptx.layout = 'LAYOUT_16x9';
  pptx.author = metadata.studentName;
  pptx.company = 'Capstone Project Submission';
  pptx.title = metadata.projectName;
  pptx.subject = 'Vibe Coding Capstone: Indian Statutory Payroll & AI Tax Advisory';

  // Palette definitions
  const NAVY = '0F172A';
  const INDIGO = '4338CA';
  const LIGHT_BG = 'F8FAFC';
  const CARD_BG = 'FFFFFF';
  const BORDER_COLOR = 'CBD5E1';
  const TEXT_DARK = '1E293B';
  const TEXT_MUTED = '64748B';
  const GREEN = '059669';
  const AMBER = 'D97706';
  const ROSE = 'E11D48';

  // Helper for slide header
  const addSlideHeader = (slide: any, title: string, category: string, slideNum: number) => {
    // Top banner
    slide.addShape(pptx.ShapeType.rect, {
      x: 0,
      y: 0,
      w: '100%',
      h: 0.9,
      fill: { color: NAVY },
    });

    slide.addText(category.toUpperCase(), {
      x: 0.8,
      y: 0.12,
      w: 8.5,
      h: 0.25,
      fontSize: 10,
      fontFace: 'Arial',
      bold: true,
      color: '818CF8',
    });

    slide.addText(title, {
      x: 0.8,
      y: 0.35,
      w: 10.5,
      h: 0.45,
      fontSize: 20,
      fontFace: 'Arial',
      bold: true,
      color: 'FFFFFF',
    });

    // Slide number
    slide.addText(`${slideNum} / 10`, {
      x: 11.5,
      y: 0.3,
      w: 1.5,
      h: 0.35,
      fontSize: 12,
      fontFace: 'Arial',
      bold: true,
      color: '94A3B8',
      align: 'right',
    });

    // Bottom subtle bar
    slide.addShape(pptx.ShapeType.rect, {
      x: 0,
      y: 7.2,
      w: '100%',
      h: 0.3,
      fill: { color: 'F1F5F9' },
    });

    slide.addText(`Capstone Project | ${metadata.projectName} | ${metadata.studentName}`, {
      x: 0.8,
      y: 7.22,
      w: 11.5,
      h: 0.25,
      fontSize: 9,
      fontFace: 'Arial',
      color: TEXT_MUTED,
    });
  };

  // ==========================================
  // SLIDE 1: TITLE SLIDE
  // ==========================================
  {
    const slide = pptx.addSlide();
    slide.background = { color: NAVY };

    // Decorative shape
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.8,
      y: 0.8,
      w: 1.8,
      h: 0.35,
      fill: { color: '312E81' },
      line: { color: '6366F1', width: 1 },
    });
    slide.addText('CAPSTONE SUBMISSION', {
      x: 0.8,
      y: 0.82,
      w: 1.8,
      h: 0.3,
      fontSize: 10,
      fontFace: 'Arial',
      bold: true,
      color: 'A5B4FC',
      align: 'center',
    });

    slide.addText('Next-Gen Indian Statutory Payroll & AI Tax Advisory System', {
      x: 0.8,
      y: 1.5,
      w: 11.5,
      h: 1.4,
      fontSize: 34,
      fontFace: 'Arial',
      bold: true,
      color: 'FFFFFF',
    });

    slide.addText(
      'An enterprise-grade, deterministic dual-regime payroll engine paired with a multi-model Google Gemini tax copilot built using Vibe Coding methodology.',
      {
        x: 0.8,
        y: 3.1,
        w: 11.0,
        h: 0.9,
        fontSize: 16,
        fontFace: 'Arial',
        color: '94A3B8',
        lineSpacingMultiple: 1.2,
      }
    );

    // Meta card
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: 4.4,
      w: 11.5,
      h: 2.2,
      fill: { color: '1E293B' },
      line: { color: '334155', width: 1 },
      rectRadius: 0.1,
    });

    slide.addText(
      [
        { text: 'Author / Candidate:\n', options: { bold: true, color: '818CF8', fontSize: 11 } },
        { text: `${metadata.studentName}\n`, options: { bold: true, color: 'FFFFFF', fontSize: 16 } },
        { text: `${metadata.studentEmail}\n\n`, options: { color: '94A3B8', fontSize: 12 } },
        { text: 'Engineering Discipline:\n', options: { bold: true, color: '818CF8', fontSize: 11 } },
        { text: 'Full-Stack Vibe Coding & LLM Systems Engineering\n', options: { color: 'FFFFFF', fontSize: 13 } },
      ],
      { x: 1.2, y: 4.6, w: 5.2, h: 1.8, fontFace: 'Arial' }
    );

    slide.addText(
      [
        { text: 'Statutory Scope:\n', options: { bold: true, color: '818CF8', fontSize: 11 } },
        { text: `Indian Income Tax Act (AY 2026–27) & EPF / ESI / PT Rules\n\n`, options: { color: 'FFFFFF', fontSize: 13 } },
        { text: 'Tech Stack:\n', options: { bold: true, color: '818CF8', fontSize: 11 } },
        { text: 'React 19 + TypeScript + Express + Google Gen AI SDK (@google/genai)\n', options: { color: '34D399', fontSize: 12, bold: true } },
        { text: `Date: ${metadata.submissionDate}`, options: { color: '94A3B8', fontSize: 11 } },
      ],
      { x: 6.8, y: 4.6, w: 5.2, h: 1.8, fontFace: 'Arial' }
    );

    slide.addNotes(
      'Slide 1 Speaker Notes:\nWelcome evaluation committee. Today I present my Capstone project: an enterprise-grade Indian Statutory Payroll and AI Tax Advisory platform. This application addresses one of the most mathematically intricate domains in Indian fintech—dual-regime taxation, statutory caps, and monthly TDS smoothing—paired with Google Gemini AI for personalized employee advisory.'
    );
  }

  // ==========================================
  // SLIDE 2: PROBLEM STATEMENT & DOMAIN COMPLEXITY
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'Problem Statement: The Indian Payroll & Tax Dilemma', '1. Context & Objectives', 2);

    // Box 1: Statutory Complexity
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Statutory Maze', {
      x: 1.1,
      y: 1.4,
      w: 3.1,
      h: 0.4,
      fontSize: 16,
      fontFace: 'Arial',
      bold: true,
      color: INDIGO,
    });
    slide.addText(
      [
        { text: '• Dual Tax Regimes:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Employees can elect Old Regime or New Regime for AY 2026-27, each with distinct slab rates, standard deductions (₹75k vs ₹50k), and rebate caps (Sec 87A).\n\n', options: { color: TEXT_MUTED } },
        { text: '• Statutory Deduction Rules:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'EPF mandatory 12% with optional ₹15,000 wage ceiling; ESI applicable if gross ≤ ₹21,000; State-specific Professional Tax (PT) slabs.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Complex HRA Exemption:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Section 10(13A) requires evaluating minimum of 3 dynamic conditions across metro/non-metro cities.', options: { color: TEXT_MUTED } },
      ],
      { x: 1.1, y: 1.9, w: 3.1, h: 4.6, fontSize: 11, fontFace: 'Arial' }
    );

    // Box 2: Employee Pain Points
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 4.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Employee Pain Points', {
      x: 5.1,
      y: 1.4,
      w: 3.1,
      h: 0.4,
      fontSize: 16,
      fontFace: 'Arial',
      bold: true,
      color: ROSE,
    });
    slide.addText(
      [
        { text: '• Regret of Wrong Regime Choice:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Employees lock in the wrong tax regime at the start of the year and pay tens of thousands in extra TDS without clear visibility.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Last-Minute Tax Panic:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Scrambling in Jan–March to submit Chapter VI-A investment proofs without knowing exact marginal tax benefits.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Lack of Personalized Guidance:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'HR teams lack the bandwidth to advise hundreds of employees individually on salary structuring.', options: { color: TEXT_MUTED } },
      ],
      { x: 5.1, y: 1.9, w: 3.1, h: 4.6, fontSize: 11, fontFace: 'Arial' }
    );

    // Box 3: Solution Vision
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 8.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('The Capstone Solution', {
      x: 9.1,
      y: 1.4,
      w: 3.1,
      h: 0.4,
      fontSize: 16,
      fontFace: 'Arial',
      bold: true,
      color: GREEN,
    });
    slide.addText(
      [
        { text: '• Deterministic Precision:\n', options: { bold: true, color: TEXT_DARK } },
        { text: '100% auditable TypeScript calculations for salary registers, calendar proration, and cumulative TDS smoothing.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Gemini AI Tax Advisory:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Generative AI analyzes individual compensation breakdown and gives proactive, customized tax-saving recommendations.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Unified Dual-Portal UX:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Single seamless SPA serving both HR Administrators (bulk runs, Excel upload) and Employees (payslips, tax simulator).', options: { color: TEXT_MUTED } },
      ],
      { x: 9.1, y: 1.9, w: 3.1, h: 4.6, fontSize: 11, fontFace: 'Arial' }
    );

    slide.addNotes(
      'Slide 2 Speaker Notes:\nIndian payroll is uniquely complex due to the coexistence of the Old and New tax regimes for AY 2026-27. Employees often struggle to choose the best regime. The goal of this capstone project was to eliminate this friction by pairing rigorous deterministic tax algorithms with natural language AI advisory.'
    );
  }

  // ==========================================
  // SLIDE 3: SYSTEM ARCHITECTURE & TECH STACK
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'System Architecture & Full-Stack Tech Stack', '2. System Engineering', 3);

    // Architecture columns
    // Column 1: Client Frontend
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: 'F0FDF4' },
      line: { color: 'BBF7D0', width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Frontend Client (SPA)', {
      x: 1.1,
      y: 1.4,
      w: 3.1,
      h: 0.35,
      fontSize: 15,
      fontFace: 'Arial',
      bold: true,
      color: '166534',
    });
    slide.addText(
      [
        { text: '• Framework:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'React 19 + TypeScript (Strict mode)\n\n', options: { color: TEXT_MUTED } },
        { text: '• Bundler & Build:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Vite 6 with Hot Module Replacement\n\n', options: { color: TEXT_MUTED } },
        { text: '• Design System:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Tailwind CSS v4, Lucide Icons, Accessible Form controls\n\n', options: { color: TEXT_MUTED } },
        { text: '• Client-Side Engines:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Deterministic taxEngine.ts, payrollEngine.ts, real-time reactive state', options: { color: TEXT_MUTED } },
      ],
      { x: 1.1, y: 1.9, w: 3.1, h: 4.6, fontSize: 11, fontFace: 'Arial' }
    );

    // Column 2: Backend & Proxy
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 4.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: 'EEF2FF' },
      line: { color: 'C7D2FE', width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Server & AI Proxy', {
      x: 5.1,
      y: 1.4,
      w: 3.1,
      h: 0.35,
      fontSize: 15,
      fontFace: 'Arial',
      bold: true,
      color: '3730A3',
    });
    slide.addText(
      [
        { text: '• Runtime:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Node.js with Express & tsx runtime\n\n', options: { color: TEXT_MUTED } },
        { text: '• Secure AI Gateway:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Encapsulated /api/ai/tax-optimize and /api/ai/tax-ask endpoints\n\n', options: { color: TEXT_MUTED } },
        { text: '• Secret Isolation:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Zero exposure of GEMINI_API_KEY to browser bundle\n\n', options: { color: TEXT_MUTED } },
        { text: '• Resilience Circuit:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Model tier cascading + per-request timeout abort controllers', options: { color: TEXT_MUTED } },
      ],
      { x: 5.1, y: 1.9, w: 3.1, h: 4.6, fontSize: 11, fontFace: 'Arial' }
    );

    // Column 3: AI & Data Services
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 8.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: 'FFFBEB' },
      line: { color: 'FDE68A', width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('AI & Data Integrations', {
      x: 9.1,
      y: 1.4,
      w: 3.1,
      h: 0.35,
      fontSize: 15,
      fontFace: 'Arial',
      bold: true,
      color: '92400E',
    });
    slide.addText(
      [
        { text: '• Google Gen AI SDK:\n', options: { bold: true, color: TEXT_DARK } },
        { text: '@google/genai with gemini-flash-latest, 3.1-flash-lite, 3.8-flash\n\n', options: { color: TEXT_MUTED } },
        { text: '• Excel IO Pipeline:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'xlsx engine for template generation, bulk upload, and multi-sheet export\n\n', options: { color: TEXT_MUTED } },
        { text: '• Document Rendering:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'html2canvas + jspdf for high-resolution digital payslip PDFs\n\n', options: { color: TEXT_MUTED } },
        { text: '• PowerPoint Engine:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'pptxgenjs for client-side programmatic presentation compilation', options: { color: TEXT_MUTED } },
      ],
      { x: 9.1, y: 1.9, w: 3.1, h: 4.6, fontSize: 11, fontFace: 'Arial' }
    );

    slide.addNotes(
      'Slide 3 Speaker Notes:\nHere is the full-stack architectural blueprint. The application is built using React 19 and Vite on the client side, with a Node.js/Express backend that acts as a secure reverse proxy to the Google Gen AI API. All sensitive API keys are kept on the server, and data export features include Excel, PDF payslips, and this PowerPoint deck.'
    );
  }

  // ==========================================
  // SLIDE 4: CORE CAPABILITIES DELIVERED
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'Core Application Modules & Feature Deliverables', '3. What Has Been Done', 4);

    const modules = [
      {
        title: '1. Master Salary Structuring',
        desc: 'Complete CTC breakdown into Basic, HRA, Conveyance, Education, LTA, Special & Other allowances. Configurable PF application toggle & ₹15k wage ceiling lock.',
        color: INDIGO,
      },
      {
        title: '2. Monthly Payroll Run & Register',
        desc: 'Interactive month-by-month payroll engine (April–March). Auto-computes gross-to-net, EPF (12% split into EPF + EPS), ESI, state PT, and progressive monthly TDS.',
        color: GREEN,
      },
      {
        title: '3. Employee Self-Service (ESS)',
        desc: 'Dual-role portal enabling employees to view real-time compensation, download official sealed PDF payslips, and submit regime preference with declaration locks.',
        color: AMBER,
      },
      {
        title: '4. Declarations & Audit Workflow',
        desc: 'Comprehensive Chapter VI-A investment declaration (80C, 80D, 80CCD NPS, 80E, 80G, 80TTA), HRA rent paid with landlord PAN validation, and Sec 24b home loan interest.',
        color: '0891B2',
      },
      {
        title: '5. Interactive Tax Simulator',
        desc: 'Live what-if scenario testing. Dynamic sliders for annual CTC, rent paid, and 80C/NPS investments with instant side-by-side Old vs New regime net take-home calculation.',
        color: '7C3AED',
      },
      {
        title: '6. Gemini AI Advisor & Copilot',
        desc: 'Deep statutory AI analysis offering bespoke tax optimization suggestions, investment reallocation advice, and an interactive Copilot conversational drawer.',
        color: ROSE,
      },
    ];

    modules.forEach((mod, idx) => {
      const col = idx % 3;
      const row = Math.floor(idx / 3);
      const x = 0.8 + col * 4.0;
      const y = 1.3 + row * 2.8;

      slide.addShape(pptx.ShapeType.roundRect, {
        x,
        y,
        w: 3.7,
        h: 2.5,
        fill: { color: CARD_BG },
        line: { color: BORDER_COLOR, width: 1 },
        rectRadius: 0.1,
      });

      slide.addShape(pptx.ShapeType.rect, {
        x: x + 0.3,
        y: y + 0.25,
        w: 0.2,
        h: 0.3,
        fill: { color: mod.color },
      });

      slide.addText(mod.title, {
        x: x + 0.6,
        y: y + 0.22,
        w: 2.9,
        h: 0.38,
        fontSize: 13,
        fontFace: 'Arial',
        bold: true,
        color: TEXT_DARK,
      });

      slide.addText(mod.desc, {
        x: x + 0.3,
        y: y + 0.75,
        w: 3.1,
        h: 1.6,
        fontSize: 10.5,
        fontFace: 'Arial',
        color: TEXT_MUTED,
        lineSpacingMultiple: 1.15,
      });
    });

    slide.addNotes(
      'Slide 4 Speaker Notes:\nSix production-grade modules were designed and implemented. From master employee onboarding and multi-month payroll runs to self-service payslip generation and real-time tax simulation, each module is fully functional and responsive.'
    );
  }

  // ==========================================
  // SLIDE 5: DETERMINISTIC TAX & PAYROLL ENGINE
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'Deep Dive: Deterministic Statutory Indian Tax Engine', '4. Core Logic & Precision', 5);

    // Left card: Mathematical Slabs
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: 1.2,
      w: 5.6,
      h: 5.6,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Statutory Tax Regimes (AY 2026–27)', {
      x: 1.1,
      y: 1.4,
      w: 5.0,
      h: 0.35,
      fontSize: 15,
      fontFace: 'Arial',
      bold: true,
      color: INDIGO,
    });

    slide.addText(
      [
        { text: 'New Tax Regime (Default u/s 115BAC):\n', options: { bold: true, color: TEXT_DARK } },
        { text: '• ₹0 – ₹3,00,000: NIL\n• ₹3,00,001 – ₹7,00,000: 5%\n• ₹7,00,001 – ₹10,00,000: 10%\n• ₹10,00,001 – ₹12,00,000: 15%\n• ₹12,00,001 – ₹15,00,000: 20%\n• Above ₹15,00,000: 30%\n• Standard Deduction: ₹75,000 (Budget 2024 enhancement)\n• Full tax rebate u/s 87A up to ₹7,00,000 net income.\n\n', options: { color: TEXT_MUTED, fontSize: 10.5 } },
        { text: 'Old Tax Regime (Elective):\n', options: { bold: true, color: TEXT_DARK } },
        { text: '• ₹0 – ₹2,50,000: NIL | ₹2.5L – ₹5L: 5% | ₹5L – ₹10L: 20% | >₹10L: 30%\n• Standard Deduction: ₹50,000\n• Chapter VI-A deductions: 80C (₹1.5L), 80D (₹25k/₹50k), 80CCD(1B) NPS (₹50k)\n• Health & Education Cess: 4% applied across both regimes.', options: { color: TEXT_MUTED, fontSize: 10.5 } },
      ],
      { x: 1.1, y: 1.85, w: 5.0, h: 4.7, fontFace: 'Arial' }
    );

    // Right card: Algorithmic Precision
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 6.8,
      y: 1.2,
      w: 5.7,
      h: 5.6,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Key Algorithmic Implementations', {
      x: 7.1,
      y: 1.4,
      w: 5.1,
      h: 0.35,
      fontSize: 15,
      fontFace: 'Arial',
      bold: true,
      color: GREEN,
    });

    slide.addText(
      [
        { text: '1. Three-Fold HRA Exemption Formula:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Exempt HRA = min(\n  a) Actual HRA received,\n  b) Rent paid - 10% of basic salary,\n  c) 50% (Metro) or 40% (Non-Metro) of basic salary\n)\n\n', options: { color: '0F766E', fontFace: 'Courier New', fontSize: 9.5 } },
        { text: '2. Progressive Monthly TDS Smoothing:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'TDS_Current_Month = (Projected_Annual_Tax - Cumulative_TDS_Paid) / Remaining_Months_in_FY\nEnsures smooth monthly cash flow without year-end deduction shock.\n\n', options: { color: TEXT_MUTED, fontSize: 10.5 } },
        { text: '3. Why Deterministic Engine in Pure TypeScript?\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'LLMs must NEVER calculate legal tax liability or bank deductions. Pure deterministic math guarantees 100% auditability and zero hallucination risk.', options: { color: TEXT_MUTED, fontSize: 10.5 } },
      ],
      { x: 7.1, y: 1.85, w: 5.1, h: 4.7, fontFace: 'Arial' }
    );

    slide.addNotes(
      'Slide 5 Speaker Notes:\nStatutory precision is paramount. The core payroll formulas are implemented deterministically in TypeScript. We model AY 2026-27 rules, including the enhanced ₹75,000 standard deduction under the New Regime, HRA 3-rule min calculation, and monthly TDS smoothing over remaining months.'
    );
  }

  // ==========================================
  // SLIDE 6: GEMINI AI ARCHITECTURE & RESILIENCE
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'Google Gemini AI Integration & Circuit-Breaker Architecture', '5. AI Advisory', 6);

    // Flow diagram boxes
    const steps = [
      {
        title: '1. Structured Context Ingestion',
        body: 'Server constructs a sanitised statutory prompt combining employee CTC components, declared investments, and deterministic tax figures from oldBreakdown & newBreakdown.',
      },
      {
        title: '2. Multi-Model Tier Fallback',
        body: 'Cascades through Gemini models via @google/genai SDK: gemini-flash-latest -> gemini-3.1-flash-lite -> gemini-3.8-flash for optimal speed and reliability.',
      },
      {
        title: '3. Circuit Breaker & Timeout Guards',
        body: '12-second abort timeout per call. If network latency spikes, the system automatically falls back to an expert rule-based chartered accountant guidance engine.',
      },
      {
        title: '4. Dual User Interfaces',
        body: 'Embedded Smart Tax Advisor tab (with structured JSON cards) + Persistent Floating AI Tax Copilot drawer accessible from any tab in the application.',
      },
    ];

    steps.forEach((step, idx) => {
      const y = 1.3 + idx * 1.35;
      slide.addShape(pptx.ShapeType.roundRect, {
        x: 0.8,
        y,
        w: 11.7,
        h: 1.15,
        fill: { color: idx % 2 === 0 ? 'F8FAFC' : CARD_BG },
        line: { color: BORDER_COLOR, width: 1 },
        rectRadius: 0.08,
      });

      slide.addShape(pptx.ShapeType.rect, {
        x: 1.0,
        y: y + 0.2,
        w: 0.2,
        h: 0.75,
        fill: { color: idx === 1 ? INDIGO : idx === 2 ? AMBER : idx === 3 ? GREEN : '64748B' },
      });

      slide.addText(step.title, {
        x: 1.4,
        y: y + 0.15,
        w: 10.8,
        h: 0.3,
        fontSize: 13,
        fontFace: 'Arial',
        bold: true,
        color: TEXT_DARK,
      });

      slide.addText(step.body, {
        x: 1.4,
        y: y + 0.48,
        w: 10.8,
        h: 0.55,
        fontSize: 11,
        fontFace: 'Arial',
        color: TEXT_MUTED,
        lineSpacingMultiple: 1.15,
      });
    });

    slide.addNotes(
      'Slide 6 Speaker Notes:\nOur AI integration uses the official @google/genai SDK on the server side. Notice our multi-tier fallback architecture: we attempt high-throughput models first, and if an upstream timeout occurs, a local deterministic statutory CA fallback responds instantly. The user experience is never blocked or frozen.'
    );
  }

  // ==========================================
  // SLIDE 7: VIBE CODING METHODOLOGY
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'Vibe Coding Methodology: From Idea to Enterprise Prototype', '6. Methodology', 7);

    // Left card: The Vibe Coding Workflow
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: 1.2,
      w: 5.6,
      h: 5.6,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('The Vibe Coding Paradigm', {
      x: 1.1,
      y: 1.4,
      w: 5.0,
      h: 0.35,
      fontSize: 15,
      fontFace: 'Arial',
      bold: true,
      color: INDIGO,
    });

    slide.addText(
      [
        { text: 'What is Vibe Coding in Practice?\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Vibe coding is high-velocity, intent-driven software development where natural language prompts and domain specifications guide the generation, testing, and continuous refinement of production software.\n\n', options: { color: TEXT_MUTED } },
        { text: 'Key Phases in This Project:\n', options: { bold: true, color: TEXT_DARK } },
        { text: '1. Domain Modeling: Codified statutory Indian tax rules and EPF/ESI formulas into robust TypeScript interfaces.\n2. Iterative Component Architecture: Created modular tabs for Salary Register, Master, Declarations, and Simulator.\n3. Frictionless UX Polish: Designed zero-pill cards, clear contrast input controls, and smooth modal flows.\n4. Edge-Case Hardening: Solved browser keyboard handling, input clearing, and API resilience.', options: { color: TEXT_MUTED } },
      ],
      { x: 1.1, y: 1.85, w: 5.0, h: 4.7, fontSize: 11, fontFace: 'Arial' }
    );

    // Right card: Engineering Discipline
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 6.8,
      y: 1.2,
      w: 5.7,
      h: 5.6,
      fill: { color: CARD_BG },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Discipline & Code Quality Controls', {
      x: 7.1,
      y: 1.4,
      w: 5.1,
      h: 0.35,
      fontSize: 15,
      fontFace: 'Arial',
      bold: true,
      color: GREEN,
    });

    slide.addText(
      [
        { text: '• 100% Strict TypeScript Typing:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Zero `any` shortcuts in payroll calculations; comprehensive interfaces for EmployeeMaster, EmployeeDeclaration, and MonthlySalaryRecord.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Automated Lint & Build Verification:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Every change was validated with tsc --noEmit and Vite production compilation, maintaining zero build errors.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Clean Code Boundaries:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Strict separation of concerns between presentation components, pure utility calculation functions, and server-side API proxy routes.', options: { color: TEXT_MUTED } },
      ],
      { x: 7.1, y: 1.85, w: 5.1, h: 4.7, fontSize: 11, fontFace: 'Arial' }
    );

    slide.addNotes(
      'Slide 7 Speaker Notes:\nAs my first vibe coding project, this experience demonstrated how pairing conversational LLM iteration with strict TypeScript typing, continuous compilation checks, and domain rigor allows a solo developer to build software that previously required a full engineering squad.'
    );
  }

  // ==========================================
  // SLIDE 8: DATA SECURITY & PRIVACY ASSESSMENT
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'Data Security, Confidentiality & Privacy Architecture', '7. Security Review', 8);

    // Card 1: Strengths
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: 'F0FDF4' },
      line: { color: '86EFAC', width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Current Security Strengths', {
      x: 1.1,
      y: 1.4,
      w: 3.1,
      h: 0.35,
      fontSize: 14,
      fontFace: 'Arial',
      bold: true,
      color: '166534',
    });
    slide.addText(
      [
        { text: '• Server-Isolated Secrets:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'GEMINI_API_KEY is strictly bound to Node.js backend; never exposed to browser or bundled in Vite assets.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Deterministic Math Integrity:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Core statutory calculations executed in code, preventing AI prompt injection from corrupting bank payout amounts.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Graceful Degradation:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Timeout controls prevent denial of service from sluggish upstream AI requests.', options: { color: TEXT_MUTED } },
      ],
      { x: 1.1, y: 1.85, w: 3.1, h: 4.7, fontSize: 10.5, fontFace: 'Arial' }
    );

    // Card 2: Vulnerabilities & Gaps
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 4.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: 'FFF1F2' },
      line: { color: 'FECDD3', width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Prototype Security Gaps', {
      x: 5.1,
      y: 1.4,
      w: 3.1,
      h: 0.35,
      fontSize: 14,
      fontFace: 'Arial',
      bold: true,
      color: '9F1239',
    });
    slide.addText(
      [
        { text: '• Client-Side Session State:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Role switching (Admin vs Employee) is handled in memory. Susceptible to client state tampering in DevTools.\n\n', options: { color: TEXT_MUTED } },
        { text: '• BOLA / IDOR Exposure:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'AI proxy routes accept employee objects directly in request body without verifying server-side session identity.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Unencrypted PII at Rest:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'PAN numbers and salary declarations are not encrypted with Field-Level Encryption (FLE).', options: { color: TEXT_MUTED } },
      ],
      { x: 5.1, y: 1.85, w: 3.1, h: 4.7, fontSize: 10.5, fontFace: 'Arial' }
    );

    // Card 3: Regulatory Compliance
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 8.8,
      y: 1.2,
      w: 3.7,
      h: 5.6,
      fill: { color: 'F8FAFC' },
      line: { color: BORDER_COLOR, width: 1 },
      rectRadius: 0.1,
    });
    slide.addText('Statutory & Compliance Rules', {
      x: 9.1,
      y: 1.4,
      w: 3.1,
      h: 0.35,
      fontSize: 14,
      fontFace: 'Arial',
      bold: true,
      color: INDIGO,
    });
    slide.addText(
      [
        { text: '• India DPDP Act 2023:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Payroll contains sensitive personal data (bank details, salary, PAN). Requires consent management and purpose limitation.\n\n', options: { color: TEXT_MUTED } },
        { text: '• Income Tax Act 1961:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Section 192 mandates accurate TDS deduction and quarterly Form 24Q filing with quarterly certificates (Form 16).\n\n', options: { color: TEXT_MUTED } },
        { text: '• Tamper-Evident Audit Trails:\n', options: { bold: true, color: TEXT_DARK } },
        { text: 'Requires immutable logs for any salary revision, tax regime lock, or rent declaration proof approval.', options: { color: TEXT_MUTED } },
      ],
      { x: 9.1, y: 1.85, w: 3.1, h: 4.7, fontSize: 10.5, fontFace: 'Arial' }
    );

    slide.addNotes(
      'Slide 8 Speaker Notes:\nThis slide directly addresses the security posture. While our prototype isolates API secrets and uses deterministic calculation logic, real-world enterprise deployment requires eliminating BOLA vulnerabilities, adding server-side JWT auth, and complying with the Indian DPDP Act.'
    );
  }

  // ==========================================
  // SLIDE 9: PRODUCTION READINESS CHECKLIST
  // ==========================================
  {
    const slide = pptx.addSlide();
    addSlideHeader(slide, 'Production Readiness Checklist & Deployment Roadmap', '8. Enterprise Readiness', 9);

    // Checklist table
    const tableData = [
      [
        { text: 'Domain Pillar', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF' } },
        { text: 'Required Enterprise Control', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF' } },
        { text: 'Current Status', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF' } },
        { text: 'Target Implementation', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF' } },
      ],
      [
        { text: 'Authentication', options: { bold: true, color: TEXT_DARK } },
        { text: 'Enterprise SSO (SAML 2.0 / OIDC) + Multi-Factor Authentication', options: { color: TEXT_MUTED } },
        { text: 'Mock / In-Memory', options: { color: AMBER, bold: true } },
        { text: 'Firebase Auth or Okta / Azure AD with HttpOnly cookies', options: { color: TEXT_DARK } },
      ],
      [
        { text: 'Authorization', options: { bold: true, color: TEXT_DARK } },
        { text: 'Server-side Role-Based Access Control (RBAC) & tenant isolation', options: { color: TEXT_MUTED } },
        { text: 'Client Guarded', options: { color: ROSE, bold: true } },
        { text: 'Express middleware verifying JWT claim on every /api request', options: { color: TEXT_DARK } },
      ],
      [
        { text: 'Data Persistence', options: { bold: true, color: TEXT_DARK } },
        { text: 'Relational database with AES-256 encryption at rest', options: { color: TEXT_MUTED } },
        { text: 'In-Memory / Local', options: { color: ROSE, bold: true } },
        { text: 'PostgreSQL on Cloud SQL with Drizzle ORM schemas', options: { color: TEXT_DARK } },
      ],
      [
        { text: 'PII Protection', options: { bold: true, color: TEXT_DARK } },
        { text: 'Field-Level Encryption (FLE) for PAN, Aadhaar & Bank Accounts', options: { color: TEXT_MUTED } },
        { text: 'Plaintext Masked in UI', options: { color: AMBER, bold: true } },
        { text: 'KMS-backed column encryption and audit masking', options: { color: TEXT_DARK } },
      ],
      [
        { text: 'Audit Logging', options: { bold: true, color: TEXT_DARK } },
        { text: 'Append-only immutable audit ledger for payroll runs & approvals', options: { color: TEXT_MUTED } },
        { text: 'Config SHA256 Hash', options: { color: GREEN, bold: true } },
        { text: 'Full write-once event streaming for all salary adjustments', options: { color: TEXT_DARK } },
      ],
      [
        { text: 'Infrastructure', options: { bold: true, color: TEXT_DARK } },
        { text: 'Containerized deployment with auto-scaling & Cloudflare WAF', options: { color: TEXT_MUTED } },
        { text: 'Docker / Cloud Run', options: { color: GREEN, bold: true } },
        { text: 'Multi-region failover with rate limiting & DDoS protection', options: { color: TEXT_DARK } },
      ],
    ];

    slide.addTable(tableData, {
      x: 0.8,
      y: 1.25,
      w: 11.7,
      h: 5.5,
      fontSize: 10,
      fontFace: 'Arial',
      border: { pt: 1, color: BORDER_COLOR },
      margin: [6, 8, 6, 8],
    });

    slide.addNotes(
      'Slide 9 Speaker Notes:\nHere is our comprehensive Production Readiness Checklist across six pillars: Authentication, Authorization, Persistence, PII Protection, Audit Logging, and Infrastructure. This roadmap outlines the exact engineering milestones required before deploying to production.'
    );
  }

  // ==========================================
  // SLIDE 10: CONCLUSION & CAPSTONE IMPACT
  // ==========================================
  {
    const slide = pptx.addSlide();
    slide.background = { color: NAVY };

    slide.addShape(pptx.ShapeType.rect, {
      x: 0.8,
      y: 0.8,
      w: 1.8,
      h: 0.35,
      fill: { color: '312E81' },
      line: { color: '6366F1', width: 1 },
    });
    slide.addText('CONCLUSION & FUTURE SCOPE', {
      x: 0.8,
      y: 0.82,
      w: 1.8,
      h: 0.3,
      fontSize: 10,
      fontFace: 'Arial',
      bold: true,
      color: 'A5B4FC',
      align: 'center',
    });

    slide.addText('Capstone Project Summary & Key Learnings', {
      x: 0.8,
      y: 1.4,
      w: 11.5,
      h: 0.6,
      fontSize: 26,
      fontFace: 'Arial',
      bold: true,
      color: 'FFFFFF',
    });

    // 3 Impact Cards
    const summaryPoints = [
      {
        title: 'Project Achievements',
        bullets: [
          'Engineered full-stack dual-regime payroll engine for AY 2026-27.',
          'Built 6 core functional modules with dual HR & Employee views.',
          'Implemented resilient Google Gemini AI advisory with CA fallback.',
          'Integrated multi-format exports: Excel, PDF payslips, PPTX deck.',
        ],
        color: '818CF8',
      },
      {
        title: 'Vibe Coding Takeaways',
        bullets: [
          'Conversational specifications accelerate complex UI/UX prototyping.',
          'Strict TypeScript interfaces prevent domain logic drift.',
          'Zero-hallucination rule: keep legal math in deterministic code.',
          'Continuous compilation catches edge cases instantly.',
        ],
        color: '34D399',
      },
      {
        title: 'Future Roadmap',
        bullets: [
          'Direct bank integration for automated NEFT/NACH salary disbursement.',
          'Automated government Form 16 Part A & B PDF generator.',
          'Biometric attendance API sync with automated loss-of-pay (LOP).',
          'Enterprise Cloud SQL migration with full SOC 2 compliance.',
        ],
        color: 'FBBF24',
      },
    ];

    summaryPoints.forEach((point, idx) => {
      const x = 0.8 + idx * 4.0;
      slide.addShape(pptx.ShapeType.roundRect, {
        x,
        y: 2.2,
        w: 3.7,
        h: 4.6,
        fill: { color: '1E293B' },
        line: { color: '334155', width: 1 },
        rectRadius: 0.1,
      });

      slide.addText(point.title, {
        x: x + 0.3,
        y: 2.5,
        w: 3.1,
        h: 0.4,
        fontSize: 15,
        fontFace: 'Arial',
        bold: true,
        color: point.color,
      });

      const bulletsObj = point.bullets.map((b) => ({
        text: `• ${b}\n\n`,
        options: { color: 'CBD5E1', fontSize: 11, lineSpacingMultiple: 1.15 },
      }));

      slide.addText(bulletsObj, {
        x: x + 0.3,
        y: 3.0,
        w: 3.1,
        h: 3.5,
        fontFace: 'Arial',
      });
    });

    slide.addNotes(
      'Slide 10 Speaker Notes:\nTo conclude, this capstone project demonstrates how modern AI-assisted engineering and domain rigor can transform traditionally complex enterprise workflows like statutory payroll. Thank you to the evaluation committee. I look forward to your questions.'
    );
  }

  // Trigger file download in browser
  const filename = `Capstone_Deck_Indian_Payroll_AI_Tax_${metadata.studentName.replace(/\s+/g, '_')}.pptx`;
  await pptx.writeFile({ fileName: filename });
}
