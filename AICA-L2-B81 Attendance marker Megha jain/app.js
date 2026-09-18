/**
 * Attendance & Salary Calculator Logic
 * Based on CA Firm Employment Offer Letter Rules
 * Multi-Employee Management Engine
 */

// Default Initial Employees (Generic - no hardcoded personal names from file)
const DEFAULT_EMPLOYEES = {
    "emp_1": {
        id: "emp_1",
        name: "Accounts Executive - 1",
        designation: "Accounts Executive",
        joiningDate: "2026-04-13",
        basicSalary: 20000,
        retainershipBonusAmount: 60000,
        retainershipBonusTargetDate: "2027-12-31",
        bankName: "Bank of Baroda",
        bankAccount: "75580100016748",
        ifsc: "BARB0VJNDYL",
        pan: "ABCDE1234F",
        aadhar: "4345 5293 4097",
        status: "Active"
    },
    "emp_2": {
        id: "emp_2",
        name: "Article Assistant - 1",
        designation: "Article Assistant",
        joiningDate: "2026-05-01",
        basicSalary: 15000,
        retainershipBonusAmount: 40000,
        retainershipBonusTargetDate: "2027-12-31",
        bankName: "State Bank of India",
        bankAccount: "30291823901",
        ifsc: "SBIN0001234",
        pan: "XYZPA9876Q",
        aadhar: "9876 5432 1098",
        status: "Active"
    }
};

// Application State
let employees = {};
let currentEmployeeId = "emp_1";
let currentYear = 2026;
let currentMonth = 3; // April (0-indexed: 3 = April)
let attendanceData = {}; // Key format: [empId][monthKey] -> array of day records
let monthParams = {}; // Key format: [empId][monthKey] -> { basicSalary, calcBasis, openingLeaves, reimbursements, tds, otherDed }

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    loadFromLocalStorage();

    if (Object.keys(employees).length === 0) {
        employees = JSON.parse(JSON.stringify(DEFAULT_EMPLOYEES));
        saveToLocalStorage();
    }

    if (!employees[currentEmployeeId]) {
        currentEmployeeId = Object.keys(employees)[0] || "emp_1";
    }

    populateEmployeeDropdown();

    const selectMonth = document.getElementById("selectMonth");
    const selectYear = document.getElementById("selectYear");

    selectMonth.value = currentMonth;
    selectYear.value = currentYear;

    selectMonth.addEventListener("change", (e) => {
        currentMonth = parseInt(e.target.value);
        renderMonthView();
    });

    selectYear.addEventListener("change", (e) => {
        currentYear = parseInt(e.target.value);
        renderMonthView();
    });

    renderEmployeeBanner();
    renderMonthView();
});

// Storage Functions
function saveToLocalStorage() {
    try {
        localStorage.setItem("ca_employees", JSON.stringify(employees));
        localStorage.setItem("ca_current_employee_id", currentEmployeeId);
        localStorage.setItem("ca_attendance_data", JSON.stringify(attendanceData));
        localStorage.setItem("ca_month_params", JSON.stringify(monthParams));
    } catch (e) {
        console.error("Storage save failed:", e);
    }
}

function loadFromLocalStorage() {
    try {
        const savedEmps = localStorage.getItem("ca_employees");
        const savedCurrEmp = localStorage.getItem("ca_current_employee_id");
        const savedData = localStorage.getItem("ca_attendance_data");
        const savedParams = localStorage.getItem("ca_month_params");

        if (savedEmps) employees = JSON.parse(savedEmps);
        if (savedCurrEmp && employees[savedCurrEmp]) currentEmployeeId = savedCurrEmp;
        if (savedData) attendanceData = JSON.parse(savedData);
        if (savedParams) monthParams = JSON.parse(savedParams);
    } catch (e) {
        console.error("Storage load failed:", e);
    }
}

// Populate Employee Selector
function populateEmployeeDropdown() {
    const select = document.getElementById("selectEmployee");
    select.innerHTML = "";
    Object.values(employees).forEach(emp => {
        const opt = document.createElement("option");
        opt.value = emp.id;
        opt.textContent = `${emp.name} (${emp.designation})`;
        if (emp.id === currentEmployeeId) opt.selected = true;
        select.appendChild(opt);
    });
}

// Switch Active Employee
function switchEmployee(empId) {
    if (employees[empId]) {
        currentEmployeeId = empId;
        saveToLocalStorage();
        renderEmployeeBanner();
        renderMonthView();
    }
}

// Render Employee Banner Details
function renderEmployeeBanner() {
    const emp = employees[currentEmployeeId];
    if (!emp) return;

    document.getElementById("empName").textContent = emp.name;
    document.getElementById("empDesignation").textContent = emp.designation;
    document.getElementById("empStatus").textContent = emp.status || "Active";
    
    // Avatar initials
    const initials = emp.name.split(" ").filter(Boolean).map(n => n[0]).slice(0, 2).join("").toUpperCase() || "EE";
    document.getElementById("empAvatar").textContent = initials;

    // Dates & Info
    const joinDateObj = new Date(emp.joiningDate);
    const joinFormatted = isNaN(joinDateObj) ? emp.joiningDate : joinDateObj.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
    document.getElementById("empJoiningDateText").textContent = joinFormatted;
    document.getElementById("empPanText").textContent = emp.pan || "—";
    document.getElementById("empBankText").textContent = emp.bankName ? `${emp.bankName} (${emp.ifsc || ''})` : "—";

    // Bonus Target
    document.getElementById("empBonusAmountText").textContent = `₹${formatINR(emp.retainershipBonusAmount || 60000)}`;
    const bonusTargetObj = new Date(emp.retainershipBonusTargetDate || "2027-12-31");
    const bonusTargetFormatted = isNaN(bonusTargetObj) ? "31st Dec 2027" : bonusTargetObj.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
    document.getElementById("empBonusTargetText").textContent = `Target: ${bonusTargetFormatted}`;
}

// Employee Modal (Add / Edit)
function openEmployeeModal(isNew = false) {
    const modal = document.getElementById("employeeModal");
    const title = document.getElementById("employeeModalTitle");

    if (isNew) {
        title.textContent = "Add New Employee";
        document.getElementById("modalEmpId").value = "";
        document.getElementById("modalEmpName").value = "";
        document.getElementById("modalEmpDesignation").value = "Accounts Executive";
        document.getElementById("modalEmpJoiningDate").value = "2026-04-13";
        document.getElementById("modalEmpBasicSalary").value = "20000";
        document.getElementById("modalEmpBonusAmount").value = "60000";
        document.getElementById("modalEmpBonusTargetDate").value = "2027-12-31";
        document.getElementById("modalEmpBankName").value = "";
        document.getElementById("modalEmpBankAccount").value = "";
        document.getElementById("modalEmpIfsc").value = "";
        document.getElementById("modalEmpPan").value = "";
        document.getElementById("modalEmpAadhar").value = "";
    } else {
        const emp = employees[currentEmployeeId];
        title.textContent = `Edit Profile: ${emp.name}`;
        document.getElementById("modalEmpId").value = emp.id;
        document.getElementById("modalEmpName").value = emp.name;
        document.getElementById("modalEmpDesignation").value = emp.designation;
        document.getElementById("modalEmpJoiningDate").value = emp.joiningDate;
        document.getElementById("modalEmpBasicSalary").value = emp.basicSalary;
        document.getElementById("modalEmpBonusAmount").value = emp.retainershipBonusAmount || 60000;
        document.getElementById("modalEmpBonusTargetDate").value = emp.retainershipBonusTargetDate || "2027-12-31";
        document.getElementById("modalEmpBankName").value = emp.bankName || "";
        document.getElementById("modalEmpBankAccount").value = emp.bankAccount || "";
        document.getElementById("modalEmpIfsc").value = emp.ifsc || "";
        document.getElementById("modalEmpPan").value = emp.pan || "";
        document.getElementById("modalEmpAadhar").value = emp.aadhar || "";
    }

    modal.classList.remove("hidden");
}

function closeEmployeeModal() {
    document.getElementById("employeeModal").classList.add("hidden");
}

function saveEmployeeProfile(e) {
    e.preventDefault();
    const idInput = document.getElementById("modalEmpId").value;
    const isNew = !idInput;
    const empId = isNew ? `emp_${Date.now()}` : idInput;

    employees[empId] = {
        id: empId,
        name: document.getElementById("modalEmpName").value.trim(),
        designation: document.getElementById("modalEmpDesignation").value.trim(),
        joiningDate: document.getElementById("modalEmpJoiningDate").value,
        basicSalary: parseFloat(document.getElementById("modalEmpBasicSalary").value) || 20000,
        retainershipBonusAmount: parseFloat(document.getElementById("modalEmpBonusAmount").value) || 60000,
        retainershipBonusTargetDate: document.getElementById("modalEmpBonusTargetDate").value || "2027-12-31",
        bankName: document.getElementById("modalEmpBankName").value.trim(),
        bankAccount: document.getElementById("modalEmpBankAccount").value.trim(),
        ifsc: document.getElementById("modalEmpIfsc").value.trim().toUpperCase(),
        pan: document.getElementById("modalEmpPan").value.trim().toUpperCase(),
        aadhar: document.getElementById("modalEmpAadhar").value.trim(),
        status: "Active"
    };

    currentEmployeeId = empId;
    saveToLocalStorage();
    populateEmployeeDropdown();
    renderEmployeeBanner();
    closeEmployeeModal();
    renderMonthView();
}

function deleteCurrentEmployee() {
    const keys = Object.keys(employees);
    if (keys.length <= 1) {
        alert("Cannot delete the only remaining employee. Add another employee first.");
        return;
    }
    const emp = employees[currentEmployeeId];
    if (confirm(`Are you sure you want to delete ${emp.name}? All recorded attendance will be removed.`)) {
        delete employees[currentEmployeeId];
        delete attendanceData[currentEmployeeId];
        delete monthParams[currentEmployeeId];
        currentEmployeeId = Object.keys(employees)[0];
        saveToLocalStorage();
        populateEmployeeDropdown();
        renderEmployeeBanner();
        renderMonthView();
    }
}

// Generate Month Key
function getMonthKey(year, month) {
    return `${year}-${String(month + 1).padStart(2, "0")}`;
}

// Get Days in Month
function getDaysInMonth(year, month) {
    return new Date(year, month + 1, 0).getDate();
}

// Day name helper
function getDayName(year, month, day) {
    const d = new Date(year, month, day);
    return d.toLocaleDateString("en-US", { weekday: "short" });
}

// Render Month View
function renderMonthView() {
    const emp = employees[currentEmployeeId];
    if (!emp) return;

    const key = getMonthKey(currentYear, currentMonth);
    const totalDays = getDaysInMonth(currentYear, currentMonth);

    if (!monthParams[currentEmployeeId]) monthParams[currentEmployeeId] = {};
    if (!attendanceData[currentEmployeeId]) attendanceData[currentEmployeeId] = {};

    // Initialize month parameters if not exists
    if (!monthParams[currentEmployeeId][key]) {
        let prevOpening = 0.0;
        const prevDate = new Date(currentYear, currentMonth - 1, 1);
        const prevKey = getMonthKey(prevDate.getFullYear(), prevDate.getMonth());
        if (monthParams[currentEmployeeId][prevKey] && monthParams[currentEmployeeId][prevKey].closingLeaves !== undefined) {
            prevOpening = monthParams[currentEmployeeId][prevKey].closingLeaves;
        }

        monthParams[currentEmployeeId][key] = {
            basicSalary: emp.basicSalary || 20000,
            calcBasis: "calendar_days",
            openingLeaves: prevOpening,
            reimbursements: 0,
            tds: 0,
            otherDed: 0
        };
    }

    const params = monthParams[currentEmployeeId][key];
    document.getElementById("inputBasicSalary").value = params.basicSalary;
    document.getElementById("selectCalcBasis").value = params.calcBasis;
    document.getElementById("inputOpeningLeaves").value = params.openingLeaves;
    document.getElementById("inputReimbursements").value = params.reimbursements;
    document.getElementById("inputTDS").value = params.tds;
    document.getElementById("inputOtherDeductions").value = params.otherDed;

    // Check pro-rata condition based on employee's joining date
    const joinDateObj = new Date(emp.joiningDate);
    const monthStartDate = new Date(currentYear, currentMonth, 1);
    const monthEndDate = new Date(currentYear, currentMonth, totalDays);
    const isMidMonthJoining = joinDateObj >= monthStartDate && joinDateObj <= monthEndDate && joinDateObj.getDate() > 1;

    const proRataBadge = document.getElementById("proRataBadge");
    if (isMidMonthJoining) {
        proRataBadge.textContent = `Joining Pro-Rata Active (${joinDateObj.getDate()} to ${totalDays} ${monthStartDate.toLocaleString('default', { month: 'short' })})`;
        proRataBadge.classList.remove("hidden");
    } else {
        proRataBadge.classList.add("hidden");
    }

    // Initialize daily records if empty
    if (!attendanceData[currentEmployeeId][key] || attendanceData[currentEmployeeId][key].length !== totalDays) {
        initDefaultMonthRecords(key, totalDays, joinDateObj);
    }

    renderTableRows();
    recalculatePayroll();
}

// Initialize default month records based on 5.5 day week & employee joining date
function initDefaultMonthRecords(key, totalDays, joinDateObj) {
    const records = [];
    for (let d = 1; d <= totalDays; d++) {
        const dayDate = new Date(currentYear, currentMonth, d);
        const dayOfWeek = dayDate.getDay(); // 0 = Sun, 6 = Sat
        const isBeforeJoining = dayDate < joinDateObj;

        let status = "P";
        let inTime = "09:30";
        let outTime = "19:00";

        if (isBeforeJoining) {
            status = "NOT_JOINED";
            inTime = "";
            outTime = "";
        } else if (dayOfWeek === 0) { // Sunday Off
            status = "OFF";
            inTime = "";
            outTime = "";
        } else if (dayOfWeek === 6) { // Saturday Half Day (5h)
            status = "HD";
            inTime = "09:30";
            outTime = "14:30";
        }

        records.push({
            day: d,
            status: status,
            in_time: inTime,
            out_time: outTime,
            wfh_productive: true,
            medical_cert_provided: false,
            note: ""
        });
    }
    attendanceData[currentEmployeeId][key] = records;
    saveToLocalStorage();
}

// Preset application
function applyPresetSchedule(presetType) {
    const emp = employees[currentEmployeeId];
    if (!emp) return;
    const key = getMonthKey(currentYear, currentMonth);
    const totalDays = getDaysInMonth(currentYear, currentMonth);
    const joinDateObj = new Date(emp.joiningDate);

    const records = [];
    for (let d = 1; d <= totalDays; d++) {
        const dayDate = new Date(currentYear, currentMonth, d);
        const dayOfWeek = dayDate.getDay();
        const isBeforeJoining = dayDate < joinDateObj;

        if (isBeforeJoining) {
            records.push({
                day: d,
                status: "NOT_JOINED",
                in_time: "",
                out_time: "",
                wfh_productive: true,
                medical_cert_provided: false,
                note: ""
            });
            continue;
        }

        if (presetType === "standard_5_5") {
            if (dayOfWeek === 0) {
                records.push({
                    day: d,
                    status: "OFF",
                    in_time: "",
                    out_time: "",
                    wfh_productive: true,
                    medical_cert_provided: false,
                    note: "Weekly Off"
                });
            } else if (dayOfWeek === 6) {
                records.push({
                    day: d,
                    status: "HD",
                    in_time: "09:30",
                    out_time: "14:30",
                    wfh_productive: true,
                    medical_cert_provided: false,
                    note: "Saturday Half-Day (5 hrs)"
                });
            } else {
                records.push({
                    day: d,
                    status: "P",
                    in_time: "09:30",
                    out_time: "19:00",
                    wfh_productive: true,
                    medical_cert_provided: false,
                    note: ""
                });
            }
        } else if (presetType === "all_present") {
            records.push({
                day: d,
                status: "P",
                in_time: "09:30",
                out_time: "19:00",
                wfh_productive: true,
                medical_cert_provided: false,
                note: ""
            });
        }
    }

    attendanceData[currentEmployeeId][key] = records;
    saveToLocalStorage();
    renderTableRows();
    recalculatePayroll();
}

function resetMonthAttendance() {
    const emp = employees[currentEmployeeId];
    if (!emp) return;
    if (confirm(`Reset attendance for ${emp.name} for this month to default?`)) {
        const key = getMonthKey(currentYear, currentMonth);
        const totalDays = getDaysInMonth(currentYear, currentMonth);
        initDefaultMonthRecords(key, totalDays, new Date(emp.joiningDate));
        renderTableRows();
        recalculatePayroll();
    }
}

// Calculate Net Working Hours (30 mins lunch break deduction)
function calculateNetHours(inTime, outTime) {
    if (!inTime || !outTime) return 0.0;
    try {
        const [h1, m1] = inTime.split(":").map(Number);
        const [h2, m2] = outTime.split(":").map(Number);
        const mins1 = h1 * 60 + m1;
        const mins2 = h2 * 60 + m2;
        if (mins2 <= mins1) return 0.0;
        const totalMins = mins2 - mins1;
        const breakMins = totalMins >= 240 ? 30 : 0;
        const netMins = Math.max(0, totalMins - breakMins);
        return Math.round((netMins / 60) * 10) / 10;
    } catch (e) {
        return 0.0;
    }
}

// Evaluate Late Status
function getLateEvaluation(inTime) {
    if (!inTime) return { isLate: false, isSevereLate: false, label: "N/A", color: "text-slate-400" };
    try {
        const [h, m] = inTime.split(":").map(Number);
        const mins = h * 60 + m;
        const cutoffStart = 9 * 60 + 30; // 09:30 AM
        const cutoff10am = 10 * 60; // 10:00 AM

        if (mins <= cutoffStart) {
            return { isLate: false, isSevereLate: false, label: "On Time", color: "bg-emerald-50 text-emerald-700 border-emerald-200" };
        } else if (mins > cutoffStart && mins <= cutoff10am) {
            return { isLate: true, isSevereLate: false, label: "Late In (>9:30)", color: "bg-amber-50 text-amber-700 border-amber-200" };
        } else {
            return { isLate: true, isSevereLate: true, label: "Severe Late (>10:00 AM)", color: "bg-rose-50 text-rose-700 border-rose-300 font-bold" };
        }
    } catch (e) {
        return { isLate: false, isSevereLate: false, label: "N/A", color: "text-slate-400" };
    }
}

// Render Daily Table Rows
function renderTableRows() {
    const emp = employees[currentEmployeeId];
    if (!emp) return;

    const key = getMonthKey(currentYear, currentMonth);
    const records = (attendanceData[currentEmployeeId] && attendanceData[currentEmployeeId][key]) || [];
    const tbody = document.getElementById("attendanceTableBody");
    tbody.innerHTML = "";
    const joinDateObj = new Date(emp.joiningDate);

    records.forEach((rec) => {
        const dayDate = new Date(currentYear, currentMonth, rec.day);
        const dayOfWeek = getDayName(currentYear, currentMonth, rec.day);
        const isSun = dayDate.getDay() === 0;
        const isSat = dayDate.getDay() === 6;
        const isBeforeJoining = dayDate < joinDateObj;

        const tr = document.createElement("tr");
        tr.className = `hover:bg-slate-50/80 transition ${isSun ? "bg-slate-50/50" : ""} ${isBeforeJoining ? "opacity-60 bg-slate-100/40" : ""}`;

        const netHrs = calculateNetHours(rec.in_time, rec.out_time);
        const lateEval = (rec.status === "P" || rec.status === "HD" || rec.status === "WFH") && rec.in_time ? getLateEvaluation(rec.in_time) : { label: "—", color: "text-slate-400" };

        tr.innerHTML = `
            <td class="py-2.5 px-3 text-center font-bold text-slate-700">${rec.day}</td>
            <td class="py-2.5 px-3">
                <div class="font-semibold text-slate-800">${rec.day} ${new Date(currentYear, currentMonth, rec.day).toLocaleString('default', { month: 'short' })}</div>
                <div class="text-[10px] ${isSun ? 'text-rose-500 font-bold' : isSat ? 'text-amber-600 font-semibold' : 'text-slate-400'}">${dayOfWeek} ${isSun ? '(Weekly Off)' : isSat ? '(Half Day 5h)' : ''}</div>
            </td>
            <td class="py-2.5 px-3">
                <select class="status-select w-full bg-white border border-slate-300 rounded-lg px-2 py-1 text-xs font-semibold text-slate-800 focus:ring-1 focus:ring-ca-600" data-day="${rec.day}" onchange="updateRecordStatus(${rec.day}, this.value)" ${isBeforeJoining ? "disabled" : ""}>
                    ${isBeforeJoining ? '<option value="NOT_JOINED" selected>Not Joined Yet</option>' : ''}
                    <option value="P" ${rec.status === 'P' ? 'selected' : ''}>🟢 Present (Full Day)</option>
                    <option value="HD" ${rec.status === 'HD' ? 'selected' : ''}>🟡 Half Day (HD)</option>
                    <option value="WFH" ${rec.status === 'WFH' ? 'selected' : ''}>🔵 Work From Home (WFH)</option>
                    <option value="PL" ${rec.status === 'PL' ? 'selected' : ''}>🏖️ Paid Leave (PL)</option>
                    <option value="UL" ${rec.status === 'UL' ? 'selected' : ''}>❌ Unpaid Leave (LOP)</option>
                    <option value="ML" ${rec.status === 'ML' ? 'selected' : ''}>🏥 Medical Leave (ML)</option>
                    <option value="EL" ${rec.status === 'EL' ? 'selected' : ''}>📚 Exam Leave (EL)</option>
                    <option value="OFF" ${rec.status === 'OFF' ? 'selected' : ''}>⚪ Weekly Off (OFF)</option>
                    <option value="HOL" ${rec.status === 'HOL' ? 'selected' : ''}>🎉 Public Holiday</option>
                </select>
            </td>
            <td class="py-2.5 px-3">
                <input type="time" value="${rec.in_time || ''}" class="w-full bg-white border border-slate-300 rounded px-1.5 py-1 text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-ca-600 ${!['P', 'HD', 'WFH'].includes(rec.status) ? 'opacity-40 bg-slate-100 cursor-not-allowed' : ''}" onchange="updateTime(${rec.day}, 'in_time', this.value)" ${!['P', 'HD', 'WFH'].includes(rec.status) || isBeforeJoining ? 'disabled' : ''}>
            </td>
            <td class="py-2.5 px-3">
                <input type="time" value="${rec.out_time || ''}" class="w-full bg-white border border-slate-300 rounded px-1.5 py-1 text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-ca-600 ${!['P', 'HD', 'WFH'].includes(rec.status) ? 'opacity-40 bg-slate-100 cursor-not-allowed' : ''}" onchange="updateTime(${rec.day}, 'out_time', this.value)" ${!['P', 'HD', 'WFH'].includes(rec.status) || isBeforeJoining ? 'disabled' : ''}>
            </td>
            <td class="py-2.5 px-3 text-center font-bold ${netHrs >= 9 ? 'text-emerald-600' : netHrs > 0 ? 'text-amber-600' : 'text-slate-400'}">
                ${netHrs > 0 ? `${netHrs} hrs` : '—'}
            </td>
            <td class="py-2.5 px-3">
                <span class="inline-block px-2 py-0.5 rounded text-[10px] border ${lateEval.color}">${lateEval.label}</span>
            </td>
            <td class="py-2.5 px-3">
                ${rec.status === 'WFH' ? `
                    <label class="flex items-center space-x-1 text-[11px] cursor-pointer">
                        <input type="checkbox" ${rec.wfh_productive ? 'checked' : ''} onchange="updateFlag(${rec.day}, 'wfh_productive', this.checked)" class="rounded text-ca-600">
                        <span class="text-slate-700">Productive</span>
                    </label>
                ` : rec.status === 'ML' ? `
                    <label class="flex items-center space-x-1 text-[11px] cursor-pointer" title="Clause 6: Medical leave >2 days requires certificate">
                        <input type="checkbox" ${rec.medical_cert_provided ? 'checked' : ''} onchange="updateFlag(${rec.day}, 'medical_cert_provided', this.checked)" class="rounded text-ca-600">
                        <span class="text-slate-700">Medical Cert</span>
                    </label>
                ` : '<span class="text-slate-300 text-[11px]">—</span>'}
            </td>
            <td class="py-2.5 px-3">
                <input type="text" placeholder="Assignment / Notes..." value="${rec.note || ''}" class="w-full bg-transparent border-b border-transparent hover:border-slate-300 focus:border-ca-600 focus:bg-white rounded px-1 py-0.5 text-xs text-slate-700 placeholder-slate-300 outline-none" onchange="updateNote(${rec.day}, this.value)" ${isBeforeJoining ? 'disabled' : ''}>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// User Record Update Handlers
function updateRecordStatus(day, newStatus) {
    const key = getMonthKey(currentYear, currentMonth);
    const rec = attendanceData[currentEmployeeId][key].find(r => r.day === day);
    if (rec) {
        rec.status = newStatus;
        if (newStatus === "P") {
            rec.in_time = "09:30";
            rec.out_time = "19:00";
        } else if (newStatus === "HD") {
            rec.in_time = "09:30";
            rec.out_time = "14:30";
        } else if (newStatus === "WFH") {
            rec.in_time = "09:30";
            rec.out_time = "19:00";
        } else {
            rec.in_time = "";
            rec.out_time = "";
        }
        saveToLocalStorage();
        renderTableRows();
        recalculatePayroll();
    }
}

function updateTime(day, field, val) {
    const key = getMonthKey(currentYear, currentMonth);
    const rec = attendanceData[currentEmployeeId][key].find(r => r.day === day);
    if (rec) {
        rec[field] = val;
        saveToLocalStorage();
        renderTableRows();
        recalculatePayroll();
    }
}

function updateFlag(day, field, val) {
    const key = getMonthKey(currentYear, currentMonth);
    const rec = attendanceData[currentEmployeeId][key].find(r => r.day === day);
    if (rec) {
        rec[field] = val;
        saveToLocalStorage();
        recalculatePayroll();
    }
}

function updateNote(day, val) {
    const key = getMonthKey(currentYear, currentMonth);
    const rec = attendanceData[currentEmployeeId][key].find(r => r.day === day);
    if (rec) {
        rec.note = val;
        saveToLocalStorage();
    }
}

// Recalculate Payroll & Update KPIs
function recalculatePayroll() {
    const emp = employees[currentEmployeeId];
    if (!emp) return;

    const key = getMonthKey(currentYear, currentMonth);
    const totalDays = getDaysInMonth(currentYear, currentMonth);

    // Read Inputs
    const basicSalary = parseFloat(document.getElementById("inputBasicSalary").value) || emp.basicSalary || 20000;
    const calcBasis = document.getElementById("selectCalcBasis").value || "calendar_days";
    const openingLeaves = parseFloat(document.getElementById("inputOpeningLeaves").value) || 0.0;
    const reimbursements = parseFloat(document.getElementById("inputReimbursements").value) || 0.0;
    const tds = parseFloat(document.getElementById("inputTDS").value) || 0.0;
    const otherDed = parseFloat(document.getElementById("inputOtherDeductions").value) || 0.0;

    // Save params
    monthParams[currentEmployeeId][key] = {
        basicSalary,
        calcBasis,
        openingLeaves,
        reimbursements,
        tds,
        otherDed
    };

    // Daily Rate
    const dailyRate = calcBasis === "standard_26" ? (basicSalary / 26.0) : (basicSalary / totalDays);

    // Pro-rata basic for joining month
    const joinDateObj = new Date(emp.joiningDate);
    const monthStartDate = new Date(currentYear, currentMonth, 1);
    const monthEndDate = new Date(currentYear, currentMonth, totalDays);

    let eligibleDays = totalDays;
    let proRataBasic = basicSalary;

    if (joinDateObj > monthEndDate) {
        proRataBasic = 0;
        eligibleDays = 0;
    } else if (joinDateObj > monthStartDate) {
        eligibleDays = (monthEndDate.getDate() - joinDateObj.getDate()) + 1;
        proRataBasic = (basicSalary / totalDays) * eligibleDays;
    }

    // Process Attendance
    const records = (attendanceData[currentEmployeeId] && attendanceData[currentEmployeeId][key]) || [];
    let presentDays = 0;
    let halfDays = 0;
    let wfhDays = 0;
    let paidLeavesRequested = 0;
    let explicitUnpaidLeaves = 0;
    let medicalLeaves = 0;
    let examLeaves = 0;
    let totalWorkedHours = 0;

    let lateCountTotal = 0;
    let lateAfter10Count = 0;

    let consecutiveMedical = 0;
    let missingMedicalCertDays = 0;

    records.forEach(rec => {
        const dayDate = new Date(currentYear, currentMonth, rec.day);
        if (dayDate < joinDateObj) return;

        // Working Hours
        if (["P", "HD", "WFH"].includes(rec.status)) {
            let hrs = calculateNetHours(rec.in_time, rec.out_time);
            if (hrs === 0) {
                hrs = rec.status === "HD" ? 4.5 : 9.0;
            }
            totalWorkedHours += hrs;
        }

        // Late evaluation
        if (["P", "HD", "WFH"].includes(rec.status) && rec.in_time) {
            const [h, m] = rec.in_time.split(":").map(Number);
            const inMins = h * 60 + m;
            if (inMins > 9 * 60 + 30) {
                lateCountTotal++;
            }
            if (inMins > 10 * 60) {
                lateAfter10Count++;
            }
        }

        // Status processing
        if (rec.status === "P") {
            presentDays++;
            consecutiveMedical = 0;
        } else if (rec.status === "HD") {
            halfDays++;
            consecutiveMedical = 0;
        } else if (rec.status === "WFH") {
            if (rec.wfh_productive) {
                wfhDays++;
            } else {
                paidLeavesRequested++;
            }
            consecutiveMedical = 0;
        } else if (rec.status === "PL") {
            paidLeavesRequested++;
            consecutiveMedical = 0;
        } else if (rec.status === "UL") {
            explicitUnpaidLeaves++;
            consecutiveMedical = 0;
        } else if (rec.status === "ML") {
            medicalLeaves++;
            paidLeavesRequested++;
            consecutiveMedical++;
            if (consecutiveMedical > 2 && !rec.medical_cert_provided) {
                missingMedicalCertDays++;
            }
        } else if (rec.status === "EL") {
            examLeaves++;
            paidLeavesRequested++;
            consecutiveMedical = 0;
        } else if (["OFF", "HOL"].includes(rec.status)) {
            consecutiveMedical = 0;
        }
    });

    // Leave Calculations (Clause 6: 1 paid leave credited per month, accumulated)
    const monthlyCreditedLeave = 1.0;
    const availableLeavePool = openingLeaves + monthlyCreditedLeave;

    let paidLeavesGranted = 0;
    let excessUnpaidLeaves = 0;
    let closingLeaves = 0;

    if (paidLeavesRequested <= availableLeavePool) {
        paidLeavesGranted = paidLeavesRequested;
        excessUnpaidLeaves = 0;
        closingLeaves = availableLeavePool - paidLeavesRequested;
    } else {
        paidLeavesGranted = availableLeavePool;
        excessUnpaidLeaves = paidLeavesRequested - availableLeavePool;
        closingLeaves = 0.0;
    }

    const totalUnpaidLeaves = excessUnpaidLeaves + explicitUnpaidLeaves;
    monthParams[currentEmployeeId][key].closingLeaves = closingLeaves;

    // Late Penalty Deductions (Clause 6: >10:00 AM treated as half-day leave, delays > 2 times attract deduction)
    let lateDeductionDays = 0;
    if (lateAfter10Count > 0) {
        lateDeductionDays += (lateAfter10Count * 0.5);
    }
    if (lateCountTotal > 2) {
        const remainingRepeated = Math.max(0, (lateCountTotal - 2) - lateAfter10Count);
        lateDeductionDays += (remainingRepeated * 0.5);
    }

    // Financial Computations
    const lopDeduction = totalUnpaidLeaves * dailyRate;
    const latePenaltyDeduction = lateDeductionDays * dailyRate;
    const grossEarnings = proRataBasic + reimbursements;
    const totalDeductions = lopDeduction + latePenaltyDeduction + tds + otherDed;
    const netSalary = Math.max(0, grossEarnings - totalDeductions);
    const leaveEncashmentVal = closingLeaves * dailyRate;

    // Retainership Bonus Progress
    const bonusTargetDateObj = new Date(emp.retainershipBonusTargetDate || "2027-12-31");
    const totalBonusDays = Math.max(1, (bonusTargetDateObj - joinDateObj) / (1000 * 60 * 60 * 24));
    const elapsedDays = Math.max(0, (Math.min(monthEndDate, bonusTargetDateObj) - joinDateObj) / (1000 * 60 * 60 * 24));
    const bonusPct = Math.min(100, Math.round((elapsedDays / totalBonusDays) * 100));

    // Update UI Elements
    document.getElementById("bonusProgressBar").style.width = `${bonusPct}%`;
    document.getElementById("bonusProgressText").textContent = `${bonusPct}% Achieved (${Math.round(elapsedDays)} / ${Math.round(totalBonusDays)} days)`;

    document.getElementById("kpiNetSalary").textContent = `₹${formatINR(netSalary)}`;
    document.getElementById("kpiGrossSub").textContent = `Gross: ₹${formatINR(grossEarnings)}`;
    document.getElementById("kpiDailyRate").textContent = `₹${dailyRate.toFixed(2)}`;

    document.getElementById("kpiWorkedDays").innerHTML = `${presentDays + wfhDays + (halfDays * 0.5)} <span class="text-xs font-normal text-slate-500">/ ${eligibleDays} days</span>`;
    document.getElementById("kpiTotalHours").textContent = `${totalWorkedHours.toFixed(1)} hrs`;

    document.getElementById("kpiLateCount").innerHTML = `${lateCountTotal} <span class="text-xs font-normal text-slate-500">times</span>`;
    document.getElementById("kpiLate10Count").textContent = `${lateAfter10Count} times`;

    const lateCard = document.getElementById("lateKpiCard");
    if (lateCountTotal > 2 || lateAfter10Count > 0) {
        lateCard.classList.add("border-rose-300", "bg-rose-50/20");
    } else {
        lateCard.classList.remove("border-rose-300", "bg-rose-50/20");
    }

    document.getElementById("kpiLeavesTaken").innerHTML = `${paidLeavesRequested + explicitUnpaidLeaves} <span class="text-xs font-normal text-slate-500">/ +1.0 earned</span>`;
    document.getElementById("kpiClosingLeaves").textContent = `${closingLeaves.toFixed(1)} days`;

    document.getElementById("kpiTotalDeductions").textContent = `₹${formatINR(totalDeductions)}`;
    document.getElementById("kpiLopPenaltySum").textContent = `₹${formatINR(lopDeduction + latePenaltyDeduction)}`;

    // Breakdown Section
    document.getElementById("summaryStandardBasic").textContent = `₹${formatINR(basicSalary)}`;
    document.getElementById("summaryProRataBasic").textContent = `₹${formatINR(proRataBasic)}`;
    document.getElementById("summaryPaidLeaveVal").textContent = `+ ₹${formatINR(paidLeavesGranted * dailyRate)} (${paidLeavesGranted} days)`;
    document.getElementById("summaryReimbursement").textContent = `₹${formatINR(reimbursements)}`;
    document.getElementById("summaryGross").textContent = `₹${formatINR(grossEarnings)}`;

    document.getElementById("summaryLopVal").textContent = `₹${formatINR(lopDeduction)} (${totalUnpaidLeaves} days)`;
    document.getElementById("summaryLateVal").textContent = `₹${formatINR(latePenaltyDeduction)} (${lateDeductionDays} half-days)`;
    document.getElementById("summaryTdsVal").textContent = `₹${formatINR(tds)}`;
    document.getElementById("summaryOtherVal").textContent = `₹${formatINR(otherDed)}`;
    document.getElementById("summaryTotalDed").textContent = `₹${formatINR(totalDeductions)}`;

    document.getElementById("summaryNetPayable").textContent = `₹${formatINR(netSalary)}`;
    document.getElementById("summaryBankDesc").textContent = emp.bankAccount ? `A/c: ${emp.bankAccount} (${emp.bankName || 'Bank'})` : "Direct Bank Transfer";
    document.getElementById("summaryAccLeave").textContent = `${closingLeaves.toFixed(1)} Days`;
    document.getElementById("summaryEncashVal").textContent = `₹${formatINR(leaveEncashmentVal)}`;

    saveToLocalStorage();
}

// Format Currency
function formatINR(val) {
    if (isNaN(val)) return "0.00";
    return Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Convert Number to Words (Indian Numbering)
function numberToWordsINR(num) {
    if (num === 0) return "Rupees Zero Only";
    const a = ["", "One ", "Two ", "Three ", "Four ", "Five ", "Six ", "Seven ", "Eight ", "Nine ", "Ten ", "Eleven ", "Twelve ", "Thirteen ", "Fourteen ", "Fifteen ", "Sixteen ", "Seventeen ", "Eighteen ", "Nineteen "];
    const b = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

    const wholeNum = Math.floor(num);
    const paise = Math.round((num - wholeNum) * 100);

    function convertGroup(n) {
        let str = "";
        if (n > 99) {
            str += a[Math.floor(n / 100)] + "Hundred ";
            n %= 100;
        }
        if (n > 19) {
            str += b[Math.floor(n / 10)] + " " + a[n % 10];
        } else {
            str += a[n];
        }
        return str;
    }

    let result = "";
    const crore = Math.floor(wholeNum / 10000000);
    const lakh = Math.floor((wholeNum % 10000000) / 100000);
    const thousand = Math.floor((wholeNum % 100000) / 1000);
    const hundred = wholeNum % 1000;

    if (crore > 0) result += convertGroup(crore) + "Crore ";
    if (lakh > 0) result += convertGroup(lakh) + "Lakh ";
    if (thousand > 0) result += convertGroup(thousand) + "Thousand ";
    if (hundred > 0) result += convertGroup(hundred);

    result = "Rupees " + result.trim();
    if (paise > 0) {
        result += " and " + convertGroup(paise).trim() + " Paise";
    }
    result += " Only";
    return result;
}

// Payslip Modal Generator
function generatePayslipModal() {
    const emp = employees[currentEmployeeId];
    if (!emp) return;

    const key = getMonthKey(currentYear, currentMonth);
    const totalDays = getDaysInMonth(currentYear, currentMonth);
    const params = (monthParams[currentEmployeeId] && monthParams[currentEmployeeId][key]) || {};
    const monthName = new Date(currentYear, currentMonth, 1).toLocaleString("default", { month: "long" });

    recalculatePayroll();

    const basicSalary = params.basicSalary || emp.basicSalary || 20000;
    const calcBasis = params.calcBasis || "calendar_days";
    const dailyRate = calcBasis === "standard_26" ? (basicSalary / 26.0) : (basicSalary / totalDays);

    const joinDateObj = new Date(emp.joiningDate);
    const monthStartDate = new Date(currentYear, currentMonth, 1);
    const monthEndDate = new Date(currentYear, currentMonth, totalDays);

    let eligibleDays = totalDays;
    let proRataBasic = basicSalary;

    if (joinDateObj > monthEndDate) {
        proRataBasic = 0;
        eligibleDays = 0;
    } else if (joinDateObj > monthStartDate) {
        eligibleDays = (monthEndDate.getDate() - joinDateObj.getDate()) + 1;
        proRataBasic = (basicSalary / totalDays) * eligibleDays;
    }

    const records = (attendanceData[currentEmployeeId] && attendanceData[currentEmployeeId][key]) || [];
    let presentCount = 0;
    let halfCount = 0;
    let wfhCount = 0;
    let plCount = 0;
    let lopCount = 0;
    let lateCount = 0;
    let late10Count = 0;

    records.forEach(r => {
        const d = new Date(currentYear, currentMonth, r.day);
        if (d < joinDateObj) return;

        if (r.status === "P") presentCount++;
        if (r.status === "HD") halfCount++;
        if (r.status === "WFH") wfhCount++;
        if (["PL", "ML", "EL"].includes(r.status)) plCount++;
        if (r.status === "UL") lopCount++;

        if (["P", "HD", "WFH"].includes(r.status) && r.in_time) {
            const [h, m] = r.in_time.split(":").map(Number);
            const inMins = h * 60 + m;
            if (inMins > 9 * 60 + 30) lateCount++;
            if (inMins > 10 * 60) late10Count++;
        }
    });

    const openingLeaves = params.openingLeaves || 0.0;
    const availablePool = openingLeaves + 1.0;
    const paidGranted = Math.min(plCount, availablePool);
    const excessLop = Math.max(0, plCount - availablePool);
    const totalUnpaid = excessLop + lopCount;
    const closingLeaves = Math.max(0, availablePool - plCount);

    let lateDedDays = 0;
    if (late10Count > 0) lateDedDays += (late10Count * 0.5);
    if (lateCount > 2) {
        const remaining = Math.max(0, (lateCount - 2) - late10Count);
        lateDedDays += (remaining * 0.5);
    }

    const lopDed = totalUnpaid * dailyRate;
    const lateDed = lateDedDays * dailyRate;
    const reimbursements = params.reimbursements || 0;
    const tds = params.tds || 0;
    const otherDed = params.otherDed || 0;
    const grossEarnings = proRataBasic + reimbursements;
    const totalDeductions = lopDed + lateDed + tds + otherDed;
    const netPayable = Math.max(0, grossEarnings - totalDeductions);

    // Populate Modal
    document.getElementById("psEmpName").textContent = emp.name;
    document.getElementById("psEmpDesignation").textContent = emp.designation;
    document.getElementById("psEmpJoiningDate").textContent = isNaN(joinDateObj) ? emp.joiningDate : joinDateObj.toLocaleDateString("en-US", { day: "2-digit", month: "long", year: "numeric" });
    document.getElementById("psEmpPan").textContent = emp.pan || "—";
    document.getElementById("psEmpAadhar").textContent = emp.aadhar || "—";
    document.getElementById("psBankName").textContent = emp.bankName || "—";
    document.getElementById("psBankAccount").textContent = emp.bankAccount || "—";
    document.getElementById("psBankIfsc").textContent = emp.ifsc || "—";

    document.getElementById("payslipMonthHeader").textContent = `Month: ${monthName} ${currentYear}`;
    document.getElementById("payslipWorkingDays").textContent = `${eligibleDays} Days (of ${totalDays})`;

    document.getElementById("psPresentDays").textContent = `${presentCount + wfhCount + (halfCount * 0.5)}`;
    document.getElementById("psPaidLeaves").textContent = `${paidGranted}`;
    document.getElementById("psUnpaidLeaves").textContent = `${totalUnpaid}`;
    document.getElementById("psClosingLeave").textContent = `${closingLeaves.toFixed(1)} Days`;

    document.getElementById("psBaseSalary").textContent = formatINR(basicSalary);
    document.getElementById("psProRataBasic").textContent = formatINR(proRataBasic);
    document.getElementById("psReimbursements").textContent = formatINR(reimbursements);
    document.getElementById("psGrossEarnings").textContent = `₹${formatINR(grossEarnings)}`;

    document.getElementById("psLop").textContent = formatINR(lopDed);
    document.getElementById("psLatePenalty").textContent = formatINR(lateDed);
    document.getElementById("psTds").textContent = formatINR(tds);
    document.getElementById("psOtherDed").textContent = formatINR(otherDed);
    document.getElementById("psTotalDeductions").textContent = `₹${formatINR(totalDeductions)}`;

    document.getElementById("psNetPayableFigures").textContent = `₹${formatINR(netPayable)}`;
    document.getElementById("psNetPayableWords").textContent = numberToWordsINR(netPayable);

    document.getElementById("payslipModal").classList.remove("hidden");
}

function closePayslipModal() {
    document.getElementById("payslipModal").classList.add("hidden");
}

// Policy Modal
function openPolicyModal() {
    document.getElementById("policyModal").classList.remove("hidden");
}

function closePolicyModal() {
    document.getElementById("policyModal").classList.add("hidden");
}

// Export CSV of Current Month
function exportMonthCSV() {
    const emp = employees[currentEmployeeId];
    if (!emp) return;

    const key = getMonthKey(currentYear, currentMonth);
    const records = (attendanceData[currentEmployeeId] && attendanceData[currentEmployeeId][key]) || [];
    const monthName = new Date(currentYear, currentMonth, 1).toLocaleString("default", { month: "long" });

    let csv = `M/s J Megha & Co. - Attendance & Salary Register\n`;
    csv += `Employee: ${emp.name}, Designation: ${emp.designation}\n`;
    csv += `Month: ${monthName} ${currentYear}\n\n`;
    csv += `Day,Date,Status,In Time,Out Time,Net Hours,Late Status,Productive/Cert,Notes\n`;

    records.forEach(r => {
        const dayDate = new Date(currentYear, currentMonth, r.day);
        const dayOfWeek = getDayName(currentYear, currentMonth, r.day);
        const netHrs = calculateNetHours(r.in_time, r.out_time);
        const lateEval = r.in_time ? getLateEvaluation(r.in_time).label : "";

        csv += `${r.day},"${r.day}-${monthName.slice(0,3)}-${currentYear} (${dayOfWeek})","${r.status}","${r.in_time || ''}","${r.out_time || ''}",${netHrs},"${lateEval}","${r.wfh_productive ? 'Yes' : 'No'}","${r.note || ''}"\n`;
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `Attendance_${emp.name.replace(/[^a-zA-Z0-9]/g, '_')}_${monthName}_${currentYear}.csv`;
    link.click();
}

// Export Full JSON Backup
function exportDataJSON() {
    const payload = {
        employees: employees,
        attendanceData: attendanceData,
        monthParams: monthParams,
        exportTimestamp: new Date().toISOString()
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `CA_Firm_Attendance_Backup_${new Date().toISOString().slice(0,10)}.json`;
    link.click();
}

// Import JSON Backup
function importDataJSON(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
        try {
            const data = JSON.parse(evt.target.result);
            if (data.employees) employees = data.employees;
            if (data.attendanceData) attendanceData = data.attendanceData;
            if (data.monthParams) monthParams = data.monthParams;
            if (!employees[currentEmployeeId]) {
                currentEmployeeId = Object.keys(employees)[0] || "emp_1";
            }
            saveToLocalStorage();
            populateEmployeeDropdown();
            renderEmployeeBanner();
            renderMonthView();
            alert("Attendance and employee database successfully restored!");
        } catch (err) {
            alert("Failed to parse JSON backup file.");
        }
    };
    reader.readAsText(file);
}
