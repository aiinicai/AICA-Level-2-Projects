import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  getDocs,
  runTransaction,
  serverTimestamp,
  setDoc,
  updateDoc,
  writeBatch,
} from './fsAdapter';
import * as XLSX from 'xlsx';
import {
  BOOTSTRAPPED_ADMIN_EMAIL,
  VALIDATION_LIMITS,
  type Employee,
  type HalfDayOption,
  type Holiday,
  type LeaveBalance,
  type LeaveCategory,
  type LeaveRequest,
  type RosterDiffSummary,
  type RosterSource,
  type RosterSyncConfig,
} from '../types/leave';
import { getCurrentYear, normalizeEmail, roundDays, sanitizeEmailId } from './dateUtils';
import { db, handleFirestoreError, OperationType } from './firebase';

export const DEFAULT_CATEGORIES: Omit<LeaveCategory, 'updatedAt'>[] = [
  {
    id: 'annual',
    name: 'Annual / Earned Leave',
    code: 'EL',
    defaultOpening: 15,
    monthlyAccrual: 1.5,
    allowNegative: false,
    requiresReason: true,
    active: true,
  },
  {
    id: 'sick',
    name: 'Sick Leave',
    code: 'SL',
    defaultOpening: 8,
    monthlyAccrual: 0.5,
    allowNegative: false,
    requiresReason: true,
    active: true,
  },
  {
    id: 'casual',
    name: 'Casual Leave',
    code: 'CL',
    defaultOpening: 6,
    monthlyAccrual: 0.5,
    allowNegative: false,
    requiresReason: true,
    active: true,
  },
  {
    id: 'comp_off',
    name: 'Compensatory Off',
    code: 'CO',
    defaultOpening: 0,
    monthlyAccrual: 0,
    allowNegative: false,
    requiresReason: true,
    active: true,
  },
  {
    id: 'lop',
    name: 'Loss of Pay (Unpaid)',
    code: 'LOP',
    defaultOpening: 0,
    monthlyAccrual: 0,
    allowNegative: true,
    requiresReason: true,
    active: true,
  },
];

export async function seedInitialDataIfNeeded(userEmail: string, displayName: string): Promise<void> {
  const email = normalizeEmail(userEmail);
  if (email !== BOOTSTRAPPED_ADMIN_EMAIL) return;

  try {
    const catSnap = await getDocs(collection(db, 'leaveCategories'));
    if (catSnap.empty) {
      const batch = writeBatch(db);
      for (const cat of DEFAULT_CATEGORIES) {
        const { id, ...rest } = cat;
        batch.set(doc(db, 'leaveCategories', id), {
          ...rest,
          updatedAt: serverTimestamp(),
        });
      }
      await batch.commit();
    }

    const holidaySnap = await getDocs(collection(db, 'holidays'));
    if (holidaySnap.empty) {
      const year = getCurrentYear();
      const batch = writeBatch(db);
      const defaults = [
        { id: `${year}-01-01`, date: `${year}-01-01`, name: "New Year's Day" },
        { id: `${year}-12-25`, date: `${year}-12-25`, name: 'Christmas Day' },
      ];
      for (const h of defaults) {
        batch.set(doc(db, 'holidays', h.id), {
          date: h.date,
          name: h.name,
          updatedAt: serverTimestamp(),
        });
      }
      await batch.commit();
    }

    const empSnap = await getDocs(collection(db, 'employees'));
    if (empSnap.size <= 1) {
      const year = getCurrentYear();
      const latestCatSnap = await getDocs(collection(db, 'leaveCategories'));
      const categories = latestCatSnap.docs.map((d) => ({
        id: d.id,
        ...(d.data() as Omit<LeaveCategory, 'id'>),
      }));

      const initialRoster: Array<Omit<Employee, 'id' | 'updatedAt'>> = [
        {
          employeeCode: '1000',
          name: 'Narendra Arora',
          email: 'narenarora71@gmail.com',
          designation: 'Partner',
          department: '',
          managerEmail: 'narenarora71@gmail.com',
          managerName: 'Narendra Arora',
          isManager: true,
          isAdmin: false,
          status: 'active',
          joiningDate: '',
          source: 'excel',
        },
        {
          employeeCode: '1001',
          name: 'Anup Mundhra',
          email: 'anup.mundhra15@gmail.com',
          designation: 'Manager',
          department: '',
          managerEmail: 'narenarora71@gmail.com',
          managerName: 'Narendra Arora',
          isManager: true,
          isAdmin: true,
          status: 'active',
          joiningDate: '',
          source: 'excel',
        },
        {
          employeeCode: '1002',
          name: 'Ayshalina',
          email: 'ayshalina0001@gmail.com',
          designation: 'Assistant Manager',
          department: '',
          managerEmail: 'anup.mundhra15@gmail.com',
          managerName: 'Anup Mundhra',
          isManager: false,
          isAdmin: false,
          status: 'active',
          joiningDate: '',
          source: 'excel',
        },
        {
          employeeCode: '1003',
          name: 'Anup',
          email: 'anup385.xyz@gmail.com',
          designation: 'Associate',
          department: '',
          managerEmail: 'anup.mundhra15@gmail.com',
          managerName: 'Anup Mundhra',
          isManager: false,
          isAdmin: false,
          status: 'active',
          joiningDate: '',
          source: 'excel',
        },
      ];

      const existingBalSnap = await getDocs(collection(db, 'leaveBalances'));
      const existingBalIds = new Set(existingBalSnap.docs.map((d) => d.id));

      const batch = writeBatch(db);
      for (const emp of initialRoster) {
        const empDocId = sanitizeEmailId(emp.email);
        batch.set(doc(db, 'employees', empDocId), {
          ...emp,
          updatedAt: serverTimestamp(),
        });

        for (const cat of categories) {
          if (!cat.active) continue;
          const balId = `${empDocId}_${year}_${cat.id}`;
          if (!existingBalIds.has(balId)) {
            batch.set(doc(db, 'leaveBalances', balId), {
              employeeId: empDocId,
              employeeEmail: emp.email,
              employeeName: emp.name,
              managerEmail: emp.managerEmail,
              year,
              categoryId: cat.id,
              categoryName: cat.name,
              opening: cat.defaultOpening,
              accrued: 0,
              availed: 0,
              closing: cat.defaultOpening,
              updatedAt: serverTimestamp(),
            });
          }
        }
      }
      await batch.commit();
    }
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, 'seedInitialData');
  }
}

export async function ensureEmployeeBalancesForYear(
  employee: Employee,
  categories: LeaveCategory[],
  existingBalances: LeaveBalance[],
  year: number
): Promise<void> {
  if (employee.status !== 'active' || categories.length === 0) return;

  const existingByCat = new Set(
    existingBalances
      .filter((b) => b.employeeId === employee.id && b.year === year)
      .map((b) => b.categoryId)
  );

  const missingCategories = categories.filter((c) => c.active && !existingByCat.has(c.id));
  if (missingCategories.length === 0) return;

  try {
    const batch = writeBatch(db);
    for (const cat of missingCategories) {
      const balId = `${employee.id}_${year}_${cat.id}`;
      batch.set(doc(db, 'leaveBalances', balId), {
        employeeId: employee.id,
        employeeEmail: employee.email,
        employeeName: employee.name,
        managerEmail: employee.managerEmail || '',
        year,
        categoryId: cat.id,
        categoryName: cat.name,
        opening: cat.defaultOpening,
        accrued: 0,
        availed: 0,
        closing: cat.defaultOpening,
        updatedAt: serverTimestamp(),
      });
    }
    await batch.commit();
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'leaveBalances');
  }
}

export async function commitRosterSync(params: {
  diff: RosterDiffSummary;
  source: RosterSource;
  syncedBy: string;
  categories: LeaveCategory[];
  existingBalances: LeaveBalance[];
  year: number;
  sheetMeta?: { spreadsheetId: string; spreadsheetTitle: string; sheetName: string };
}): Promise<void> {
  const { diff, source, syncedBy, categories, existingBalances, year, sheetMeta } = params;
  const existingBalanceKeys = new Set(existingBalances.map((b) => b.id));
  const balancesByEmpId = new Map<string, LeaveBalance[]>();
  for (const b of existingBalances) {
    const list = balancesByEmpId.get(b.employeeId) || [];
    list.push(b);
    balancesByEmpId.set(b.employeeId, list);
  }

  const operations: Array<{
    type: 'set' | 'update';
    ref: ReturnType<typeof doc>;
    data: Record<string, unknown>;
  }> = [];

  let activeCount = 0;
  let resignedCount = 0;

  for (const record of diff.resolvedRecords) {
    const empId = sanitizeEmailId(record.email);
    if (record.status === 'active') activeCount += 1;
    else resignedCount += 1;

    operations.push({
      type: 'set',
      ref: doc(db, 'employees', empId),
      data: {
        ...record,
        source,
        updatedAt: serverTimestamp(),
      },
    });

    if (record.status === 'active') {
      for (const cat of categories) {
        if (!cat.active) continue;
        const balId = `${empId}_${year}_${cat.id}`;
        if (!existingBalanceKeys.has(balId)) {
          operations.push({
            type: 'set',
            ref: doc(db, 'leaveBalances', balId),
            data: {
              employeeId: empId,
              employeeEmail: record.email,
              employeeName: record.name,
              managerEmail: record.managerEmail || '',
              year,
              categoryId: cat.id,
              categoryName: cat.name,
              opening: cat.defaultOpening,
              accrued: 0,
              availed: 0,
              closing: cat.defaultOpening,
              updatedAt: serverTimestamp(),
            },
          });
        }
      }
    }

    // Sync managerEmail & employeeName changes to existing balance docs so manager visibility stays accurate
    const empBalances = balancesByEmpId.get(empId) || [];
    for (const bal of empBalances) {
      if (bal.managerEmail !== record.managerEmail || bal.employeeName !== record.name) {
        operations.push({
          type: 'update',
          ref: doc(db, 'leaveBalances', bal.id),
          data: {
            managerEmail: record.managerEmail || '',
            employeeName: record.name,
            updatedAt: serverTimestamp(),
          },
        });
      }
    }
  }

  if (sheetMeta) {
    const syncDoc: Omit<RosterSyncConfig, 'updatedAt'> & { updatedAt: ReturnType<typeof serverTimestamp> } = {
      spreadsheetId: sheetMeta.spreadsheetId.slice(0, VALIDATION_LIMITS.maxSpreadsheetIdLength),
      spreadsheetTitle: sheetMeta.spreadsheetTitle.slice(0, VALIDATION_LIMITS.maxSpreadsheetTitleLength),
      sheetName: sheetMeta.sheetName.slice(0, VALIDATION_LIMITS.maxSheetNameLength),
      lastSyncedBy: normalizeEmail(syncedBy).slice(0, VALIDATION_LIMITS.maxEmailLength),
      activeCount,
      resignedCount,
      updatedAt: serverTimestamp(),
    };
    operations.push({
      type: 'set',
      ref: doc(db, 'settings', 'rosterSync'),
      data: syncDoc,
    });
  }

  // Commit in chunks of 400 to respect Firestore 500-write batch limit
  try {
    const CHUNK_SIZE = 400;
    for (let i = 0; i < operations.length; i += CHUNK_SIZE) {
      const chunk = operations.slice(i, i + CHUNK_SIZE);
      const batch = writeBatch(db);
      for (const op of chunk) {
        if (op.type === 'set') {
          batch.set(op.ref, op.data);
        } else {
          batch.update(op.ref, op.data);
        }
      }
      await batch.commit();
    }
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, 'employees/rosterSync');
  }
}

export async function saveSingleEmployee(
  emp: Omit<Employee, 'id' | 'updatedAt'>,
  categories: LeaveCategory[],
  existingBalances: LeaveBalance[],
  year: number
): Promise<void> {
  const empId = sanitizeEmailId(emp.email);
  try {
    await setDoc(doc(db, 'employees', empId), {
      ...emp,
      email: normalizeEmail(emp.email),
      managerEmail: emp.managerEmail ? normalizeEmail(emp.managerEmail) : '',
      updatedAt: serverTimestamp(),
    });
    if (emp.status === 'active') {
      await ensureEmployeeBalancesForYear({ ...emp, id: empId }, categories, existingBalances, year);
    }
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, `employees/${empId}`);
  }
}

export async function submitLeaveRequest(params: {
  employee: Employee;
  category: LeaveCategory;
  startDate: string;
  endDate: string;
  halfDay: HalfDayOption;
  workingDays: number;
  reason: string;
}): Promise<string> {
  const { employee, category, startDate, endDate, halfDay, workingDays, reason } = params;
  const trimmedReason = reason.trim().slice(0, VALIDATION_LIMITS.maxReasonLength);

  if (!employee.managerEmail || !VALIDATION_LIMITS.emailPattern.test(employee.managerEmail)) {
    throw new Error('You do not have a valid Reporting Manager Email assigned in the employee directory.');
  }
  if (employee.status !== 'active') {
    throw new Error('Inactive or resigned employees cannot submit new leave requests.');
  }
  if (workingDays <= 0) {
    throw new Error('Selected date range contains zero working days.');
  }
  if (!trimmedReason) {
    throw new Error('Please enter a brief reason for your leave request.');
  }

  try {
    const docRef = await addDoc(collection(db, 'leaveRequests'), {
      employeeId: employee.id,
      employeeEmail: employee.email,
      employeeName: employee.name,
      employeeDesignation: employee.designation || '',
      managerEmail: employee.managerEmail,
      categoryId: category.id,
      categoryName: category.name,
      startDate,
      endDate,
      halfDay,
      workingDays: roundDays(workingDays),
      reason: trimmedReason,
      status: 'pending',
      managerComment: '',
      reviewedBy: '',
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp(),
    });
    return docRef.id;
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'leaveRequests');
  }
}

export async function reviewLeaveRequest(params: {
  request: LeaveRequest;
  decision: 'approved' | 'rejected';
  comment: string;
  reviewerEmail: string;
  categories: LeaveCategory[];
}): Promise<void> {
  const { request, decision, comment, reviewerEmail, categories } = params;
  const reqRef = doc(db, 'leaveRequests', request.id);
  const year = Number(request.startDate.slice(0, 4)) || getCurrentYear();
  const balId = `${request.employeeId}_${year}_${request.categoryId}`;
  const balRef = doc(db, 'leaveBalances', balId);
  const cleanComment = comment.trim().slice(0, VALIDATION_LIMITS.maxCommentLength);
  const cleanReviewer = normalizeEmail(reviewerEmail);

  try {
    await runTransaction(db, async (tx) => {
      const reqSnap = await tx.get(reqRef);
      if (!reqSnap.exists()) {
        throw new Error('Leave request no longer exists.');
      }
      const reqData = reqSnap.data() as LeaveRequest;
      if (reqData.status !== 'pending') {
        throw new Error(`This request has already been ${reqData.status}.`);
      }

      if (decision === 'approved') {
        const balSnap = await tx.get(balRef);
        if (balSnap.exists()) {
          const bal = balSnap.data() as LeaveBalance;
          const newAvailed = roundDays(bal.availed + reqData.workingDays);
          const newClosing = roundDays(bal.opening + bal.accrued - newAvailed);
          tx.update(balRef, {
            availed: newAvailed,
            closing: newClosing,
            updatedAt: serverTimestamp(),
          });
        } else {
          const cat = categories.find((c) => c.id === reqData.categoryId);
          const defaultOpening = cat?.defaultOpening ?? 0;
          const availed = roundDays(reqData.workingDays);
          tx.set(balRef, {
            employeeId: reqData.employeeId,
            employeeEmail: reqData.employeeEmail,
            employeeName: reqData.employeeName,
            managerEmail: reqData.managerEmail,
            year,
            categoryId: reqData.categoryId,
            categoryName: reqData.categoryName,
            opening: defaultOpening,
            accrued: 0,
            availed,
            closing: roundDays(defaultOpening - availed),
            updatedAt: serverTimestamp(),
          });
        }
      }

      tx.update(reqRef, {
        status: decision,
        managerComment: cleanComment,
        reviewedBy: cleanReviewer,
        reviewedAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      });
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `leaveRequests/${request.id}`);
  }
}

export async function cancelPendingLeaveRequest(requestId: string): Promise<void> {
  try {
    await updateDoc(doc(db, 'leaveRequests', requestId), {
      status: 'cancelled',
      updatedAt: serverTimestamp(),
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `leaveRequests/${requestId}`);
  }
}

export async function adjustEmployeeBalance(params: {
  balance: LeaveBalance;
  opening: number;
  accrued: number;
}): Promise<void> {
  const { balance, opening, accrued } = params;
  const cleanOpening = roundDays(opening);
  const cleanAccrued = roundDays(Math.max(0, accrued));
  const closing = roundDays(cleanOpening + cleanAccrued - balance.availed);

  try {
    await updateDoc(doc(db, 'leaveBalances', balance.id), {
      opening: cleanOpening,
      accrued: cleanAccrued,
      closing,
      updatedAt: serverTimestamp(),
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `leaveBalances/${balance.id}`);
  }
}

export async function runMonthlyAccrualPosting(params: {
  employees: Employee[];
  balances: LeaveBalance[];
  categories: LeaveCategory[];
  year: number;
}): Promise<number> {
  const { employees, balances, categories, year } = params;
  const activeEmpMap = new Map<string, Employee>();
  for (const emp of employees) {
    if (emp.status === 'active') activeEmpMap.set(emp.id, emp);
  }

  const balById = new Map<string, LeaveBalance>();
  for (const b of balances) {
    balById.set(b.id, b);
  }

  const accruingCats = categories.filter((c) => c.active && c.monthlyAccrual > 0);
  const ops: Array<{ type: 'set' | 'update'; ref: ReturnType<typeof doc>; data: Record<string, unknown> }> = [];

  for (const emp of activeEmpMap.values()) {
    for (const cat of accruingCats) {
      const balId = `${emp.id}_${year}_${cat.id}`;
      const existing = balById.get(balId);
      if (existing) {
        const newAccrued = roundDays(existing.accrued + cat.monthlyAccrual);
        const newClosing = roundDays(existing.opening + newAccrued - existing.availed);
        ops.push({
          type: 'update',
          ref: doc(db, 'leaveBalances', balId),
          data: {
            accrued: newAccrued,
            closing: newClosing,
            updatedAt: serverTimestamp(),
          },
        });
      } else {
        const newAccrued = roundDays(cat.monthlyAccrual);
        ops.push({
          type: 'set',
          ref: doc(db, 'leaveBalances', balId),
          data: {
            employeeId: emp.id,
            employeeEmail: emp.email,
            employeeName: emp.name,
            managerEmail: emp.managerEmail || '',
            year,
            categoryId: cat.id,
            categoryName: cat.name,
            opening: cat.defaultOpening,
            accrued: newAccrued,
            availed: 0,
            closing: roundDays(cat.defaultOpening + newAccrued),
            updatedAt: serverTimestamp(),
          },
        });
      }
    }
  }

  try {
    const CHUNK = 400;
    for (let i = 0; i < ops.length; i += CHUNK) {
      const batch = writeBatch(db);
      for (const op of ops.slice(i, i + CHUNK)) {
        if (op.type === 'set') batch.set(op.ref, op.data);
        else batch.update(op.ref, op.data);
      }
      await batch.commit();
    }
    return ops.length;
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, 'leaveBalances/accrual');
  }
}

export async function saveLeaveCategory(category: Omit<LeaveCategory, 'updatedAt'>): Promise<void> {
  const cleanId = category.id.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_').slice(0, 64);
  const cleanCode = category.code.trim().toUpperCase().replace(/[^A-Z0-9_-]/g, '_').slice(0, 16);
  try {
    await setDoc(doc(db, 'leaveCategories', cleanId), {
      name: category.name.trim().slice(0, VALIDATION_LIMITS.maxCategoryNameLength),
      code: cleanCode || 'LV',
      defaultOpening: roundDays(Math.max(0, category.defaultOpening)),
      monthlyAccrual: roundDays(Math.max(0, category.monthlyAccrual)),
      allowNegative: category.allowNegative,
      requiresReason: category.requiresReason,
      active: category.active,
      updatedAt: serverTimestamp(),
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, `leaveCategories/${cleanId}`);
  }
}

export async function saveHoliday(date: string, name: string): Promise<void> {
  const id = date.trim();
  try {
    await setDoc(doc(db, 'holidays', id), {
      date: id,
      name: name.trim().slice(0, VALIDATION_LIMITS.maxHolidayNameLength),
      updatedAt: serverTimestamp(),
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, `holidays/${id}`);
  }
}

export async function removeHoliday(holidayId: string): Promise<void> {
  try {
    await deleteDoc(doc(db, 'holidays', holidayId));
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `holidays/${holidayId}`);
  }
}

export function exportBalancesToExcel(
  balances: LeaveBalance[],
  employees: Employee[],
  year: number
): void {
  const empById = new Map<string, Employee>();
  for (const e of employees) empById.set(e.id, e);

  const rows = balances
    .filter((b) => b.year === year)
    .sort((a, b) => a.employeeName.localeCompare(b.employeeName) || a.categoryName.localeCompare(b.categoryName))
    .map((b) => {
      const emp = empById.get(b.employeeId);
      return {
        'Employee Code': emp?.employeeCode || '',
        Employee: b.employeeName,
        Email: b.employeeEmail,
        Designation: emp?.designation || '',
        Department: emp?.department || '',
        'Reporting Manager': b.managerEmail || '',
        Status: emp?.status || 'active',
        Year: b.year,
        'Leave Category': b.categoryName,
        Opening: b.opening,
        Accrued: b.accrued,
        Availed: b.availed,
        Closing: b.closing,
      };
    });

  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, `Leave_Balances_${year}`);
  XLSX.writeFile(wb, `LeaveLedger_Balances_${year}.xlsx`);
}
