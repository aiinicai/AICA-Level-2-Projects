import React, { useState, useEffect } from 'react';
import { Client } from '../types';
import { X, Building2, AlertCircle } from 'lucide-react';

interface AddClientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (client: Client) => Promise<void>;
  /** Pre-fill legal name / GSTIN, e.g. from a just-extracted notice. */
  prefill?: { legalName?: string; gstin?: string } | null;
}

export const AddClientModal: React.FC<AddClientModalProps> = ({ isOpen, onClose, onSave, prefill }) => {
  const [legalName, setLegalName] = useState('');
  const [tradeName, setTradeName] = useState('');
  const [gstin, setGstin] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setLegalName(prefill?.legalName || '');
      setGstin((prefill?.gstin || '').toUpperCase());
      setTradeName('');
      setEmail('');
      setPhone('');
      setAddress('');
      setErrorMsg(null);
    }
  }, [isOpen, prefill?.legalName, prefill?.gstin]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!legalName.trim() || !gstin.trim()) {
      setErrorMsg('Legal Name and GSTIN are mandatory.');
      return;
    }

    const cleanGstin = gstin.trim().toUpperCase();
    if (cleanGstin.length !== 15) {
      setErrorMsg('GSTIN must be exactly 15 alphanumeric characters.');
      return;
    }

    setIsSaving(true);
    setErrorMsg(null);
    try {
      const newClient: Client = {
        id: 'client_' + Date.now(),
        legalName: legalName.trim(),
        tradeName: (tradeName.trim() || legalName.trim()).slice(0, 30),
        gstin: cleanGstin,
        email: email.trim() || 'taxpayer@client.in',
        phone: phone.trim() || '+91 98000 00000',
        pan: cleanGstin.slice(2, 12),
        address: address.trim() || 'Principal Place of Business',
      };
      await onSave(newClient);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Error saving client');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#4338CA]" />
            <h2 className="text-sm font-bold text-gray-900">Add New GST Client</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-200 text-gray-400 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-3.5 text-xs">
          <div>
            <label className="block font-bold text-gray-700 mb-1">Taxpayer Legal Name *</label>
            <input
              type="text"
              required
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
              placeholder="e.g. ABC Enterprises Private Limited"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-gray-700 mb-1">Trade / Brand Name</label>
              <input
                type="text"
                value={tradeName}
                onChange={(e) => setTradeName(e.target.value)}
                placeholder="e.g. ABC Enterprises"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
              />
            </div>
            <div>
              <label className="block font-bold text-gray-700 mb-1">15-Digit GSTIN *</label>
              <input
                type="text"
                required
                maxLength={15}
                value={gstin}
                onChange={(e) => setGstin(e.target.value.toUpperCase())}
                placeholder="e.g. 27AAACH0000A1Z5"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA] font-mono uppercase"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-gray-700 mb-1">Client Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="finance@company.in"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
              />
            </div>
            <div>
              <label className="block font-bold text-gray-700 mb-1">Mobile / Phone</label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
              />
            </div>
          </div>

          <div>
            <label className="block font-bold text-gray-700 mb-1">Registered Business Address</label>
            <textarea
              rows={2}
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Plot No., Industrial Area, City, State, PIN"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
            />
          </div>

          {errorMsg && (
            <div className="p-2.5 rounded-lg bg-red-50 text-red-700 flex items-center gap-2 font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="pt-3 border-t border-gray-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-bold cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-5 py-2 bg-[#4338CA] text-white font-bold rounded-lg hover:bg-[#3730A3] transition-all cursor-pointer shadow-xs"
            >
              {isSaving ? 'Saving...' : 'Save Client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
