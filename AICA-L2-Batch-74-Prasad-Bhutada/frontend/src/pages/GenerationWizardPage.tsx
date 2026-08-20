import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface Template {
  id: string;
  name: string;
  category: { name: string };
}
interface MergedPlaceholder {
  placeholderId: string;
  name: string;
  validationType: string;
  isImage: boolean;
  usedIn: string[];
  mappedClientField: string | null;
}
interface Client {
  id: string;
  name: string;
}

export default function GenerationWizardPage() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [templateSearch, setTemplateSearch] = useState('');
  const [placeholders, setPlaceholders] = useState<MergedPlaceholder[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [images, setImages] = useState<Record<string, File>>({});
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState('');
  const [clientName, setClientName] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generatedFiles, setGeneratedFiles] = useState<
    {
      templateId: string;
      templateName: string;
      docxFileName: string | null;
      pdfFileName: string | null;
      pdfError?: string | null;
    }[]
  >([]);
  const [batchDir, setBatchDir] = useState('');
  const [pdfUnavailable, setPdfUnavailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    api.get('/templates', { params: { search: templateSearch } }).then((r) => setTemplates(r.data.data));
  }, [templateSearch]);

  useEffect(() => {
    api.get('/clients').then((r) => setClients(r.data.data));
  }, []);

  function toggleTemplate(id: string) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function goToStep2() {
    if (!selectedIds.length) return;
    const previousValues = values;
    const r = await api.post('/generation/merge-placeholders', { templateIds: selectedIds });
    const merged: MergedPlaceholder[] = r.data.data;

    // Preserve previously entered values; drop values for placeholders no longer present.
    const nextValues: Record<string, string> = {};
    for (const p of merged) if (previousValues[p.name] !== undefined) nextValues[p.name] = previousValues[p.name];
    setValues(nextValues);
    setPlaceholders(merged);
    setStep(2);
  }

  async function autoFill() {
    if (!clientId) return;
    const r = await api.post('/generation/autofill', { clientId, templateIds: selectedIds });
    setValues((prev) => ({ ...prev, ...r.data.data }));
    const c = clients.find((x) => x.id === clientId);
    if (c) setClientName(c.name);
  }

  async function goToPreview() {
    setBusy(true);
    setErrors({});
    try {
      const r = await api.post('/generation/validate', { templateIds: selectedIds, values });
      const errs = r.data.data as { placeholder: string; message: string }[];
      const missingImages = placeholders.filter((p) => p.isImage && !images[p.name]).map((p) => p.name);
      if (errs.length || missingImages.length) {
        const map: Record<string, string> = {};
        errs.forEach((e) => (map[e.placeholder] = e.message));
        missingImages.forEach((name) => (map[name] = 'Please upload an image.'));
        setErrors(map);
        return;
      }

      const form = new FormData();
      form.append('clientId', clientId);
      form.append('clientName', clientName || 'Client');
      form.append('templateIds', JSON.stringify(selectedIds));
      form.append('values', JSON.stringify(values));
      form.append('outputFormats', JSON.stringify(['docx', 'pdf']));
      Object.entries(images).forEach(([name, file]) => form.append(name, file));

      const res = await api.post('/generation/generate', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const files = res.data.data.files as typeof generatedFiles;
      setGeneratedFiles(files);
      setBatchDir(res.data.data.batchDir);
      setPdfUnavailable(!!res.data.data.pdfUnavailable);
      setStep(3);
      if (files[0]?.docxFileName) {
        loadPreview(res.data.data.batchDir, files[0].docxFileName);
      }
    } catch (e: any) {
      setErrors({ _general: e.message });
    } finally {
      setBusy(false);
    }
  }

  async function loadPreview(dir: string, fileName: string) {
    setPreviewFile(fileName);
    setPreviewLoading(true);
    try {
      const r = await api.get('/generation/preview', { params: { dir, file: fileName } });
      setPreviewHtml(r.data.data.html);
    } catch {
      setPreviewHtml('<p style="color:#999">Preview is not available for this file.</p>');
    } finally {
      setPreviewLoading(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6 max-w-5xl mx-auto">
      <Steps current={step} />

      {step === 1 && (
        <div className="mt-6">
          <input
            placeholder="Search templates by name or keyword…"
            value={templateSearch}
            onChange={(e) => setTemplateSearch(e.target.value)}
            className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-3 py-2 mb-4"
          />
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="p-2 w-10"></th>
                  <th className="p-2 text-left">Template</th>
                  <th className="p-2 text-left">Category</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => toggleTemplate(t.id)}
                    className="cursor-pointer border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <td className="p-2 text-center">
                      <input type="checkbox" checked={selectedIds.includes(t.id)} readOnly />
                    </td>
                    <td className="p-2">{t.name}</td>
                    <td className="p-2 text-gray-500">{t.category?.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              disabled={!selectedIds.length}
              onClick={goToStep2}
              className="px-4 py-2 rounded-md bg-brand-600 text-white disabled:opacity-40"
            >
              Next ({selectedIds.length} selected)
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="mt-6">
          <div className="flex gap-2 items-end mb-4 bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
            <div className="flex-1">
              <label className="text-xs text-gray-500">Import from Client Master</label>
              <select
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-2 py-1.5"
              >
                <option value="">Select client…</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <button onClick={autoFill} className="px-3 py-1.5 rounded-md border border-brand-500 text-brand-600 text-sm">
              Auto Fill
            </button>
          </div>

          <label className="text-xs text-gray-500">Client Name (used in file naming)</label>
          <input
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-3 py-2 mb-4"
          />

          <div className="space-y-4">
            {placeholders.map((p) => (
              <div key={p.placeholderId}>
                <label className="text-sm font-medium">{p.name}</label>
                {p.isImage ? (
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/gif"
                    onChange={(e) => e.target.files && setImages((prev) => ({ ...prev, [p.name]: e.target.files![0] }))}
                    className="block text-sm mt-1"
                  />
                ) : (
                  <input
                    value={values[p.name] || ''}
                    onChange={(e) => setValues((prev) => ({ ...prev, [p.name]: e.target.value }))}
                    className="w-full border border-gray-300 dark:border-gray-600 bg-transparent rounded-md px-3 py-2 mt-1"
                  />
                )}
                {errors[p.name] && <p className="text-xs text-red-600 mt-1">{errors[p.name]}</p>}
                <p className="text-xs italic text-gray-400 mt-1">Used in: {p.usedIn.join(', ')}</p>
              </div>
            ))}
          </div>

          {errors._general && <p className="text-sm text-red-600 mt-4">{errors._general}</p>}

          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep(1)} className="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600">
              Back
            </button>
            <button
              disabled={busy}
              onClick={goToPreview}
              className="px-4 py-2 rounded-md bg-brand-600 text-white disabled:opacity-40"
            >
              {busy ? 'Generating…' : 'Preview & Generate'}
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold mb-3">Preview & Download</h2>

          {pdfUnavailable && (
            <div className="mb-3 text-sm bg-amber-50 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-200 rounded-md p-3">
              <strong>PDF isn't available yet on this server</strong> — Word documents below are unaffected and
              ready to download. To enable PDF downloads, ask your administrator to install LibreOffice (see
              docs/INSTALLATION.md, "Optional: PDF generation").
            </div>
          )}

          <div className="grid grid-cols-[220px_1fr_220px] gap-0 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden h-[560px]">
            {/* LEFT: selected documents */}
            <div className="border-r border-gray-200 dark:border-gray-700 overflow-y-auto bg-gray-50 dark:bg-gray-800">
              {generatedFiles.map((f) => (
                <div
                  key={f.templateId}
                  onClick={() => f.docxFileName && loadPreview(batchDir, f.docxFileName)}
                  className={`px-3 py-2.5 cursor-pointer border-b border-gray-100 dark:border-gray-700 text-sm ${
                    previewFile === f.docxFileName
                      ? 'bg-brand-50 dark:bg-gray-700 font-medium'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  {f.templateName}
                </div>
              ))}
            </div>

            {/* CENTRE: Word-like preview */}
            <div className="overflow-y-auto bg-gray-100 dark:bg-gray-900 p-4">
              {previewLoading ? (
                <p className="text-sm text-gray-400 text-center mt-10">Loading preview…</p>
              ) : (
                <div className="docx-preview" dangerouslySetInnerHTML={{ __html: previewHtml }} />
              )}
            </div>

            {/* RIGHT: per-document actions */}
            <div className="border-l border-gray-200 dark:border-gray-700 overflow-y-auto p-3">
              <a
                href={`/api/generation/download?dir=${encodeURIComponent(batchDir)}&all=true&zipName=Documents.zip`}
                className="block text-center text-xs px-2 py-2 mb-1.5 rounded-md bg-brand-600 text-white hover:bg-brand-700"
              >
                Download All (Word)
              </a>
              {!pdfUnavailable && (
                <a
                  href={`/api/generation/download?dir=${encodeURIComponent(batchDir)}&all=true&zipName=Documents.zip`}
                  className="block text-center text-xs px-2 py-2 mb-3 rounded-md border border-brand-500 text-brand-600"
                >
                  Download All (ZIP incl. PDF)
                </a>
              )}

              <div className="space-y-2 mt-3">
                {generatedFiles.map((f) => (
                  <div key={f.templateId} className="border border-gray-200 dark:border-gray-700 rounded-md p-2">
                    <p className="text-xs font-medium mb-1.5 truncate" title={f.templateName}>
                      {f.templateName}
                    </p>
                    <div className="flex gap-1.5">
                      {f.docxFileName && (
                        <a
                          className="flex-1 text-center text-xs px-2 py-1 border rounded-md"
                          href={`/api/generation/download?dir=${encodeURIComponent(batchDir)}&file=${encodeURIComponent(f.docxFileName)}`}
                        >
                          Word
                        </a>
                      )}
                      {f.pdfFileName ? (
                        <a
                          className="flex-1 text-center text-xs px-2 py-1 border rounded-md"
                          href={`/api/generation/download?dir=${encodeURIComponent(batchDir)}&file=${encodeURIComponent(f.pdfFileName)}`}
                        >
                          PDF
                        </a>
                      ) : f.pdfError ? (
                        <span className="flex-1 text-center text-xs text-gray-400" title={f.pdfError}>
                          No PDF
                        </span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={() => {
                setStep(1);
                setSelectedIds([]);
                setValues({});
                setImages({});
                setGeneratedFiles([]);
                setPdfUnavailable(false);
                setPreviewFile(null);
                setPreviewHtml('');
              }}
              className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm"
            >
              Start New Batch
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Steps({ current }: { current: number }) {
  const labels = ['Select Templates', 'Fill Placeholders', 'Preview & Download'];
  return (
    <div className="flex gap-4">
      {labels.map((l, i) => (
        <div key={l} className={`text-sm ${current === i + 1 ? 'text-brand-600 font-semibold' : 'text-gray-400'}`}>
          {i + 1}. {l}
        </div>
      ))}
    </div>
  );
}
