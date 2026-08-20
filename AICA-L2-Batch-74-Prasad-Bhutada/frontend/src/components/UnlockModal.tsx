import { useState } from 'react';
import { api } from '../api/client';

export default function UnlockModal({ onClose, onUnlocked }: { onClose: () => void; onUnlocked: () => void }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.post('/settings/unlock', { password });
      sessionStorage.setItem('templateAdminToken', res.data.data.token);
      onUnlocked();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <form onSubmit={submit} className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-sm p-6">
        <h2 className="text-lg font-semibold mb-1">Manage Formats</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Enter the Template Management password to continue.
        </p>
        <input
          autoFocus
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-3 py-2 mb-3"
          placeholder="Password"
        />
        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose} className="px-3 py-1.5 rounded-md text-sm hover:bg-gray-100 dark:hover:bg-gray-700">
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-3 py-1.5 rounded-md text-sm bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {loading ? 'Checking…' : 'Unlock'}
          </button>
        </div>
      </form>
    </div>
  );
}
