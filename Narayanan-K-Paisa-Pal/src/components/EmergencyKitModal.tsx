import React, { useState } from 'react';
import {
  X,
  Printer,
  ShieldAlert,
  Building,
  HeartPulse,
  FolderArchive,
  UserCheck,
  Plus,
  Trash2,
} from 'lucide-react';
import { AppRow, UserProfile } from '../types';
import { inr, inrS, INV, longD, REC, todayIST } from '../utils/calculations';
import { triggerPrint } from '../utils/exportImport';

interface Props {
  isOpen: boolean;
  rows: AppRow[];
  profile: UserProfile;
  onUpdateProfile: (profile: UserProfile) => void;
  onClose: () => void;
}

export const EmergencyKitModal: React.FC<Props> = ({
  isOpen,
  rows,
  profile,
  onUpdateProfile,
  onClose,
}) => {
  const [notes, setNotes] = useState(
    profile.emergencyNotes ||
      'Important original certificates, deposit receipts and locker keys are stored in the home safe / steel almirah. In case of emergency, please contact the family members and advisors listed below.'
  );

  const [contacts, setContacts] = useState<
    { name: string; relation: string; phone: string }[]
  >(
    profile.emergencyContacts || [
      { name: 'Family Doctor', relation: 'Medical', phone: '' },
      { name: 'Chartered Accountant / Tax Advisor', relation: 'Financial', phone: '' },
      { name: 'Key Bank Branch Manager', relation: 'Banking', phone: '' },
    ]
  );

  if (!isOpen) return null;

  const saveEmergencyDetails = () => {
    onUpdateProfile({
      ...profile,
      emergencyNotes: notes,
      emergencyContacts: contacts,
    });
  };

  const handleAddContact = () => {
    setContacts([...contacts, { name: '', relation: '', phone: '' }]);
  };

  const handleContactChange = (index: number, field: string, val: string) => {
    const next = contacts.map((c, i) => (i === index ? { ...c, [field]: val } : c));
    setContacts(next);
  };

  const handleRemoveContact = (index: number) => {
    setContacts(contacts.filter((_, i) => i !== index));
  };

  // Group assets for emergency sheet
  const bankFds = rows.filter((r) => r.kind === 'inv' && ['fd', 'rd', 'bond'].includes(r.data?.type));
  const otherInvs = rows.filter((r) => r.kind === 'inv' && !['fd', 'rd', 'bond'].includes(r.data?.type));
  const policies = rows.filter(
    (r) =>
      r.kind === 'due' &&
      ['insurance', 'mediclaim', 'vehicle'].includes(r.data?.category)
  );
  const records = rows.filter((r) => r.kind === 'rec');

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-3 sm:p-6 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5]">
        {/* Modal Top Control Bar (Hidden during printing) */}
        <div className="no-print flex items-center justify-between px-6 py-4 border-b border-[#DCE2EA] dark:border-[#25324A] bg-slate-50 dark:bg-slate-900/60 rounded-t-2xl">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <h2 className="font-bold text-base">Family Emergency & Nominee Kit</h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                saveEmergencyDetails();
                triggerPrint();
              }}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#0B3B66] dark:bg-[#5B9BE0] text-white dark:text-[#08121F] hover:brightness-110 transition shadow-sm"
            >
              <Printer className="w-4 h-4" />
              <span>Print / Save as PDF</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Document Body */}
        <div className="p-6 sm:p-8 overflow-y-auto flex-1 space-y-6 text-sm">
          {/* Document Header */}
          <div className="text-center pb-4 border-b-2 border-slate-800 dark:border-slate-300">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight uppercase">
              Family Financial Emergency Summary
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
              Confidential Family Document · Prepared on {longD(todayIST())}
            </p>
          </div>

          {/* Section 1: Bank Fixed Deposits & Bonds */}
          <div>
            <h3 className="font-bold text-sm uppercase tracking-wider text-[#0B3B66] dark:text-[#5B9BE0] border-b pb-1 mb-2.5 flex items-center gap-1.5">
              <Building className="w-4 h-4" />
              <span>1. Bank Fixed Deposits & Bonds</span>
            </h3>

            {bankFds.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b bg-slate-100 dark:bg-slate-800/80">
                      <th className="py-2 px-2">Institution & Account/Folio</th>
                      <th className="py-2 px-2">Holder</th>
                      <th className="py-2 px-2 text-right">Invested / Value</th>
                      <th className="py-2 px-2">Maturity Date</th>
                      <th className="py-2 px-2">Notes / Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {bankFds.map((r) => {
                      const d = r.data || {};
                      return (
                        <tr key={r.id}>
                          <td className="py-2 px-2 font-medium">
                            {d.name} {d.institution ? `(${d.institution})` : ''}
                            {d.ref && <div className="text-[11px] text-slate-500">No: {d.ref}</div>}
                          </td>
                          <td className="py-2 px-2">{d.holder || '–'}</td>
                          <td className="py-2 px-2 text-right font-semibold">
                            {d.current ? inr(d.current) : d.invested ? inr(d.invested) : '–'}
                          </td>
                          <td className="py-2 px-2">{d.maturity ? longD(d.maturity) : '–'}</td>
                          <td className="py-2 px-2 text-[11px] text-slate-500">{d.notes || '–'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No deposits or bonds registered.</p>
            )}
          </div>

          {/* Section 2: Insurance & Mediclaim Policies */}
          <div>
            <h3 className="font-bold text-sm uppercase tracking-wider text-[#0B3B66] dark:text-[#5B9BE0] border-b pb-1 mb-2.5 flex items-center gap-1.5">
              <HeartPulse className="w-4 h-4" />
              <span>2. Life, Health & Vehicle Insurance</span>
            </h3>

            {policies.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b bg-slate-100 dark:bg-slate-800/80">
                      <th className="py-2 px-2">Policy / Provider</th>
                      <th className="py-2 px-2">Policy No.</th>
                      <th className="py-2 px-2">Insured / Holder</th>
                      <th className="py-2 px-2 text-right">Premium</th>
                      <th className="py-2 px-2">Renewal Due</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {policies.map((r) => {
                      const d = r.data || {};
                      return (
                        <tr key={r.id}>
                          <td className="py-2 px-2 font-medium">
                            {d.name} {d.provider ? `(${d.provider})` : ''}
                          </td>
                          <td className="py-2 px-2 font-mono text-[11px]">{d.ref || '–'}</td>
                          <td className="py-2 px-2">{d.holder || '–'}</td>
                          <td className="py-2 px-2 text-right font-semibold">
                            {d.amount ? inr(d.amount) : '–'}
                          </td>
                          <td className="py-2 px-2">{longD(d.due)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No insurance policies registered.</p>
            )}
          </div>

          {/* Section 3: Government Records & Documents */}
          <div>
            <h3 className="font-bold text-sm uppercase tracking-wider text-[#0B3B66] dark:text-[#5B9BE0] border-b pb-1 mb-2.5 flex items-center gap-1.5">
              <FolderArchive className="w-4 h-4" />
              <span>3. Document Records & Expiries</span>
            </h3>

            {records.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b bg-slate-100 dark:bg-slate-800/80">
                      <th className="py-2 px-2">Document</th>
                      <th className="py-2 px-2">Document / Account No.</th>
                      <th className="py-2 px-2">Holder</th>
                      <th className="py-2 px-2">Expiry Date</th>
                      <th className="py-2 px-2">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {records.map((r) => {
                      const d = r.data || {};
                      return (
                        <tr key={r.id}>
                          <td className="py-2 px-2 font-medium">
                            {d.title} ({REC[d.type] || d.type})
                          </td>
                          <td className="py-2 px-2 font-mono text-[11px]">{d.number || '–'}</td>
                          <td className="py-2 px-2">{d.holder || '–'}</td>
                          <td className="py-2 px-2">{d.expires ? longD(d.expires) : 'No expiry'}</td>
                          <td className="py-2 px-2 text-[11px] text-slate-500">{d.notes || '–'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No document records registered.</p>
            )}
          </div>

          {/* Section 4: Emergency Contacts */}
          <div>
            <div className="flex items-center justify-between border-b pb-1 mb-2.5">
              <h3 className="font-bold text-sm uppercase tracking-wider text-[#0B3B66] dark:text-[#5B9BE0] flex items-center gap-1.5">
                <UserCheck className="w-4 h-4" />
                <span>4. Key Emergency Contacts & Advisors</span>
              </h3>
              <button
                type="button"
                onClick={handleAddContact}
                className="no-print text-xs font-semibold text-[#0E7C86] hover:underline flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Contact</span>
              </button>
            </div>

            <div className="space-y-2">
              {contacts.map((c, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <input
                    type="text"
                    placeholder="Name / Role"
                    value={c.name}
                    onChange={(e) => handleContactChange(i, 'name', e.target.value)}
                    className="flex-1 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5"
                  />
                  <input
                    type="text"
                    placeholder="Relationship / Specialty"
                    value={c.relation}
                    onChange={(e) => handleContactChange(i, 'relation', e.target.value)}
                    className="w-36 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5"
                  />
                  <input
                    type="tel"
                    placeholder="Phone number"
                    value={c.phone}
                    onChange={(e) => handleContactChange(i, 'phone', e.target.value)}
                    className="w-40 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5"
                  />
                  <button
                    type="button"
                    onClick={() => handleRemoveContact(i)}
                    className="no-print p-1 text-rose-500 hover:text-rose-700"
                    aria-label="Remove contact"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Section 5: Instructions to Family / Safe Location */}
          <div>
            <h3 className="font-bold text-sm uppercase tracking-wider text-[#0B3B66] dark:text-[#5B9BE0] border-b pb-1 mb-2">
              5. Instructions & Storage Location for Next-of-Kin
            </h3>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Bank locker is at Branch X (Locker #104, Key with spouse). Original deeds are in safe box."
              className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-xs focus:outline-none"
            />
          </div>
        </div>

        {/* Modal Bottom Bar */}
        <div className="no-print px-6 py-4 border-t border-[#DCE2EA] dark:border-[#25324A] flex items-center justify-between bg-slate-50 dark:bg-slate-900/60 rounded-b-2xl">
          <span className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
            Changes to contacts and instructions are saved with your backup.
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                saveEmergencyDetails();
                onClose();
              }}
              className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
            >
              Save Details
            </button>
            <button
              onClick={() => {
                saveEmergencyDetails();
                triggerPrint();
              }}
              className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-semibold bg-[#0B3B66] dark:bg-[#5B9BE0] text-white dark:text-[#08121F] transition shadow-sm flex items-center gap-1.5"
            >
              <Printer className="w-4 h-4" />
              <span>Print Dossier</span>
            </button>
            <button
              onClick={onClose}
              className="min-h-[44px] px-3.5 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
