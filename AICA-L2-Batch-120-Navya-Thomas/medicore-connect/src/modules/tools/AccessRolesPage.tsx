import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  UserCheck,
  Eye,
  Lock,
  Edit2,
  Save,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
  Users,
} from 'lucide-react';
import { getActiveUser } from '../../core/auth';
import {
  getAccessMatrix,
  saveAccessMatrix,
  DEFAULT_ACCESS_MATRIX,
  getUserAccessSummary,
} from '../../core/accessMatrix';
import { USERS } from '../../data/users';
import { ERPModule, ModuleAccessConfig } from '../../core/types';
import { formatAED } from '../../core/currency';
import { addAuditLog } from '../../core/storage';

interface AccessRolesPageProps {
  onNavigate: (route: string) => void;
}

export const AccessRolesPage: React.FC<AccessRolesPageProps> = ({ onNavigate }) => {
  const currentUser = getActiveUser();
  const isCFO = currentUser.role === 'CFO' || currentUser.userId === 'daniel.reed';

  const [matrix, setMatrix] = useState<ModuleAccessConfig[]>(getAccessMatrix());
  const [editingModule, setEditingModule] = useState<ERPModule | null>(null);
  const [editForm, setEditForm] = useState<Partial<ModuleAccessConfig>>({});
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const accessSummary = getUserAccessSummary(currentUser);

  useEffect(() => {
    const handleUpdate = () => setMatrix(getAccessMatrix());
    window.addEventListener('medicore-access-matrix-changed', handleUpdate);
    return () => window.removeEventListener('medicore-access-matrix-changed', handleUpdate);
  }, []);

  const handleStartEdit = (item: ModuleAccessConfig) => {
    if (!isCFO) {
      setMessage({
        text: 'Only the Chief Financial Officer (Daniel Reed) has permission to edit the Enterprise Access Matrix.',
        type: 'error',
      });
      return;
    }
    setEditingModule(item.module);
    setEditForm({ ...item });
  };

  const handleSaveEdit = () => {
    if (!isCFO || !editingModule) return;

    // Validate maker != approver
    if (editForm.makerUserId && editForm.approverUserId && editForm.makerUserId === editForm.approverUserId) {
      setMessage({
        text: 'Segregation of duties violation: The Maker and Approver must be distinct individuals.',
        type: 'error',
      });
      return;
    }

    const updated = matrix.map((m) => {
      if (m.module === editingModule) {
        const makerUser = USERS.find((u) => u.userId === editForm.makerUserId);
        const approverUser = USERS.find((u) => u.userId === editForm.approverUserId);
        return {
          ...m,
          ...editForm,
          makerName: makerUser?.name || m.makerName,
          approverName: approverUser?.name || m.approverName,
        };
      }
      return m;
    });

    saveAccessMatrix(updated);
    setMatrix(updated);
    setEditingModule(null);

    addAuditLog({
      entityType: 'AccessMatrix',
      entityId: editingModule,
      action: 'UPDATE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Updated Maker/Approver access rules for module ${editingModule}`,
      details: editForm as any,
    });

    setMessage({
      text: `Successfully updated Maker and Approver configuration for ${editingModule}.`,
      type: 'success',
    });
  };

  const handleResetDefaults = () => {
    if (!isCFO) return;
    saveAccessMatrix(DEFAULT_ACCESS_MATRIX);
    setMatrix(DEFAULT_ACCESS_MATRIX);
    setMessage({
      text: 'Enterprise Access Matrix restored to official IFRS Group defaults.',
      type: 'success',
    });
  };

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <ShieldCheck className="w-6 h-6 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              Enterprise Access Control & Segregation of Duties Matrix
            </h1>
            <p className="text-xs text-gray-500">
              One Maker and one Approver per module &bull; Universal Viewer permissions &bull; Section 1 Specification
            </p>
          </div>
        </div>

        {isCFO && (
          <button
            onClick={handleResetDefaults}
            className="px-3.5 py-1.5 border border-plum-300 text-[#5B2C83] hover:bg-plum-50 rounded-lg text-xs font-semibold shadow-2xs flex items-center space-x-1.5 transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Matrix to Default</span>
          </button>
        )}
      </div>

      {message && (
        <div
          className={`mb-5 p-3.5 rounded-xl border text-xs flex items-center justify-between shadow-2xs ${
            message.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <div className="flex items-center space-x-2">
            {message.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <span>{message.text}</span>
          </div>
          <button
            onClick={() => setMessage(null)}
            className="text-gray-400 hover:text-gray-600 cursor-pointer font-bold ml-4"
          >
            &times;
          </button>
        </div>
      )}

      {/* "My Access" Overview Card */}
      <div className="bg-gradient-to-r from-[#3F1D5C] to-[#5B2C83] rounded-2xl p-5 text-white shadow-md mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-amber-300 text-[10px] uppercase font-bold tracking-widest block mb-1">
              Active Session Profile
            </span>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-white/10 border border-white/20 flex items-center justify-center font-bold text-amber-300 text-sm">
                {currentUser.name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')}
              </div>
              <div>
                <h2 className="text-lg font-extrabold">{currentUser.name}</h2>
                <span className="text-plum-200 text-xs">
                  {currentUser.role} &bull; User ID: <span className="font-mono text-white">{currentUser.userId}</span>
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-md border border-white/15 rounded-xl p-3.5 flex flex-wrap gap-4 text-xs">
            <div>
              <span className="text-plum-200 block text-[10px] uppercase">General Permission</span>
              <span className="font-bold text-white flex items-center space-x-1">
                <Eye className="w-3.5 h-3.5 text-amber-300 inline" />
                <span>Viewer on ALL modules</span>
              </span>
            </div>
            <div className="h-8 w-px bg-white/20 hidden sm:block" />
            <div>
              <span className="text-plum-200 block text-[10px] uppercase">Maker Responsibilities</span>
              <span className="font-bold text-emerald-300">
                {accessSummary.makerModules.length > 0
                  ? accessSummary.makerModules.join(', ')
                  : 'None (Viewer only)'}
              </span>
            </div>
            <div className="h-8 w-px bg-white/20 hidden sm:block" />
            <div>
              <span className="text-plum-200 block text-[10px] uppercase">Approver Authorizations</span>
              <span className="font-bold text-amber-300">
                {accessSummary.isCFO
                  ? 'All Modules (CFO Final Approval)'
                  : accessSummary.approverModules.length > 0
                  ? accessSummary.approverModules.join(', ')
                  : 'None'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Access Matrix Table Card */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-sm text-gray-900">Module Access Control Matrix</h3>
            <p className="text-xs text-gray-500">
              {isCFO
                ? 'As CFO, you may reconfigure named Makers, Approvers, and limits below.'
                : 'Read-only view. Segregation of duties changes require CFO authorization.'}
            </p>
          </div>
          {!isCFO && (
            <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-medium">
              <Lock className="w-3 h-3 text-gray-400" />
              <span>Editing locked (CFO only)</span>
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#FAF7FC] text-gray-700 uppercase font-semibold text-[10px] border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">ERP Module</th>
                <th className="py-3 px-4">Designated Maker</th>
                <th className="py-3 px-4">Designated Approver</th>
                <th className="py-3 px-4">Approval Limit</th>
                <th className="py-3 px-4">Your Access</th>
                {isCFO && <th className="py-3 px-4 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {matrix.map((row) => {
                const isEditing = editingModule === row.module;
                const isUserMaker = currentUser.userId.toLowerCase() === row.makerUserId.toLowerCase();
                const isUserApprover =
                  currentUser.userId.toLowerCase() === row.approverUserId.toLowerCase() || isCFO;

                return (
                  <tr
                    key={row.module}
                    className={`hover:bg-plum-50/20 transition-colors ${
                      isEditing ? 'bg-amber-50/40' : ''
                    }`}
                  >
                    <td className="py-3.5 px-4 font-bold text-gray-900">
                      <div>
                        <span>{row.module}</span>
                        {row.description && (
                          <span className="block text-[10px] text-gray-400 font-normal">
                            {row.description}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Maker Column */}
                    <td className="py-3.5 px-4">
                      {isEditing ? (
                        <select
                          value={editForm.makerUserId || row.makerUserId}
                          onChange={(e) => {
                            const u = USERS.find((x) => x.userId === e.target.value);
                            setEditForm({
                              ...editForm,
                              makerUserId: e.target.value,
                              makerName: u?.name || '',
                            });
                          }}
                          className="px-2 py-1 border border-plum-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83]"
                        >
                          {USERS.map((u) => (
                            <option key={u.userId} value={u.userId}>
                              {u.name} ({u.role})
                            </option>
                          ))}
                        </select>
                      ) : (
                        <div className="flex items-center space-x-1.5">
                          <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="font-semibold text-gray-800">{row.makerName}</span>
                          <span className="font-mono text-[10px] text-gray-400">({row.makerUserId})</span>
                        </div>
                      )}
                    </td>

                    {/* Approver Column */}
                    <td className="py-3.5 px-4">
                      {isEditing ? (
                        <select
                          value={editForm.approverUserId || row.approverUserId}
                          onChange={(e) => {
                            const u = USERS.find((x) => x.userId === e.target.value);
                            setEditForm({
                              ...editForm,
                              approverUserId: e.target.value,
                              approverName: u?.name || '',
                            });
                          }}
                          className="px-2 py-1 border border-plum-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83]"
                        >
                          {USERS.filter((u) => u.approvalLimitAED !== 0 || u.role === 'CFO').map(
                            (u) => (
                              <option key={u.userId} value={u.userId}>
                                {u.name} ({u.role})
                              </option>
                            )
                          )}
                        </select>
                      ) : (
                        <div className="flex items-center space-x-1.5">
                          <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
                          <span className="font-semibold text-gray-800">{row.approverName}</span>
                          <span className="font-mono text-[10px] text-gray-400">({row.approverUserId})</span>
                        </div>
                      )}
                    </td>

                    {/* Approval Limit Column */}
                    <td className="py-3.5 px-4 font-mono font-medium text-gray-700">
                      {isEditing ? (
                        <input
                          type="number"
                          placeholder="Unlimited"
                          value={editForm.approvalLimitAED ?? ''}
                          onChange={(e) =>
                            setEditForm({
                              ...editForm,
                              approvalLimitAED: e.target.value ? Number(e.target.value) : null,
                            })
                          }
                          className="w-28 px-2 py-1 border border-plum-300 rounded text-xs"
                        />
                      ) : row.approvalLimitAED ? (
                        `AED ${row.approvalLimitAED.toLocaleString()}`
                      ) : (
                        <span className="text-gray-400 italic">Unlimited (CFO)</span>
                      )}
                    </td>

                    {/* User Role Badge */}
                    <td className="py-3.5 px-4">
                      {isUserMaker ? (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                          Maker
                        </span>
                      ) : isUserApprover ? (
                        <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] font-bold">
                          Approver
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-[10px]">
                          Viewer
                        </span>
                      )}
                    </td>

                    {/* Actions Column */}
                    {isCFO && (
                      <td className="py-3.5 px-4 text-right">
                        {isEditing ? (
                          <div className="flex items-center justify-end space-x-1.5">
                            <button
                              onClick={handleSaveEdit}
                              className="px-2.5 py-1 bg-[#5B2C83] text-white rounded text-[11px] font-semibold hover:bg-[#3F1D5C] cursor-pointer flex items-center space-x-1"
                            >
                              <Save className="w-3 h-3" />
                              <span>Save</span>
                            </button>
                            <button
                              onClick={() => setEditingModule(null)}
                              className="px-2 py-1 text-gray-500 hover:text-gray-700 text-[11px] cursor-pointer"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleStartEdit(row)}
                            className="p-1 text-gray-400 hover:text-[#5B2C83] rounded hover:bg-plum-50 cursor-pointer"
                            title="Edit rule"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
