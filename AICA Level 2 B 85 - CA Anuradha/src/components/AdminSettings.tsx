import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Department, Role, DepartmentCategory, User } from '../types';
import {
  formatDate,
  formatIST,
} from '../utils/formatters';
import {
  exportConsolidatedToCSV,
  exportDepartmentSummaryToCSV,
} from '../utils/exportCsv';
import {
  Calendar,
  Layers,
  Users,
  Download,
  Plus,
  Trash2,
  Edit,
  Save,
  CheckCircle2,
  Lock,
  Unlock,
  RotateCcw,
  Sliders,
  Shield,
  FileSpreadsheet,
  Building,
  Server,
  IndianRupee,
} from 'lucide-react';

export const AdminSettings: React.FC = () => {
  const {
    months,
    activeMonth,
    categories,
    users,
    openNewMonth,
    closeMonth,
    addCategory,
    editCategory,
    deleteCategory,
    addUser,
    updateUser,
    resetToInitialData,
    currentSubmissions,
  } = useApp();

  // Active Admin Sub-tab: 'cycles' | 'categories' | 'users' | 'export'
  const [adminTab, setAdminTab] = useState<'cycles' | 'categories' | 'users' | 'export'>('cycles');

  // New Month Cycle Form State
  const [newMonthId, setNewMonthId] = useState<string>('2026-11');
  const [newMonthLabel, setNewMonthLabel] = useState<string>('November 2026');
  const [newMonthDeadline, setNewMonthDeadline] = useState<string>('2026-10-28');
  const [newMonthRate, setNewMonthRate] = useState<number>(0.01825);
  const [newMonthRateSource, setNewMonthRateSource] = useState<string>('RBI Reference Rate Benchmark');
  const [cycleMsg, setCycleMsg] = useState<string | null>(null);

  // New Category Form State
  const [newCatDept, setNewCatDept] = useState<Department>('HR');
  const [newCatName, setNewCatName] = useState<string>('');
  const [newCatDesc, setNewCatDesc] = useState<string>('');

  // New User Form State
  const [newUserName, setNewUserName] = useState<string>('');
  const [newUserEmail, setNewUserEmail] = useState<string>('');
  const [newUserRole, setNewUserRole] = useState<Role>('department_submitter');
  const [newUserDept, setNewUserDept] = useState<Department | undefined>('HR');
  const [newUserTitle, setNewUserTitle] = useState<string>('');

  // Handle Open New Month
  const handleCreateMonth = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMonthId || !newMonthLabel || !newMonthDeadline) {
      alert('Please fill all required cycle fields.');
      return;
    }
    openNewMonth(newMonthId, newMonthLabel, newMonthDeadline, newMonthRate, newMonthRateSource);
    setCycleMsg(`Cycle "${newMonthLabel}" opened successfully!`);
    setTimeout(() => setCycleMsg(null), 3500);
  };

  // Handle Add Category
  const handleAddCategory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName.trim()) {
      alert('Please enter a category name.');
      return;
    }
    addCategory({
      department: newCatDept,
      name: newCatName.trim(),
      description: newCatDesc.trim(),
    });
    setNewCatName('');
    setNewCatDesc('');
  };

  // Handle Add User
  const handleAddUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserName.trim() || !newUserEmail.trim()) {
      alert('Please enter user name and email.');
      return;
    }
    addUser({
      name: newUserName.trim(),
      email: newUserEmail.trim(),
      role: newUserRole,
      department: newUserRole === 'department_submitter' ? newUserDept : undefined,
      title: newUserTitle.trim() || `${newUserDept || ''} Lead`,
    });
    setNewUserName('');
    setNewUserEmail('');
    setNewUserTitle('');
  };

  const getDeptIcon = (dept: Department) => {
    switch (dept) {
      case 'HR':
        return <Users className="w-3.5 h-3.5 text-blue-600" />;
      case 'Admin':
        return <Building className="w-3.5 h-3.5 text-amber-600" />;
      case 'IT':
        return <Server className="w-3.5 h-3.5 text-indigo-600" />;
      case 'Finance':
        return <IndianRupee className="w-3.5 h-3.5 text-emerald-600" />;
    }
  };

  return (
    <div id="admin-settings-container" className="space-y-6">
      
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-slate-100 text-slate-800 border border-slate-300 uppercase tracking-wider">
                System Administration
              </span>
              <h2 className="text-xl font-bold text-slate-900">
                Governance, Categories & User Management
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Configure monthly operational deadlines, line-item classification taxonomies, and access permissions.
            </p>
          </div>
        </div>
      </div>

      {/* Admin Sub Navigation Tabs */}
      <div className="flex border-b border-slate-200 gap-2 text-xs font-bold">
        <button
          onClick={() => setAdminTab('cycles')}
          className={`pb-2.5 px-4 transition-all border-b-2 flex items-center gap-1.5 ${
            adminTab === 'cycles'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Monthly Cycles & Deadlines</span>
        </button>

        <button
          onClick={() => setAdminTab('categories')}
          className={`pb-2.5 px-4 transition-all border-b-2 flex items-center gap-1.5 ${
            adminTab === 'categories'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Department Category Taxonomies</span>
        </button>

        <button
          onClick={() => setAdminTab('users')}
          className={`pb-2.5 px-4 transition-all border-b-2 flex items-center gap-1.5 ${
            adminTab === 'users'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>User Directory & Roles</span>
        </button>

        <button
          onClick={() => setAdminTab('export')}
          className={`pb-2.5 px-4 transition-all border-b-2 flex items-center gap-1.5 ${
            adminTab === 'export'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          <span>Reports & System Backups</span>
        </button>
      </div>

      {/* SUB-TAB 1: Monthly Cycles */}
      {adminTab === 'cycles' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Create New Cycle Form */}
          <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Plus className="w-4 h-4 text-blue-600" />
              <span>Open New Monthly Cycle</span>
            </h3>

            {cycleMsg && (
              <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{cycleMsg}</span>
              </div>
            )}

            <form onSubmit={handleCreateMonth} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-medium mb-1">Month Key (YYYY-MM):</label>
                <input
                  type="text"
                  required
                  value={newMonthId}
                  onChange={(e) => setNewMonthId(e.target.value)}
                  placeholder="2026-11"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 font-mono text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Display Label:</label>
                <input
                  type="text"
                  required
                  value={newMonthLabel}
                  onChange={(e) => setNewMonthLabel(e.target.value)}
                  placeholder="November 2026"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Submission Deadline:</label>
                <input
                  type="date"
                  required
                  value={newMonthDeadline}
                  onChange={(e) => setNewMonthDeadline(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Initial FX Rate (INR→AUD):</label>
                <input
                  type="number"
                  step="0.00001"
                  required
                  value={newMonthRate}
                  onChange={(e) => setNewMonthRate(parseFloat(e.target.value) || 0.01825)}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 font-mono text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Rate Benchmark Source:</label>
                <input
                  type="text"
                  value={newMonthRateSource}
                  onChange={(e) => setNewMonthRateSource(e.target.value)}
                  placeholder="e.g. RBI reference rate as of 24/10/2026"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-sm transition-colors mt-2"
              >
                Open Cycle for Submissions
              </button>
            </form>
          </div>

          {/* List of Existing Cycles */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Active & Historic Monthly Cycles
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="py-2.5 px-3">Month Cycle</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Deadline</th>
                    <th className="py-2.5 px-3 font-mono">FX Rate</th>
                    <th className="py-2.5 px-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {months.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-3 font-bold text-slate-900">
                        {m.label} <span className="text-[10px] text-slate-400 font-mono">({m.id})</span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            m.status === 'Open'
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : m.status === 'Ready for Approval'
                              ? 'bg-blue-50 text-blue-700 border-blue-200'
                              : m.status === 'Approved'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-slate-100 text-slate-600 border-slate-200'
                          }`}
                        >
                          {m.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">
                        {formatDate(m.submissionDeadline)}
                      </td>
                      <td className="py-2.5 px-3 font-mono font-semibold text-emerald-700">
                        {m.exchangeRate}
                      </td>
                      <td className="py-2.5 px-3">
                        {m.status !== 'Closed' ? (
                          <button
                            type="button"
                            onClick={() => {
                              if (confirm(`Lock & close monthly cycle "${m.label}"?`)) {
                                closeMonth(m.id);
                              }
                            }}
                            className="text-slate-600 hover:text-red-700 font-semibold text-[11px]"
                          >
                            Close Cycle
                          </button>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Archived</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* SUB-TAB 2: Department Category Taxonomies */}
      {adminTab === 'categories' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Add Category Form */}
          <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Plus className="w-4 h-4 text-blue-600" />
              <span>Add Department Category</span>
            </h3>

            <form onSubmit={handleAddCategory} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-medium mb-1">Department:</label>
                <select
                  value={newCatDept}
                  onChange={(e) => setNewCatDept(e.target.value as Department)}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs font-semibold focus:ring-1 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="HR">HR Department</option>
                  <option value="Admin">Admin Department</option>
                  <option value="IT">IT Department</option>
                  <option value="Finance">Finance Department</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Category Name:</label>
                <input
                  type="text"
                  required
                  value={newCatName}
                  onChange={(e) => setNewCatName(e.target.value)}
                  placeholder="e.g. Employee Wellness Program"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Description / Guidelines:</label>
                <textarea
                  rows={2}
                  value={newCatDesc}
                  onChange={(e) => setNewCatDesc(e.target.value)}
                  placeholder="Explain what expenses should be categorized here..."
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-sm transition-colors mt-2"
              >
                Save New Category
              </button>
            </form>
          </div>

          {/* Existing Categories Table */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Configured Categories ({categories.length})
            </h3>

            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold sticky top-0">
                    <th className="py-2.5 px-3">Dept</th>
                    <th className="py-2.5 px-3">Category Name</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3 w-12 text-center"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {categories.map((cat) => (
                    <tr key={cat.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-3">
                        <span className="flex items-center gap-1 font-bold text-slate-800">
                          {getDeptIcon(cat.department)}
                          {cat.department}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-900">
                        {cat.name}
                      </td>
                      <td className="py-2.5 px-3 text-slate-500">
                        {cat.description}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <button
                          type="button"
                          onClick={() => {
                            if (confirm(`Delete category "${cat.name}"?`)) {
                              deleteCategory(cat.id);
                            }
                          }}
                          className="text-slate-400 hover:text-red-600 p-1"
                          title="Delete category"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* SUB-TAB 3: User Directory */}
      {adminTab === 'users' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Add User Form */}
          <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Plus className="w-4 h-4 text-blue-600" />
              <span>Provision App User</span>
            </h3>

            <form onSubmit={handleAddUser} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-medium mb-1">Full Name:</label>
                <input
                  type="text"
                  required
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Email:</label>
                <input
                  type="email"
                  required
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="rahul.sharma@maropost.com"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">System Role:</label>
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value as Role)}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs font-semibold focus:ring-1 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="department_submitter">Department Submitter</option>
                  <option value="finance_controller">Finance Controller</option>
                  <option value="management">Management Approver</option>
                  <option value="admin">System Administrator</option>
                </select>
              </div>

              {newUserRole === 'department_submitter' && (
                <div>
                  <label className="block text-slate-700 font-medium mb-1">Assigned Department:</label>
                  <select
                    value={newUserDept}
                    onChange={(e) => setNewUserDept(e.target.value as Department)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs font-semibold focus:ring-1 focus:ring-blue-500 focus:outline-none"
                  >
                    <option value="HR">HR</option>
                    <option value="Admin">Admin</option>
                    <option value="IT">IT</option>
                    <option value="Finance">Finance</option>
                  </select>
                </div>
              )}

              <div>
                <label className="block text-slate-700 font-medium mb-1">Corporate Title:</label>
                <input
                  type="text"
                  value={newUserTitle}
                  onChange={(e) => setNewUserTitle(e.target.value)}
                  placeholder="e.g. Lead Talent Acquisition"
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-sm transition-colors mt-2"
              >
                Provision User
              </button>
            </form>
          </div>

          {/* User List */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Registered Users & Roles ({users.length})
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="py-2.5 px-3">Name</th>
                    <th className="py-2.5 px-3">Role</th>
                    <th className="py-2.5 px-3">Department</th>
                    <th className="py-2.5 px-3">Title</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-3">
                        <div className="font-bold text-slate-900">{u.name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">{u.email}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                          {u.role}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-800">
                        {u.department || '—'}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">
                        {u.title}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* SUB-TAB 4: Reports & System Backups */}
      {adminTab === 'export' && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Data Exports & Administrative Tools
            </h3>
            <p className="text-xs text-slate-500">
              Download consolidated corporate reports, raw database JSON backups, or reset demo state.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            {/* Export 1: Consolidated CSV */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 flex flex-col justify-between space-y-3">
              <div>
                <FileSpreadsheet className="w-6 h-6 text-emerald-600 mb-2" />
                <h4 className="font-bold text-slate-900 text-xs">
                  Consolidated Line Items CSV
                </h4>
                <p className="text-[11px] text-slate-500 mt-1">
                  Full dataset of all line items, departments, categories, INR/AUD conversions, priorities, and approval records for {activeMonth.label}.
                </p>
              </div>

              <button
                type="button"
                onClick={() => exportConsolidatedToCSV(activeMonth, currentSubmissions)}
                className="flex items-center justify-center gap-1.5 w-full py-2 bg-white hover:bg-slate-50 text-slate-800 font-bold border border-slate-300 rounded-lg text-xs shadow-xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Line Items CSV</span>
              </button>
            </div>

            {/* Export 2: Department Summary CSV */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 flex flex-col justify-between space-y-3">
              <div>
                <Download className="w-6 h-6 text-blue-600 mb-2" />
                <h4 className="font-bold text-slate-900 text-xs">
                  Department Summary CSV
                </h4>
                <p className="text-[11px] text-slate-500 mt-1">
                  Department-level subtotal aggregates in INR & AUD with priority breakdowns for executive briefings.
                </p>
              </div>

              <button
                type="button"
                onClick={() => exportDepartmentSummaryToCSV(activeMonth, currentSubmissions)}
                className="flex items-center justify-center gap-1.5 w-full py-2 bg-white hover:bg-slate-50 text-slate-800 font-bold border border-slate-300 rounded-lg text-xs shadow-xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Dept Summary CSV</span>
              </button>
            </div>

            {/* Reset Demo State */}
            <div className="p-4 rounded-xl border border-red-200 bg-red-50/30 flex flex-col justify-between space-y-3">
              <div>
                <RotateCcw className="w-6 h-6 text-red-600 mb-2" />
                <h4 className="font-bold text-slate-900 text-xs">
                  Reset Demo State
                </h4>
                <p className="text-[11px] text-slate-500 mt-1">
                  Restore default pre-seeded state for October 2026 with realistic initial corporate figures across all 4 departments.
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  if (confirm('Are you sure you want to reset all data back to the default demo state?')) {
                    resetToInitialData();
                  }
                }}
                className="flex items-center justify-center gap-1.5 w-full py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg text-xs shadow-xs"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Demo Database</span>
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
