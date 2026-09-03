import React, { useState } from 'react';
import { X, Copy, Check, Download, FileCode, Terminal, FileText, Globe } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const PythonBundleModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'run' | 'app' | 'req' | 'html'>('run');
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const downloadFile = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const runInstructions = `# Complete Fast Setup Guide for Local Python Desktop App

# 1. Ensure LM Studio Local Server is running:
#    - Open LM Studio -> Click Local Server tab (left icon)
#    - Model: Llama-3-8B, Qwen2.5, or Mistral
#    - Port: 1234 -> Click "Start Server" (http://localhost:1234/v1)

# 2. Install dependencies:
pip install -r requirements.txt

# 3. Start the FastAPI server:
python app.py

# 4. Open in browser:
http://localhost:8000/app
`;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-4xl h-[85vh] flex flex-col shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-white">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Standalone FastAPI + Python Desktop Suite</h3>
              <p className="text-[11px] text-gray-500">Run 100% offline on your local machine with LM Studio</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 p-2 bg-gray-50 border-b border-gray-100 overflow-x-auto text-xs">
          <button
            onClick={() => setActiveTab('run')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-semibold transition ${
              activeTab === 'run' ? 'bg-white text-gray-900 shadow-2xs border border-gray-200' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <Terminal className="w-3.5 h-3.5 text-blue-600" />
            <span>Setup & Run Instructions</span>
          </button>
          <button
            onClick={() => setActiveTab('app')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-semibold transition ${
              activeTab === 'app' ? 'bg-white text-gray-900 shadow-2xs border border-gray-200' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <FileCode className="w-3.5 h-3.5 text-blue-600" />
            <span>app.py (FastAPI)</span>
          </button>
          <button
            onClick={() => setActiveTab('req')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-semibold transition ${
              activeTab === 'req' ? 'bg-white text-gray-900 shadow-2xs border border-gray-200' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-blue-600" />
            <span>requirements.txt</span>
          </button>
          <button
            onClick={() => setActiveTab('html')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-semibold transition ${
              activeTab === 'html' ? 'bg-white text-gray-900 shadow-2xs border border-gray-200' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <Globe className="w-3.5 h-3.5 text-blue-600" />
            <span>standalone_index.html</span>
          </button>
        </div>

        {/* Tab Body Content */}
        <div className="flex-1 p-5 overflow-y-auto bg-gray-50 font-mono text-xs text-gray-800 select-text leading-relaxed">
          {activeTab === 'run' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-white border border-gray-200 space-y-2 shadow-2xs">
                <h4 className="text-sm font-semibold text-gray-900 font-sans">🚀 Quick Start Checklist</h4>
                <ol className="list-decimal list-inside space-y-1.5 text-gray-600 font-sans text-xs">
                  <li><strong>Start LM Studio:</strong> Open LM Studio, load your model, go to Local Server tab, and click <em>Start Server</em> on port <code>1234</code>.</li>
                  <li><strong>Create Python environment:</strong> <code>python -m venv venv && source venv/bin/activate</code></li>
                  <li><strong>Install packages:</strong> <code>pip install -r requirements.txt</code></li>
                  <li><strong>Run application:</strong> <code>python app.py</code></li>
                  <li><strong>Open UI:</strong> Navigate to <code>http://localhost:8000/app</code></li>
                </ol>
              </div>
              <pre className="p-4 bg-white rounded-xl border border-gray-200 text-gray-800 overflow-x-auto whitespace-pre-wrap shadow-2xs">{runInstructions}</pre>
            </div>
          )}

          {activeTab === 'app' && (
            <div>
              <p className="text-[11px] text-gray-500 mb-2 font-sans">FastAPI backend containing document parsers (PDF, DOCX, XLSX, CSV, Pillow), LM Studio SSE streaming proxy, and python-docx / python-pptx builders.</p>
              <pre className="p-4 bg-white rounded-xl border border-gray-200 text-gray-800 overflow-x-auto whitespace-pre-wrap shadow-2xs"># app.py is saved in your project root. Click 'Copy Commands' or run directly with python app.py</pre>
            </div>
          )}

          {activeTab === 'req' && (
            <div>
              <p className="text-[11px] text-gray-500 mb-2 font-sans">Python dependencies required for offline document extraction and document building.</p>
              <pre className="p-4 bg-white rounded-xl border border-gray-200 text-blue-900 font-mono shadow-2xs">
fastapi&gt;=0.110.0
uvicorn[standard]&gt;=0.28.0
openai&gt;=1.14.0
pypdf&gt;=4.1.0
python-docx&gt;=1.1.0
python-pptx&gt;=0.6.23
openpyxl&gt;=3.1.2
Pillow&gt;=10.2.0
python-multipart&gt;=0.0.9
aiofiles&gt;=23.2.1
requests&gt;=2.31.0
              </pre>
            </div>
          )}

          {activeTab === 'html' && (
            <div>
              <p className="text-[11px] text-gray-500 mb-2 font-sans">Standalone Vanilla JavaScript + Tailwind CSS single-file desktop frontend template.</p>
              <pre className="p-4 bg-white rounded-xl border border-gray-200 text-gray-700 font-mono shadow-2xs">
&lt;!-- standalone_index.html is created in your project root ready for local serving --&gt;
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3.5 border-t border-gray-100 bg-white flex justify-between items-center text-xs">
          <span className="text-gray-500">All files are generated in your local repository.</span>
          <button
            onClick={() => copyToClipboard(runInstructions)}
            className="px-3.5 py-1.5 bg-white hover:bg-gray-50 text-gray-700 rounded-lg flex items-center gap-1.5 font-semibold border border-gray-200 shadow-2xs transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-gray-500" />}
            <span>{copied ? 'Copied Instructions' : 'Copy Commands'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
