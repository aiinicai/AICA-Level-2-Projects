import { useEffect, useState } from 'react';
import { api } from '../api/client';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    api.get('/settings').then((r) => setSettings(r.data.data));
  }, []);

  async function save() {
    await api.put('/settings', settings);
    alert('Settings saved.');
  }

  async function changePassword() {
    if (!newPassword) return;
    await api.post('/settings/change-password', { newPassword });
    setNewPassword('');
    alert('Password updated.');
  }

  return (
    <div className="h-full overflow-y-auto p-6 max-w-2xl mx-auto">
      <h1 className="text-lg font-semibold mb-4">Application Settings</h1>
      <div className="space-y-3">
        {Object.entries(settings).map(([key, value]) => (
          <div key={key}>
            <label className="text-xs text-gray-500">{key}</label>
            <input
              value={value}
              onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
              className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm"
            />
          </div>
        ))}
      </div>
      <button onClick={save} className="mt-4 px-4 py-2 bg-brand-600 text-white rounded-md text-sm">
        Save Settings
      </button>

      <div className="mt-8 border-t border-gray-200 dark:border-gray-700 pt-4">
        <h2 className="text-sm font-medium mb-2">Change Template Management Password</h2>
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="New password"
          className="border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm mr-2"
        />
        <button onClick={changePassword} className="px-3 py-1.5 border rounded-md text-sm">
          Update Password
        </button>
      </div>
    </div>
  );
}
