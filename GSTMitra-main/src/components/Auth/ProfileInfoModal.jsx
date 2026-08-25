import React, { useState } from 'react';

const ProfileInfoModal = ({ open, initialName = '', initialPhone = '', onSave, onClose }) => {
  const [displayName, setDisplayName] = useState(initialName);
  const [phoneNumber, setPhoneNumber] = useState(initialPhone);
  const [error, setError] = useState('');

  if (!open) return null;

  const handleSave = () => {
    if (!displayName.trim()) {
      setError('Name is required');
      return;
    }
    if (!/^\d{10}$/.test(phoneNumber.trim())) {
      setError('Valid 10-digit phone number required');
      return;
    }
    setError('');
    onSave({ displayName: displayName.trim(), phoneNumber: phoneNumber.trim() });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60">
      <div className="bg-white rounded-xl p-8 w-full max-w-sm shadow-lg">
        <h2 className="text-xl font-bold mb-4 text-black">Complete Your Profile</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
          <input
            type="text"
            className="w-full px-3 py-2 rounded border border-gray-300 focus:outline-none"
            value={displayName}
            onChange={e => setDisplayName(e.target.value)}
            placeholder="Your Name"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
          <input
            type="tel"
            className="w-full px-3 py-2 rounded border border-gray-300 focus:outline-none"
            value={phoneNumber}
            onChange={e => setPhoneNumber(e.target.value)}
            placeholder="10-digit Phone Number"
            maxLength={10}
          />
        </div>
        {error && <div className="text-red-600 mb-2 text-sm">{error}</div>}
        <div className="flex gap-2 justify-end mt-4">
          <button
            className="px-4 py-2 rounded bg-gray-200 text-gray-700 font-semibold hover:bg-gray-300"
            onClick={onClose}
          >Cancel</button>
          <button
            className="px-4 py-2 rounded bg-black text-white font-bold hover:bg-gray-800"
            onClick={handleSave}
          >Save</button>
        </div>
      </div>
    </div>
  );
};

export default ProfileInfoModal;
