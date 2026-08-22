import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface PlaceholderRow {
  id: string;
  name: string;
  isImage: boolean;
  mappedClientField: string | null;
  usedInTemplates: string[];
}
interface AvailableField {
  fieldKey: string;
  label: string;
}

export default function MappingPage({ isAdmin, onNeedUnlock }: { isAdmin: boolean; onNeedUnlock: () => void }) {
  const [placeholders, setPlaceholders] = useState<PlaceholderRow[]>([]);
  const [availableFields, setAvailableFields] = useState<AvailableField[]>([]);

  useEffect(() => {
    if (!isAdmin) return;
    load();
  }, [isAdmin]);

  async function load() {
    const [phRes, fieldsRes] = await Promise.all([
      api.get('/placeholder-mappings'),
      api.get('/placeholder-mappings/available-fields'),
    ]);
    setPlaceholders(phRes.data.data);
    setAvailableFields(fieldsRes.data.data);
  }

  async function setMapping(placeholderId: string, clientFieldKey: string) {
    if (!clientFieldKey) {
      await api.delete(`/placeholder-mappings/${placeholderId}`);
    } else {
      await api.put(`/placeholder-mappings/${placeholderId}`, { clientFieldKey });
    }
    await load();
  }

  if (!isAdmin) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-3">Placeholder Mapping is part of Template Management and is password protected.</p>
          <button onClick={onNeedUnlock} className="px-4 py-2 bg-brand-600 text-white rounded-md">
            Enter Password
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6 max-w-3xl mx-auto">
      <h1 className="text-lg font-semibold mb-1">Placeholder Mapping</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Map each template placeholder to a Client Master field so <strong>Auto Fill</strong> can populate it
        automatically during document generation. Placeholders without a mapping still work — staff just type
        them in by hand.
      </p>

      {placeholders.length === 0 ? (
        <p className="text-sm text-gray-400">
          No placeholders found yet — import a template first (Manage Formats → Import Template).
        </p>
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="p-2 text-left">Placeholder</th>
                <th className="p-2 text-left">Used in</th>
                <th className="p-2 text-left">Maps to Client Master field</th>
              </tr>
            </thead>
            <tbody>
              {placeholders.map((p) => (
                <tr key={p.id} className="border-t border-gray-100 dark:border-gray-800">
                  <td className="p-2 font-medium">
                    {p.name}
                    {p.isImage && <span className="ml-2 text-xs text-brand-600">image</span>}
                  </td>
                  <td className="p-2 text-xs italic text-gray-500">{p.usedInTemplates.join(', ')}</td>
                  <td className="p-2">
                    {p.isImage ? (
                      <span className="text-xs text-gray-400">Not applicable (uploaded per document)</span>
                    ) : (
                      <select
                        value={p.mappedClientField || ''}
                        onChange={(e) => setMapping(p.id, e.target.value)}
                        className="border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1 text-sm"
                      >
                        <option value="">— Not mapped (manual entry) —</option>
                        {availableFields.map((f) => (
                          <option key={f.fieldKey} value={f.fieldKey}>
                            {f.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
