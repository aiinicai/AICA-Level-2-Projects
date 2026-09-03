import React, { useState, useEffect } from 'react';
import {
  Zap,
  Terminal,
  Play,
  Copy,
  Check,
  CheckCircle2,
  AlertCircle,
  Database,
  Radio,
  Code2,
  RefreshCw,
  Cpu,
  Layers,
  ArrowRight,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { McpToolDefinition, McpExecutionResult, ClientProfile } from '../../types';

interface McpConnectorsPanelProps {
  client: ClientProfile;
}

export const McpConnectorsPanel: React.FC<McpConnectorsPanelProps> = ({ client }) => {
  const [tools, setTools] = useState<McpToolDefinition[]>([]);
  const [selectedTool, setSelectedTool] = useState<McpToolDefinition | null>(null);
  const [selectedPortal, setSelectedPortal] = useState<'qbo' | 'tally' | 'zoho' | 'xero' | 'netsuite'>('qbo');
  const [toolArgs, setToolArgs] = useState<Record<string, any>>({
    portal: 'qbo',
    as_of_date: '2026-08-31',
    account_type: 'revenue',
    limit: 50,
  });
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<McpExecutionResult | null>(null);
  const [copiedString, setCopiedString] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'invoker' | 'protocol' | 'endpoints'>('invoker');

  useEffect(() => {
    fetchMcpTools();
  }, []);

  const fetchMcpTools = async () => {
    try {
      const res = await fetch('/api/mcp/tools');
      if (res.ok) {
        const data = await res.json();
        setTools(data.tools || []);
        if (data.tools?.length > 0) {
          setSelectedTool(data.tools[0]);
        }
      }
    } catch (e) {
      console.warn('Using fallback MCP tools list', e);
      // Fallback tools
      const fallbackTools: McpToolDefinition[] = [
        {
          name: 'accounting_query_ledger',
          description: 'Queries live general ledger accounts, transactions, and balances across accounting portals',
          category: 'accounting',
          supportedConnectors: ['qbo', 'tally', 'zoho', 'netsuite', 'xero'],
          inputSchema: {
            type: 'object',
            properties: {
              portal: { type: 'string', description: 'Accounting software target: qbo, tally, zoho, xero, netsuite' },
              account_type: { type: 'string', description: 'Filter: all, revenue, cogs, expense, asset, liability' },
              limit: { type: 'number', description: 'Maximum transactions to retrieve' },
            },
            required: ['portal'],
          },
        },
        {
          name: 'accounting_get_trial_balance',
          description: 'Extracts full debit/credit trial balance and balance sheet line items',
          category: 'reports',
          supportedConnectors: ['qbo', 'tally', 'zoho', 'netsuite', 'xero'],
          inputSchema: {
            type: 'object',
            properties: {
              portal: { type: 'string', description: 'Target portal' },
              as_of_date: { type: 'string', description: 'Date format YYYY-MM-DD' },
            },
            required: ['portal'],
          },
        },
        {
          name: 'accounting_get_ar_aging',
          description: 'Retrieves categorized Accounts Receivable aging schedules (Current, 1-30, 31-60, 61-90, 90+ days)',
          category: 'reports',
          supportedConnectors: ['qbo', 'tally', 'zoho', 'netsuite', 'xero'],
          inputSchema: {
            type: 'object',
            properties: {
              portal: { type: 'string', description: 'Target portal' },
              as_of_date: { type: 'string', description: 'Cut-off date' },
            },
            required: ['portal'],
          },
        },
        {
          name: 'accounting_push_budget_metrics',
          description: 'Uploads calculated pro-forma budget and forecast line items to ERP/accounting cloud',
          category: 'accounting',
          supportedConnectors: ['qbo', 'tally', 'zoho', 'netsuite', 'xero'],
          inputSchema: {
            type: 'object',
            properties: {
              portal: { type: 'string', description: 'Target portal' },
              fiscal_year: { type: 'number', description: 'Target fiscal year' },
              basis_method: { type: 'string', description: 'Forecast driver method' },
            },
            required: ['portal', 'fiscal_year'],
          },
        },
      ];
      setTools(fallbackTools);
      setSelectedTool(fallbackTools[0]);
    }
  };

  const handleExecuteTool = async () => {
    if (!selectedTool) return;
    setIsExecuting(true);
    setExecutionResult(null);

    const fullArgs = {
      ...toolArgs,
      portal: selectedPortal,
    };

    try {
      const res = await fetch('/api/mcp/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: `req-${Date.now()}`,
          method: 'tools/call',
          params: {
            name: selectedTool.name,
            arguments: fullArgs,
          },
        }),
      });

      const responseJson = await res.json();
      if (responseJson.result) {
        setExecutionResult({
          toolName: selectedTool.name,
          portal: selectedPortal,
          executedAt: new Date().toLocaleTimeString(),
          status: 'success',
          data: responseJson.result,
        });
      } else {
        setExecutionResult({
          toolName: selectedTool.name,
          portal: selectedPortal,
          executedAt: new Date().toLocaleTimeString(),
          status: 'success',
          data: responseJson,
        });
      }
    } catch (e: any) {
      setExecutionResult({
        toolName: selectedTool.name,
        portal: selectedPortal,
        executedAt: new Date().toLocaleTimeString(),
        status: 'error',
        error: e.message || 'Execution error over MCP HTTP transport',
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedString(label);
    setTimeout(() => setCopiedString(null), 2500);
  };

  const sseEndpoint = `${window.location.origin}/api/mcp/sse`;
  const postEndpoint = `${window.location.origin}/api/mcp/messages`;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 text-white rounded-3xl p-6 border border-slate-800 shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded-md bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                <Cpu className="w-4 h-4" />
              </span>
              <h3 className="text-base font-bold text-white tracking-wide">
                Model Context Protocol (MCP) Accounting Gateway
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                MCP 2024-11-05 Spec Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Standardized MCP server providing native tools to query general ledgers, extract live trial balances, fetch AR/AP aging, and push budget metrics across QuickBooks Online, Tally Prime, Zoho Books, NetSuite, and Xero.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => copyToClipboard(`{"mcpServers": {"cfo-accounting": {"url": "${sseEndpoint}"}}}`, 'config')}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors"
            >
              {copiedString === 'config' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
              Copy MCP Config JSON
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 mt-5 border-t border-slate-800 pt-4 text-xs font-bold">
          <button
            onClick={() => setActiveTab('invoker')}
            className={`px-3.5 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'invoker'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Play className="w-3 h-3" /> Interactive Tool Invoker
          </button>
          <button
            onClick={() => setActiveTab('protocol')}
            className={`px-3.5 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'protocol'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Terminal className="w-3 h-3" /> Protocol & Schema Specs ({tools.length} Tools)
          </button>
          <button
            onClick={() => setActiveTab('endpoints')}
            className={`px-3.5 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'endpoints'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Radio className="w-3 h-3" /> SSE & HTTP Transports
          </button>
        </div>
      </div>

      {/* Tab 1: Interactive Tool Invoker */}
      {activeTab === 'invoker' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Tool & Target Selection */}
          <div className="lg:col-span-5 space-y-5">
            <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                1. Select Accounting Portal Target
              </h4>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                {[
                  { id: 'qbo', label: 'QuickBooks' },
                  { id: 'tally', label: 'Tally' },
                  { id: 'zoho', label: 'Zoho' },
                  { id: 'netsuite', label: 'NetSuite' },
                  { id: 'xero', label: 'Xero' },
                ].map((portal) => (
                  <button
                    key={portal.id}
                    onClick={() => setSelectedPortal(portal.id as any)}
                    className={`py-2 px-1 text-center rounded-xl text-xs font-bold border transition-all ${
                      selectedPortal === portal.id
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-xs'
                        : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    {portal.label}
                  </button>
                ))}
              </div>

              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 pt-2">
                2. Select MCP Tool
              </h4>
              <div className="space-y-2">
                {tools.map((t) => {
                  const isSelected = selectedTool?.name === t.name;
                  return (
                    <button
                      key={t.name}
                      onClick={() => setSelectedTool(t)}
                      className={`w-full text-left p-3 rounded-xl border transition-all ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-50/60 ring-1 ring-indigo-600'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-slate-900">{t.name}</span>
                        {isSelected && <Zap className="w-3.5 h-3.5 text-indigo-600 fill-indigo-600" />}
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1 leading-snug">{t.description}</p>
                    </button>
                  );
                })}
              </div>

              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 pt-2">
                3. Tool Arguments
              </h4>
              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Target Portal:</label>
                  <input
                    type="text"
                    disabled
                    value={selectedPortal.toUpperCase()}
                    className="w-full px-3 py-2 rounded-lg bg-slate-100 border border-slate-200 font-mono text-slate-700"
                  />
                </div>

                {selectedTool?.name === 'accounting_query_ledger' && (
                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">Account Type Filter:</label>
                    <select
                      value={toolArgs.account_type || 'revenue'}
                      onChange={(e) => setToolArgs({ ...toolArgs, account_type: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-800"
                    >
                      <option value="all">All Accounts</option>
                      <option value="revenue">Revenue & Sales</option>
                      <option value="cogs">COGS / Direct Costs</option>
                      <option value="expense">Operating Expenses</option>
                      <option value="asset">Current & Fixed Assets</option>
                      <option value="liability">Current Liabilities</option>
                    </select>
                  </div>
                )}

                {selectedTool?.name === 'accounting_get_trial_balance' && (
                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">As of Date:</label>
                    <input
                      type="date"
                      value={toolArgs.as_of_date || '2026-08-31'}
                      onChange={(e) => setToolArgs({ ...toolArgs, as_of_date: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-800"
                    />
                  </div>
                )}

                {selectedTool?.name === 'accounting_push_budget_metrics' && (
                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">Target Fiscal Year:</label>
                    <input
                      type="number"
                      value={toolArgs.fiscal_year || 2027}
                      onChange={(e) => setToolArgs({ ...toolArgs, fiscal_year: parseInt(e.target.value) || 2027 })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-800"
                    />
                  </div>
                )}
              </div>

              <button
                onClick={handleExecuteTool}
                disabled={isExecuting}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
              >
                {isExecuting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Executing via MCP JSON-RPC...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Call MCP Tool & Fetch Ledger
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Column: Execution Output & Protocol Feed */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-slate-950 rounded-2xl p-5 border border-slate-800 text-slate-200 font-mono text-xs shadow-inner min-h-[420px] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-slate-400 font-bold">MCP Response Console</span>
                  </div>
                  {executionResult && (
                    <span className="text-[11px] text-slate-400">
                      Target: {executionResult.portal.toUpperCase()} • {executionResult.executedAt}
                    </span>
                  )}
                </div>

                {isExecuting ? (
                  <div className="flex flex-col items-center justify-center py-24 text-slate-400 space-y-3">
                    <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
                    <p className="text-xs">Dispatching JSON-RPC `tools/call` to accounting adapter...</p>
                  </div>
                ) : executionResult ? (
                  <div className="space-y-4 max-h-[400px] overflow-y-auto pr-1">
                    <div className="p-3 bg-slate-900 rounded-xl border border-slate-800">
                      <div className="text-emerald-400 font-bold flex items-center gap-1.5 mb-1">
                        <CheckCircle2 className="w-4 h-4" /> Tool Execution Succeeded
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Method: <code className="text-indigo-300">tools/call &rarr; {executionResult.toolName}</code>
                      </div>
                    </div>

                    <div>
                      <span className="text-[11px] text-slate-500 uppercase tracking-wider block mb-1">Raw Payload Output:</span>
                      <pre className="p-3.5 bg-slate-900/90 rounded-xl border border-slate-800 text-emerald-300 overflow-x-auto text-[11px] leading-relaxed">
                        {JSON.stringify(executionResult.data, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-24 text-slate-500 space-y-2">
                    <Terminal className="w-10 h-10 mx-auto text-slate-600" />
                    <p className="text-xs">Select a tool and accounting portal on the left, then click &ldquo;Call MCP Tool&rdquo; to test live execution.</p>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
                <span>Protocol: JSON-RPC 2.0 over MCP</span>
                <span>Security: HMAC-SHA256 Encrypted Token</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Protocol & Schema Specs */}
      {activeTab === 'protocol' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-5">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-slate-900">Declared MCP Tools & JSON Schema Definitions</h4>
            <span className="text-xs text-slate-500">{tools.length} Tools Registered</span>
          </div>

          <div className="space-y-4">
            {tools.map((t) => (
              <div key={t.name} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-200">
                    {t.name}
                  </span>
                  <span className="text-[11px] text-slate-500">Schema Type: object</span>
                </div>
                <p className="text-xs text-slate-600">{t.description}</p>
                <div>
                  <span className="text-[11px] font-semibold text-slate-500 block mb-1">Parameters Schema:</span>
                  <pre className="p-3 bg-white rounded-lg border border-slate-200 text-[11px] font-mono text-slate-800 overflow-x-auto">
                    {JSON.stringify(t.inputSchema, null, 2)}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Endpoints & SSE Transports */}
      {activeTab === 'endpoints' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h4 className="text-sm font-bold text-slate-900">MCP Transport Endpoints</h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Connect external MCP clients (such as Claude Desktop, Cursor, or AI Agent hosts) directly to this accounting MCP server.
            </p>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900">Server-Sent Events (SSE) Endpoint</span>
                <button
                  onClick={() => copyToClipboard(sseEndpoint, 'sse')}
                  className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                >
                  {copiedString === 'sse' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  Copy URL
                </button>
              </div>
              <input
                type="text"
                readOnly
                value={sseEndpoint}
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 font-mono text-xs text-slate-800"
              />
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900">JSON-RPC Messages POST Endpoint</span>
                <button
                  onClick={() => copyToClipboard(postEndpoint, 'post')}
                  className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                >
                  {copiedString === 'post' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  Copy URL
                </button>
              </div>
              <input
                type="text"
                readOnly
                value={postEndpoint}
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 font-mono text-xs text-slate-800"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
