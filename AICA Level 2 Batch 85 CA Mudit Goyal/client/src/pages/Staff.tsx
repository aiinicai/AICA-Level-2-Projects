import React, { useCallback, useEffect, useState } from 'react';
import {
  Staff, getStaff, createStaff, updateStaff, toggleStaffActive, resetStaffPassword,
} from '../api';
import { formatDateDdMmmYy } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';
import Modal from '../components/Modal';
import { useAuth } from '../contexts/AuthContext';

const StaffPage: React.FC = () => {
  const { user } = useAuth();
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Staff | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getStaff();
      setStaff(res.data);
      setError('');
    } catch (err) {
      setError(errorMessage(err, 'Could not load staff'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (member: Staff) => {
    const verb = member.isActive ? 'Deactivate' : 'Reactivate';
    if (!window.confirm(`${verb} ${member.staffName}?`)) return;
    try {
      await toggleStaffActive(member.id);
      await load();
    } catch (err) {
      window.alert(errorMessage(err, 'That did not work'));
    }
  };

  const reset = async (member: Staff) => {
    const password = window.prompt(`New password for ${member.staffName} (at least 8 characters)`);
    if (!password) return;
    try {
      await resetStaffPassword(member.id, password);
      window.alert('Password reset.');
    } catch (err) {
      window.alert(errorMessage(err, 'Could not reset the password'));
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Staff</h1>
        <button className="btn-primary" onClick={() => { setEditing(null); setFormOpen(true); }}>
          + Add staff
        </button>
      </div>

      {error && <div className="card text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="text-sm text-gray-500">Loading…</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header">Name</th>
                <th className="table-header">Email</th>
                <th className="table-header">Role</th>
                <th className="table-header">Joined</th>
                <th className="table-header">Status</th>
                <th className="table-header" />
              </tr>
            </thead>
            <tbody>
              {staff.map((member) => (
                <tr key={member.id} className="hover:bg-gray-50">
                  <td className="table-cell">
                    <div className="font-medium">{member.staffName}</div>
                    {member.designation && <div className="text-xs text-gray-400">{member.designation}</div>}
                  </td>
                  <td className="table-cell">{member.email}</td>
                  <td className="table-cell">
                    <span className={`badge ${member.user?.role === 'ADMIN' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-700'}`}>
                      {member.user?.role ?? '—'}
                    </span>
                  </td>
                  <td className="table-cell whitespace-nowrap">{formatDateDdMmmYy(member.joiningDate)}</td>
                  <td className="table-cell">
                    <span className={`badge ${member.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                      {member.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="table-cell text-right whitespace-nowrap space-x-3">
                    <button className="text-brand-600 hover:underline text-sm" onClick={() => { setEditing(member); setFormOpen(true); }}>
                      Edit
                    </button>
                    <button className="text-brand-600 hover:underline text-sm" onClick={() => reset(member)}>
                      Reset password
                    </button>
                    {/* Deactivating yourself locks you out of the app you are in. */}
                    {member.id !== user?.staffId && (
                      <button className="text-red-600 hover:underline text-sm" onClick={() => toggle(member)}>
                        {member.isActive ? 'Deactivate' : 'Reactivate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <StaffModal
        member={editing}
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false);
          load();
        }}
      />
    </div>
  );
};

const StaffModal: React.FC<{
  member: Staff | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}> = ({ member, open, onClose, onSaved }) => {
  const [staffName, setStaffName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [designation, setDesignation] = useState('');
  const [joiningDate, setJoiningDate] = useState('');
  const [role, setRole] = useState('STAFF');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setStaffName(member?.staffName ?? '');
    setEmail(member?.email ?? '');
    setPhone(member?.phone ?? '');
    setDesignation(member?.designation ?? '');
    setJoiningDate(member?.joiningDate?.slice(0, 10) ?? '');
    setRole(member?.user?.role ?? 'STAFF');
    setPassword('');
    setError('');
  }, [open, member]);

  const submit = async () => {
    setError('');
    if (!staffName.trim()) return setError('Name is required');
    if (!member && password.length < 8) return setError('Password must be at least 8 characters');

    setBusy(true);
    try {
      const payload = { staffName: staffName.trim(), phone: phone.trim(), designation: designation.trim(), joiningDate: joiningDate || null, role };
      if (member) {
        await updateStaff(member.id, payload);
      } else {
        await createStaff({ ...payload, email: email.trim(), password });
      }
      onSaved();
    } catch (err) {
      setError(errorMessage(err, 'Could not save'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} title={member ? `Edit ${member.staffName}` : 'Add staff'} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="label">Name *</label>
          <input className="input-field" value={staffName} onChange={(e) => setStaffName(e.target.value)} />
        </div>
        <div>
          <label className="label">Email {member ? '' : '*'}</label>
          <input
            className="input-field"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            // The email is the login. Changing it would orphan the account, so
            // it is fixed once the record exists.
            disabled={!!member}
          />
          {member && <p className="text-xs text-gray-500 mt-1">The email is the sign-in name and cannot be changed here.</p>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Phone</label>
            <input className="input-field" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div>
            <label className="label">Designation</label>
            <input className="input-field" value={designation} onChange={(e) => setDesignation(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Joining date</label>
            <input className="input-field" type="date" value={joiningDate} onChange={(e) => setJoiningDate(e.target.value)} />
          </div>
          <div>
            <label className="label">Role</label>
            <select className="input-field" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="STAFF">Staff</option>
              <option value="ADMIN">Admin</option>
            </select>
          </div>
        </div>
        {!member && (
          <div>
            <label className="label">Password *</label>
            <input className="input-field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
          </div>
        )}

        {error && <div role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}

        <div className="flex gap-2 justify-end pt-1">
          <button className="btn-secondary" onClick={onClose} disabled={busy}>Cancel</button>
          <button className="btn-primary" onClick={submit} disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
        </div>
      </div>
    </Modal>
  );
};

export default StaffPage;
