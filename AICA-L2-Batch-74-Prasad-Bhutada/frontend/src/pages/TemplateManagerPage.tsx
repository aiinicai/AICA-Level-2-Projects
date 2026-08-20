import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

interface Template {
  id: string;
  name: string;
  category: { id: string; name: string };
  keywords: string | null;
  status: string;
}
interface PlaceholderInfo {
  id: string;
  name: string;
  validationType: string;
  isImage: boolean;
  placeholder: { name: string; isImage: boolean };
}

export default function TemplateManagerPage({
  isAdmin,
  onNeedUnlock,
}: {
  isAdmin: boolean;
  onNeedUnlock: () => void;
}) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<{ id: string; name: string }[]>([]);
  const [search, setSearch] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [selected, setSelected] = useState<Template | null>(null);
  const [previewHtml, setPreviewHtml] = useState('');
  const [placeholders, setPlaceholders] = useState<PlaceholderInfo[]>([]);
  const [showImport, setShowImport] = useState(false);

  useEffect(() => {
    if (!isAdmin) return;
    api.get('/categories').then((r) => setCategories(r.data.data));
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, search, categoryId]);

  async function load() {
    const r = await api.get('/templates', { params: { search, categoryId } });
    setTemplates(r.data.data);
  }

  async function openTemplate(t: Template) {
    setSelected(t);
    const [previewRes, detailRes] = await Promise.all([
      api.get(`/templates/${t.id}/preview`),
      api.get(`/templates/${t.id}`),
    ]);
    setPreviewHtml(previewRes.data.data.html);
    setPlaceholders(detailRes.data.data.placeholders);
  }

  async function handleDelete(t: Template) {
    const dep = await api.get(`/templates/${t.id}/dependencies`);
    const proceed = dep.data.data.hasDependencies
      ? window.confirm(`${dep.data.data.message}\n\nMove to Recycle Bin anyway?`)
      : window.confirm(`Move "${t.name}" to Recycle Bin?`);
    if (!proceed) return;
    await api.delete(`/templates/${t.id}`);
    await load();
    if (selected?.id === t.id) setSelected(null);
  }

  async function handleRename(t: Template) {
    const name = window.prompt('New template name', t.name);
    if (!name) return;
    await api.patch(`/templates/${t.id}/rename`, { name });
    await load();
  }

  if (!isAdmin) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-3">Template Management is password protected.</p>
          <button onClick={onNeedUnlock} className="px-4 py-2 bg-brand-600 text-white rounded-md">
            Enter Password
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full grid grid-cols-[300px_1fr_300px] gap-0">
      {/* LEFT PANEL */}
      <div className="border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
        <div className="p-3 space-y-2 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setShowImport(true)}
            className="w-full bg-brand-600 text-white rounded-md py-2 text-sm font-medium hover:bg-brand-700"
          >
            + Import Template
          </button>
          <Link
            to="/mapping"
            className="block text-center text-xs text-brand-600 dark:text-brand-300 hover:underline"
          >
            Placeholder Mapping →
          </Link>
          <input
            placeholder="Search by name or keyword…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm"
          />
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 overflow-y-auto">
          {templates
            .slice()
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((t) => (
              <div
                key={t.id}
                onClick={() => openTemplate(t)}
                className={`px-3 py-2 cursor-pointer border-b border-gray-100 dark:border-gray-800 text-sm ${
                  selected?.id === t.id ? 'bg-brand-50 dark:bg-gray-700' : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-gray-500">{t.category?.name}</div>
              </div>
            ))}
          {templates.length === 0 && <p className="text-sm text-gray-400 p-3">No templates found.</p>}
        </div>
      </div>

      {/* CENTRE PANEL */}
      <div className="overflow-y-auto bg-gray-100 dark:bg-gray-900 p-6">
        {selected ? (
          <>
            <div className="flex gap-2 mb-4 justify-center flex-wrap">
              <ToolbarBtn onClick={() => window.open(`/api/templates/${selected.id}/download`, '_blank')}>
                Download
              </ToolbarBtn>
              <ToolbarBtn onClick={() => handleRename(selected)}>Rename</ToolbarBtn>
              <ToolbarBtn onClick={() => handleDelete(selected)} danger>
                Delete
              </ToolbarBtn>
            </div>
            <div className="docx-preview" dangerouslySetInnerHTML={{ __html: previewHtml }} />
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400 text-sm">
            Select a template to preview
          </div>
        )}
      </div>

      {/* RIGHT PANEL */}
      <div className="border-l border-gray-200 dark:border-gray-700 p-3 overflow-y-auto">
        <h3 className="font-medium text-sm mb-2">Detected Placeholders</h3>
        {selected ? (
          placeholders.length ? (
            <ul className="space-y-1">
              {placeholders.map((p) => (
                <li
                  key={p.id}
                  className="text-sm px-2 py-1.5 rounded bg-gray-50 dark:bg-gray-800 flex items-center justify-between"
                >
                  <span>{p.placeholder.name}</span>
                  {p.placeholder.isImage && <span className="text-xs text-brand-600">image</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No placeholders detected.</p>
          )
        ) : (
          <p className="text-sm text-gray-400">Select a template to view its placeholders.</p>
        )}
      </div>

      {showImport && (
        <ImportModal
          categories={categories}
          onClose={() => setShowImport(false)}
          onImported={async () => {
            setShowImport(false);
            await load();
          }}
        />
      )}
    </div>
  );
}

function ToolbarBtn({
  children,
  onClick,
  danger,
}: {
  children: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-3 py-1.5 rounded-md border ${
        danger
          ? 'border-red-300 text-red-600 hover:bg-red-50'
          : 'border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
      }`}
    >
      {children}
    </button>
  );
}

function ImportModal({
  categories,
  onClose,
  onImported,
}: {
  categories: { id: string; name: string }[];
  onClose: () => void;
  onImported: () => void;
}) {
  const [files, setFiles] = useState<FileList | null>(null);
  const [categoryId, setCategoryId] = useState(categories[0]?.id || '');
  const [keywords, setKeywords] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!files || files.length === 0) return setError('Please choose one or more .docx files.');
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      Array.from(files).forEach((f) => form.append('files', f));
      form.append('categoryId', categoryId);
      form.append('keywords', keywords);
      await api.post('/templates/import', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      onImported();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold mb-4">Import Template(s)</h2>
        <input
          type="file"
          multiple
          accept=".docx"
          onChange={(e) => setFiles(e.target.files)}
          className="w-full text-sm mb-3"
        />
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm mb-3"
        >
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input
          placeholder="Keywords (comma separated)"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5 text-sm mb-3"
        />
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
            {busy ? 'Importing…' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  );
}
