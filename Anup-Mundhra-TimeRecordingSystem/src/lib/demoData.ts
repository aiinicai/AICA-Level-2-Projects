/**
 * Sample organisation used by "Try Demo" mode. Every name, email, client and
 * project below is fictional (example.com addresses). Dates are generated
 * relative to today so the demo always looks current.
 */
import { ensureSeeded, serverTimestamp, type DemoRole } from './demoStore';

export const DEMO_ADMIN_EMAIL = 'demo.admin@example.com';
const PARTNER = 'demo.partner@example.com';
const MANAGER = 'demo.manager@example.com';
const EMPLOYEE = 'demo.employee@example.com';
const INTERN = 'demo.intern@example.com';

export const DEMO_USERS: Record<DemoRole, { email: string; name: string; label: string }> = {
  admin: { email: DEMO_ADMIN_EMAIL, name: 'Priya Sharma', label: 'HR Admin' },
  manager: { email: MANAGER, name: 'Arjun Nair', label: 'Manager' },
  employee: { email: EMPLOYEE, name: 'Kavya Iyer', label: 'Employee' },
};

const idOf = (email: string) => email.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');

const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const isWeekend = (d: Date) => d.getDay() === 0 || d.getDay() === 6;

interface Person {
  code: string;
  name: string;
  email: string;
  designation: string;
  department: string;
  managerEmail: string;
  managerName: string;
  isManager: boolean;
  isAdmin: boolean;
  joiningDate: string;
}

const PEOPLE: Person[] = [
  {
    code: '2000', name: 'Rohan Mehta', email: PARTNER, designation: 'Partner', department: 'Audit & Advisory',
    managerEmail: PARTNER, managerName: 'Rohan Mehta', isManager: true, isAdmin: false, joiningDate: '2015-04-01',
  },
  {
    code: '2001', name: 'Priya Sharma', email: DEMO_ADMIN_EMAIL, designation: 'HR & Finance Manager', department: 'Operations',
    managerEmail: PARTNER, managerName: 'Rohan Mehta', isManager: true, isAdmin: true, joiningDate: '2018-07-16',
  },
  {
    code: '2002', name: 'Arjun Nair', email: MANAGER, designation: 'Manager', department: 'Audit & Advisory',
    managerEmail: PARTNER, managerName: 'Rohan Mehta', isManager: true, isAdmin: false, joiningDate: '2019-02-04',
  },
  {
    code: '2003', name: 'Kavya Iyer', email: EMPLOYEE, designation: 'Associate', department: 'Audit & Advisory',
    managerEmail: MANAGER, managerName: 'Arjun Nair', isManager: false, isAdmin: false, joiningDate: '2022-06-01',
  },
  {
    code: '2004', name: 'Rahul Verma', email: INTERN, designation: 'Intern', department: 'Audit & Advisory',
    managerEmail: MANAGER, managerName: 'Arjun Nair', isManager: false, isAdmin: false, joiningDate: '2026-01-12',
  },
];

const CATEGORIES = [
  { id: 'annual', name: 'Annual / Earned Leave', code: 'EL', defaultOpening: 15, monthlyAccrual: 1.5, allowNegative: false, requiresReason: true, active: true },
  { id: 'sick', name: 'Sick Leave', code: 'SL', defaultOpening: 8, monthlyAccrual: 0.5, allowNegative: false, requiresReason: true, active: true },
  { id: 'casual', name: 'Casual Leave', code: 'CL', defaultOpening: 6, monthlyAccrual: 0.5, allowNegative: false, requiresReason: true, active: true },
  { id: 'comp_off', name: 'Compensatory Off', code: 'CO', defaultOpening: 0, monthlyAccrual: 0, allowNegative: false, requiresReason: true, active: true },
  { id: 'lop', name: 'Loss of Pay (Unpaid)', code: 'LOP', defaultOpening: 0, monthlyAccrual: 0, allowNegative: true, requiresReason: true, active: true },
];

const PROJECTS = [
  { code: 'PRJ-101', name: 'Statutory Audit FY26', client: 'Acme Textiles Ltd', type: 'chargeable' },
  { code: 'PRJ-102', name: 'Internal Controls Review', client: 'Bluewave Foods', type: 'chargeable' },
  { code: 'PRJ-103', name: 'Tax Advisory Retainer', client: 'Orion Motors', type: 'chargeable' },
  { code: 'PRJ-104', name: 'IFRS Conversion Support', client: 'Zenith Tech', type: 'chargeable' },
  { code: 'NC-001', name: 'Training & Learning', client: 'Internal', type: 'non_chargeable' },
  { code: 'NC-002', name: 'Business Development', client: 'Internal', type: 'non_chargeable' },
  { code: 'NC-003', name: 'Admin & Internal Work', client: 'Internal', type: 'non_chargeable' },
] as const;

type Pattern = Array<[string, number]>;
const PATTERNS: Pattern[] = [
  [['PRJ-101', 8]],
  [['PRJ-101', 5], ['NC-001', 3]],
  [['PRJ-102', 6], ['PRJ-101', 2]],
  [['PRJ-103', 4.5], ['PRJ-101', 3.5]],
  [['PRJ-104', 8]],
  [['PRJ-102', 4], ['NC-002', 2], ['NC-003', 2]],
];

export function seedDemoData(): void {
  ensureSeeded((set) => {
    const now = new Date();
    const year = now.getFullYear();
    const today = iso(now);

    for (const c of CATEGORIES) {
      const { id, ...rest } = c;
      set('leaveCategories', id, { ...rest, updatedAt: serverTimestamp() });
    }

    const holidays = [
      [`${year}-01-01`, "New Year's Day"],
      [`${year}-01-26`, 'Republic Day'],
      [`${year}-08-15`, 'Independence Day'],
      [`${year}-10-02`, 'Gandhi Jayanti'],
      [`${year}-12-25`, 'Christmas Day'],
    ];
    for (const [date, name] of holidays) {
      set('holidays', date, { date, name, updatedAt: serverTimestamp() });
    }
    const holidayDates = new Set(holidays.map((h) => h[0]));

    for (const p of PROJECTS) {
      set('projects', p.code, {
        code: p.code,
        name: p.name,
        client: p.client,
        type: p.type,
        active: true,
        partnerName: 'Rohan Mehta',
        partnerEmail: PARTNER,
        managerName: 'Arjun Nair',
        managerEmail: MANAGER,
        updatedAt: serverTimestamp(),
      });
    }

    for (const p of PEOPLE) {
      const id = idOf(p.email);
      set('employees', id, {
        employeeCode: p.code,
        name: p.name,
        email: p.email,
        designation: p.designation,
        department: p.department,
        managerEmail: p.managerEmail,
        managerName: p.managerName,
        isManager: p.isManager,
        isAdmin: p.isAdmin,
        status: 'active',
        joiningDate: p.joiningDate,
        source: 'manual',
        updatedAt: serverTimestamp(),
      });
    }

    // Leave: one approved (past) for Kavya, one pending for Rahul, one rejected for Arjun's team lead view
    const weekdaysBack: string[] = [];
    for (let i = 1; weekdaysBack.length < 14; i++) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      if (!isWeekend(d) && !holidayDates.has(iso(d))) weekdaysBack.push(iso(d));
    }
    // weekdaysBack[0] is the most recent working day
    const kavyaLeave = [weekdaysBack[9], weekdaysBack[8]]; // two older consecutive working days
    const nextMon = new Date(now);
    nextMon.setDate(now.getDate() + ((8 - now.getDay()) % 7 || 7));
    const nextTue = new Date(nextMon);
    nextTue.setDate(nextMon.getDate() + 1);

    const leaveRows = [
      {
        id: 'demo_leave_1', email: EMPLOYEE, cat: ['annual', 'Annual / Earned Leave'], start: kavyaLeave[0], end: kavyaLeave[1],
        days: 2, reason: 'Family function', status: 'approved', comment: 'Approved. Enjoy!', reviewer: MANAGER,
      },
      {
        id: 'demo_leave_2', email: INTERN, cat: ['casual', 'Casual Leave'], start: iso(nextMon), end: iso(nextTue),
        days: 2, reason: 'University exam', status: 'pending', comment: '', reviewer: '',
      },
      {
        id: 'demo_leave_3', email: EMPLOYEE, cat: ['sick', 'Sick Leave'], start: iso(nextMon), end: iso(nextMon),
        days: 1, reason: 'Medical check-up', status: 'pending', comment: '', reviewer: '',
      },
    ];
    for (const l of leaveRows) {
      const p = PEOPLE.find((x) => x.email === l.email)!;
      const { id, ...rest } = {
        id: l.id,
        employeeId: idOf(p.email),
        employeeEmail: p.email,
        employeeName: p.name,
        employeeDesignation: p.designation,
        managerEmail: p.managerEmail,
        categoryId: l.cat[0],
        categoryName: l.cat[1],
        startDate: l.start,
        endDate: l.end,
        halfDay: 'none',
        workingDays: l.days,
        reason: l.reason,
        status: l.status,
        managerComment: l.comment,
        reviewedBy: l.reviewer,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      };
      set('leaveRequests', id, rest);
    }

    // Balances
    const month = now.getMonth() + 1;
    for (const p of PEOPLE) {
      for (const c of CATEGORIES) {
        const approved = leaveRows
          .filter((l) => l.email === p.email && l.status === 'approved' && l.cat[0] === c.id)
          .reduce((s, l) => s + l.days, 0);
        const accrued = Math.round(c.monthlyAccrual * month * 10) / 10;
        const balId = `${idOf(p.email)}_${year}_${c.id}`;
        set('leaveBalances', balId, {
          employeeId: idOf(p.email),
          employeeEmail: p.email,
          employeeName: p.name,
          managerEmail: p.managerEmail,
          year,
          categoryId: c.id,
          categoryName: c.name,
          opening: c.defaultOpening,
          accrued,
          availed: approved,
          closing: Math.round((c.defaultOpening + accrued - approved) * 10) / 10,
          updatedAt: serverTimestamp(),
        });
      }
    }

    // Timesheets for the last working days: oldest approved, middle submitted, newest draft
    const leaveSet = new Set(kavyaLeave);
    const timesheetPeople = [PEOPLE[3], PEOPLE[4], PEOPLE[2], PEOPLE[1]]; // Kavya, Rahul, Arjun, Priya
    timesheetPeople.forEach((p, pi) => {
      weekdaysBack.slice(0, 12).forEach((date, di) => {
        if (p.email === EMPLOYEE && leaveSet.has(date)) return; // approved leave day: no timesheet
        const pattern = PATTERNS[(di + pi) % PATTERNS.length];
        const lines = pattern.map(([code, hours]) => {
          const proj = PROJECTS.find((x) => x.code === code)!;
          return { projectCode: proj.code, projectName: proj.name, clientName: proj.client, type: proj.type, hours };
        });
        // di: 0 = most recent day. Newest 2 = draft, next 3 = submitted, rest approved.
        const status = di < 2 ? 'draft' : di < 5 ? 'submitted' : 'approved';
        const mgr = p.managerEmail;
        const mgrName = p.managerName;
        set('timesheetEntries', `${idOf(p.email)}_${date}`, {
          employeeId: idOf(p.email),
          employeeEmail: p.email,
          employeeName: p.name,
          managerEmail: mgr,
          date,
          lines,
          totalHours: 8,
          status,
          managerComment: '',
          reviewedBy: status === 'approved' ? mgr : '',
          reopenedBy: '',
          reopenReason: '',
          ...(status !== 'draft' ? { submittedAt: serverTimestamp() } : {}),
          ...(status === 'approved' ? { reviewedAt: serverTimestamp() } : {}),
          updatedAt: serverTimestamp(),
        });
        void mgrName;
      });
    });

    // Partner (self-managed): one submitted day so the HR admin sees an approval item
    const pDate = weekdaysBack[2];
    set('timesheetEntries', `${idOf(PARTNER)}_${pDate}`, {
      employeeId: idOf(PARTNER),
      employeeEmail: PARTNER,
      employeeName: 'Rohan Mehta',
      managerEmail: PARTNER,
      date: pDate,
      lines: [
        { projectCode: 'PRJ-101', projectName: 'Statutory Audit FY26', clientName: 'Acme Textiles Ltd', type: 'chargeable', hours: 5 },
        { projectCode: 'NC-002', projectName: 'Business Development', clientName: 'Internal', type: 'non_chargeable', hours: 3 },
      ],
      totalHours: 8,
      status: 'submitted',
      managerComment: '',
      reviewedBy: '',
      reopenedBy: '',
      reopenReason: '',
      submittedAt: serverTimestamp(),
      updatedAt: serverTimestamp(),
    });
    void today;
  });
}
