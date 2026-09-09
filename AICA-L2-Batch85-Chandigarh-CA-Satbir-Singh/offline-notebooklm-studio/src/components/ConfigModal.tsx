import React from 'react';
import { LmStudioConfig } from '../types';
import { Settings2, X, Check, Server, RefreshCw } from 'lucide-react';

interface Props {
  config: LmStudioConfig;
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: LmStudioConfig) => void;
  onTestConnection: () => Promise<void>;
}

export const ConfigModal: React.FC<Props> = ({ config, isOpen, onClose, onSave, onTestConnection }) => {
  const [url, setUrl] = React.useState(config.baseUrl);
  const [temp, setTemp] = React.useState(config.temperature);
  const [testing, setTesting] = React.useState(false);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTesting(true);
    await onTestConnection();
    setTesting(false);
  };

  const handleSave = () => {
    onSave({
      ...config,
      baseUrl: url.trim(),
      temperature: temp,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white border border-gray-200 rounded-2xl w-full max-w-md p-5 shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Settings2 className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-gray-900">LM Studio & Model Setup</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1 rounded-lg hover:bg-gray-100 transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3.5 text-xs">
          <div>
            <label className="block font-medium text-gray-700 mb-1">LM Studio Endpoint URL</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="http://localhost:1234/v1"
                className="flex-1 bg-white border border-gray-200 focus:border-blue-500 rounded-lg px-3 py-2 text-gray-900 focus:outline-none font-mono text-xs shadow-2xs"
              />
              <button
                type="button"
                onClick={handleTest}
                disabled={testing}
                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg border border-gray-200 flex items-center gap-1 shrink-0 font-medium transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
                <span>Test</span>
              </button>
            </div>
            <p className="text-[10px] text-gray-400 mt-1">
              Standard local endpoint is <code className="text-blue-600 bg-blue-50 px-1 py-0.5 rounded">http://localhost:1234/v1</code>
            </p>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="font-medium text-gray-700">Temperature (Creativity)</label>
              <span className="font-mono text-gray-600 font-semibold">{temp.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={temp}
              onChange={(e) => setTemp(parseFloat(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
              <span>0.0 (Deterministic / Exact)</span>
              <span>1.0 (Creative / Analytical)</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 space-y-1.5 text-xs text-gray-600">
            <div className="flex items-center gap-1.5 text-gray-900 font-semibold">
              <Server className="w-3.5 h-3.5 text-blue-600" />
              <span>Offline LM Studio Quick Guide:</span>
            </div>
            <p>1. Open LM Studio on your computer.</p>
            <p>2. Load your desired model (Llama-3, Mistral, Qwen, DeepSeek).</p>
            <p>3. Go to the "Local Server" tab and toggle on port <strong>1234</strong>.</p>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-3 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 text-xs font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
};
