import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface ClientField {
  id: string;
  fieldKey: string;
  label: string;
  fieldType: string;
}
interface CustomValue {
  field: ClientField;
  value: string | null;
}
interface Client {
  id: string;
  name: string;
  addressLine1?: string;
  addressLine2?: string;
  clientType?: string;
  mobile?: string;
  email?: string;
  customValues: CustomValue[];
}

const SYSTEM_FIELDS: { key: keyof Client; label: string }[] = [
  { key: 'name', label: 'Client Name' },
  { key: 'addressLine1', label: 'Address Line 1' },
  { key: 'addressLine2', label: 'Address Line 2' },
  { key: 'clientType', label: 'Client Type' },
  { key: 'mobile', label: 'Mobile' },
  { key: 'email', label: 'Email' },
];

export default function ClientsPage({ isAdmin }: { isAdmin: boolean }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [fields, setFields] = useState<ClientField[]>([]);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showFieldAdmin, setShowFieldAdmin] = useState(false);

  useEffect(() => {
    load();
    api.get('/clients/fields').then((r) => setFields(r.data.data));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  async function load() {
    const r = await api.get('/clients', { params: { search } });
    setClients(r.data.data);
  }

  function startEdit(c: Client) {
    const flat: Record<string, string> = {
      name: c.name,
      addressLine1: c.addressLine1 || '',
      addressLine2: c.addressLine2 || '',
      clientType: c.clientType || '',
      mobile: c.mobile || '',
      email: c.email || '',
    };
    for (const cv of c.customValues) flat[cv.field.fieldKey] = cv.value || '';
    setForm(flat);
    setEditingId(c.id);
  }

  async function save() {
    if (!form.name) return;
    const customFields: Record<string, string> = {};
    for (const f of fields) if (form[f.fieldKey] !== undefined) customFields[f.fieldKey] = form[f.fieldKey];

    const payload = {
      name: form.name,
      addressLine1: form.addressLine1,
      addressLine2: form.addressLine2,
      clientType: form.clientType,
      mobile: form.mobile,
      email: form.email,
      customFields,
    };

    if (editingId) await api.put(`/clients/${editingId}`, payload);
    else await api.post('/clients', payload);
    setForm({});
    setEditingId(null);
    await load();
  }

  async function remove(id: string) {
    if (!window.confirm('Delete this client?')) return;
    await api.delete(`/clients/${id}`);
    await load();
  }

  async function importExcel(file: File) {
    const fd = new FormData();
    fd.append('file', file);
    await api.post('/clients/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    await load();
  }

  return (
    <div className="h-full overflow-y-auto p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-lg font-semibold">Manage Clients</h1>
        <div className="flex gap-2">
          {isAdmin && (
            <button onClick={() => setShowFieldAdmin(true)} className="text-sm px-3 py-1.5 border rounded-md">
              + Custom Field
            </button>
          )}
          <a href="/api/clients/export" className="text-sm px-3 py-1.5 border rounded-md">
            Export to Excel
          </a>
          <label className="text-sm px-3 py-1.5 border rounded-md cursor-pointer">
            Bulk Import
            <input
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={(e) => e.target.files && importExcel(e.target.files[0])}
            />
          </label>
        </div>
      </div>

      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md mb-4 grid grid-cols-2 gap-2">
        {SYSTEM_FIELDS.map((f) => (
          <input
            key={f.key}
            placeholder={f.label}
            value={form[f.key] || ''}
            onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
            className="border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm"
          />
        ))}
        {fields.map((f) => (
          <input
            key={f.id}
            placeholder={f.label}
            value={form[f.fieldKey] || ''}
            onChange={(e) => setForm({ ...form, [f.fieldKey]: e.target.value })}
            className="border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm"
          />
        ))}
        <button onClick={save} className="col-span-2 bg-brand-600 text-white rounded-md py-1.5 text-sm">
          {editingId ? 'Update Client' : 'Add Client'}
        </button>
        {editingId && (
          <button
            onClick={() => {
              setForm({});
              setEditingId(null);
            }}
            className="col-span-2 text-xs text-gray-500"
          >
            Cancel editing
          </button>
        )}
      </div>

      <input
        placeholder="Search clients…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-3 py-2 mb-3"
      />

      <table className="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="p-2 text-left">Name</th>
            <th className="p-2 text-left">Mobile</th>
            <th className="p-2 text-left">Email</th>
            <th className="p-2 text-left">PAN</th>
            <th className="p-2"></th>
          </tr>
        </thead>
        <tbody>
          {clients.map((c) => (
            <tr key={c.id} className="border-t border-gray-100 dark:border-gray-800">
              <td className="p-2">{c.name}</td>
              <td className="p-2">{c.mobile}</td>
              <td className="p-2">{c.email}</td>
              <td className="p-2">{c.customValues.find((v) => v.field.fieldKey === 'pan')?.value || ''}</td>
              <td className="p-2 flex gap-2">
                <button className="text-xs text-brand-600" onClick={() => startEdit(c)}>
                  Edit
                </button>
                <button className="text-xs text-red-600" onClick={() => remove(c.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showFieldAdmin && (
        <AddFieldModal
          onClose={() => setShowFieldAdmin(false)}
          onAdded={async (field) => {
            setFields((prev) => [...prev, field]);
            setShowFieldAdmin(false);
          }}
        />
      )}
    </div>
  );
}

const FIELD_TYPES = ['Text', 'Email', 'Mobile', 'Date', 'PAN', 'GSTIN', 'PinCode'];

function AddFieldModal({
  onClose,
  onAdded,
}: {
  onClose: () => void;
  onAdded: (field: ClientField) => void;
}) {
  const [label, setLabel] = useState('');
  const [fieldType, setFieldType] = useState('Text');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function slugify(s: string) {
    return s
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  async function submit() {
    if (!label.trim()) return setError('Please enter a field name, e.g. "PAN" or "Date of Birth".');
    setBusy(true);
    setError(null);
    try {
      const fieldKey = slugify(label);
      const res = await api.post('/clients/fields', { fieldKey, label: label.trim(), fieldType });
      onAdded(res.data.data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-sm p-6">
        <h2 className="text-lg font-semibold mb-1">Add a Client Master Field</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          This becomes available on every client's form and can be mapped to a placeholder in Manage Formats →
          Placeholder Mapping.
        </p>
        <input
          autoFocus
          placeholder="Field name, e.g. Date of Birth"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-3 py-2 mb-3"
        />
        <select
          value={fieldType}
          onChange={(e) => setFieldType(e.target.value)}
          className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-3 py-2 mb-3"
        >
          {FIELD_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 rounded-md text-sm hover:bg-gray-100 dark:hover:bg-gray-700">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy}
            className="px-3 py-1.5 rounded-md text-sm bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? 'Adding…' : 'Add Field'}
          </button>
        </div>
      </div>
    </div>
  );
}
