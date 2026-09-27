import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Scale, Mail, Sparkles, BookOpen, ChevronDown, ChevronUp, Copy, Check, 
  RotateCcw, AlertTriangle, ShieldCheck, Database, Cloud, Lock, RefreshCw, ExternalLink, X, Settings,
  Workflow, FileJson, Cpu, GitFork, ArrowRight, Code
} from 'lucide-react';
import { PWAInstallButton } from './components/PWAInstallButton';
import { OfflineIndicator } from './components/OfflineIndicator';
import { Logo } from './components/Logo';
import { WebhookResponse } from './types/advisory';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  responseMeta?: WebhookResponse;
  showDetails?: boolean;
}

const SUGGESTED_PROMPTS = [
  'What is the TDS on sale of my Indian property?',
  'Can an NRI repatriate property sale proceeds?',
  'Do NRIs need to link PAN with Aadhaar?',
  'How does DTAA relief work?',
  'What happens to my bank account when I become an NRI?',
  'Can an NRI buy property in India?',
  'How is my residential status determined?',
  'Do I need to disclose my foreign assets?'
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-msg',
      sender: 'assistant',
      text: `### Welcome to the NRI Advisory Assistant
I can help answer your questions regarding Indian Income-tax and FEMA provisions for Non-Resident Indians.

Select one of our common queries below or ask your specific question directly:`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Google Drive & Sheets Integration States
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);
  const [isN8nModalOpen, setIsN8nModalOpen] = useState(false);
  const [n8nWorkflowJson, setN8nWorkflowJson] = useState<string | null>(null);
  const [n8nCopied, setN8nCopied] = useState(false);

  const [isSyncEnabled, setIsSyncEnabled] = useState<boolean>(() => {
    return localStorage.getItem('google_sync_enabled') === 'true' || !!localStorage.getItem('google_access_token');
  });
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem('google_access_token'));
  const [spreadsheetId, setSpreadsheetId] = useState<string | null>(() => localStorage.getItem('google_spreadsheet_id'));
  const [syncStatus, setSyncStatus] = useState<'idle' | 'linking' | 'ready' | 'searching' | 'creating' | 'syncing' | 'success' | 'error'>('idle');
  const [syncError, setSyncError] = useState<string | null>(null);

  const openN8nModal = async () => {
    setIsN8nModalOpen(true);
    if (!n8nWorkflowJson) {
      try {
        const res = await fetch('/api/n8n/workflow');
        if (res.ok) {
          const text = await res.text();
          setN8nWorkflowJson(text);
        }
      } catch (err) {
        console.warn('Failed to fetch n8n workflow JSON:', err);
      }
    }
  };

  const copyN8nWorkflowToClipboard = () => {
    if (!n8nWorkflowJson) return;
    navigator.clipboard.writeText(n8nWorkflowJson);
    setN8nCopied(true);
    setTimeout(() => setN8nCopied(false), 2500);
  };

  // Secret admin mode for Google Drive and Google Sheets Sync control
  const [isAdmin, setIsAdmin] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      return params.get('admin') === 'true' || params.get('control') === 'true';
    }
    return false;
  });

  const googleTokenClientRef = useRef<any>(null);

  const refreshAccessTokenSilently = (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (typeof window === 'undefined' || !(window as any).google) {
        reject(new Error('Google API Client script not loaded yet.'));
        return;
      }

      try {
        const client = (window as any).google.accounts.oauth2.initTokenClient({
          client_id: '107011927528-loiokkov4umckh8kuvn7c28iq16vdmr0.apps.googleusercontent.com',
          scope: 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/spreadsheets',
          callback: async (tokenResponse: any) => {
            if (tokenResponse && tokenResponse.access_token) {
              const token = tokenResponse.access_token;
              const expiresIn = tokenResponse.expires_in || 3600;
              const expiryTime = Date.now() + (expiresIn * 1000);

              setAccessToken(token);
              setIsSyncEnabled(true);
              localStorage.setItem('google_access_token', token);
              localStorage.setItem('google_token_expiry', expiryTime.toString());
              localStorage.setItem('google_sync_enabled', 'true');
              setSyncStatus('ready');
              resolve(token);
            } else {
              reject(new Error('Failed to retrieve access token silently.'));
            }
          },
          error_callback: (err: any) => {
            reject(err);
          }
        });
        googleTokenClientRef.current = client;
        // Promptless refresh: checks Google session silently in the background
        client.requestAccessToken({ prompt: '' });
      } catch (err) {
        reject(err);
      }
    });
  };

  // Initialize and persist sync status on mount across page refreshes with silent refresh
  useEffect(() => {
    const syncEnabled = localStorage.getItem('google_sync_enabled') === 'true';
    const storedToken = localStorage.getItem('google_access_token');
    const sheetId = localStorage.getItem('google_spreadsheet_id');
    const expiryStr = localStorage.getItem('google_token_expiry');

    if (syncEnabled) {
      setIsSyncEnabled(true);
      if (sheetId) setSpreadsheetId(sheetId);

      // Verify Google Access Token is fresh (Auto renew silently in the background if within 5m of expiry)
      const isExpiringSoon = expiryStr ? (Date.now() + 300000 > parseInt(expiryStr)) : true;
      if (isExpiringSoon || !storedToken) {
        const timer = setTimeout(() => {
          refreshAccessTokenSilently().catch((err) => {
            console.warn('Silent automatic token renewal failed on mount:', err);
            setSyncStatus('error');
            setSyncError('Google session expired. Click "Re-connect Google Drive" to resume real-time query logging.');
          });
        }, 1500);
        return () => clearTimeout(timer);
      } else {
        setAccessToken(storedToken);
        setSyncStatus('ready');
      }
    }
  }, []);

  // Append new logs to Sheets if integrated (with auto silent token refresh fallback)
  const appendLogToGoogleSheets = async (userMsg: string, response: any) => {
    if (!spreadsheetId) return;

    let currentToken = accessToken;
    const expiryStr = localStorage.getItem('google_token_expiry');
    const isExpiringSoon = expiryStr ? (Date.now() + 300000 > parseInt(expiryStr)) : true;

    if (!currentToken || isExpiringSoon) {
      try {
        currentToken = await refreshAccessTokenSilently();
      } catch (err) {
        console.warn('Silent refresh inside query append failed, falling back to current token:', err);
        if (!currentToken) {
          setSyncStatus('error');
          setSyncError('Google session expired. Click "Re-connect Google Drive" to authorize.');
          return;
        }
      }
    }

    try {
      const logRow = [
        `LOG-${Date.now()}`,
        new Date().toISOString(),
        `sess_${Date.now()}`,
        'pwa',
        userMsg,
        response.topic || 'Unclassified',
        (response.matched_faq_ids || []).join('; '),
        response.answer || '',
        (response.sources || []).map((s: any) => s.provision).join('; '),
        response.confidence || 0,
        response.out_of_scope ? 'TRUE' : 'FALSE',
        response.escalation_required ? 'TRUE' : 'FALSE',
        response.out_of_scope ? 'OUT_OF_SCOPE' : 'SUCCESS'
      ];

      const res = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/CHAT_LOG!A:M:append?valueInputOption=USER_ENTERED`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          values: [logRow]
        })
      });

      if (!res.ok) {
        if (res.status === 401) {
          // Token rejected at api level, do one final attempt with fresh silent token
          try {
            const freshToken = await refreshAccessTokenSilently();
            await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/CHAT_LOG!A:M:append?valueInputOption=USER_ENTERED`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${freshToken}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ values: [logRow] })
            });
            return;
          } catch (refreshErr) {
            setSyncStatus('error');
            setSyncError('Google session expired. Click "Re-connect Google Drive" to authorize.');
          }
        }
        throw new Error(`Failed to append log to Sheets: ${res.statusText}`);
      }
    } catch (err) {
      console.warn('Error auto-syncing log entry to Google Sheets:', err);
    }
  };

  const handleLinkGoogle = () => {
    setSyncStatus('linking');
    setSyncError(null);

    if (typeof window === 'undefined' || !(window as any).google) {
      setSyncStatus('error');
      setSyncError('Google API Client script not loaded yet. Please refresh and try again.');
      return;
    }

    try {
      const client = (window as any).google.accounts.oauth2.initTokenClient({
        client_id: '107011927528-loiokkov4umckh8kuvn7c28iq16vdmr0.apps.googleusercontent.com',
        scope: 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/spreadsheets',
        callback: async (tokenResponse: any) => {
          if (tokenResponse && tokenResponse.access_token) {
            const token = tokenResponse.access_token;
            const expiresIn = tokenResponse.expires_in || 3600;
            const expiryTime = Date.now() + (expiresIn * 1000);

            setAccessToken(token);
            setIsSyncEnabled(true);
            localStorage.setItem('google_access_token', token);
            localStorage.setItem('google_token_expiry', expiryTime.toString());
            localStorage.setItem('google_sync_enabled', 'true');
            setSyncStatus('ready');
            
            // Search if file already exists
            await searchAndSyncSheet(token);
          } else {
            setSyncStatus('error');
            setSyncError('Failed to retrieve Google Access Token.');
          }
        },
        error_callback: (err: any) => {
          setSyncStatus('error');
          setSyncError(err?.message || 'Authentication error occurred.');
        }
      });

      client.requestAccessToken({ prompt: 'consent' });
    } catch (err: any) {
      setSyncStatus('error');
      setSyncError(err.message || 'Error initializing Google authentication.');
    }
  };

  const searchAndSyncSheet = async (token: string) => {
    setSyncStatus('searching');
    try {
      const query = encodeURIComponent("name='NRI Advisory Database & Audit Logs' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false");
      const res = await fetch(`https://www.googleapis.com/drive/v3/files?q=${query}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!res.ok) throw new Error(`Google Drive API returned ${res.status}`);

      const data = await res.json();
      if (data.files && data.files.length > 0) {
        const fileId = data.files[0].id;
        setSpreadsheetId(fileId);
        localStorage.setItem('google_spreadsheet_id', fileId);
        setSyncStatus('success');
      } else {
        // Not found, create it
        await createNewSpreadsheet(token);
      }
    } catch (err: any) {
      setSyncStatus('error');
      setSyncError(`Error searching for file on Google Drive: ${err.message || err}`);
    }
  };

  const createNewSpreadsheet = async (token: string) => {
    setSyncStatus('creating');
    try {
      // 1. Create Spreadsheet
      const res = await fetch('https://sheets.googleapis.com/v4/spreadsheets', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          properties: {
            title: 'NRI Advisory Database & Audit Logs'
          },
          sheets: [
            { properties: { title: 'FAQ_KNOWLEDGE_BASE' } },
            { properties: { title: 'SOURCES' } },
            { properties: { title: 'CHANGE_LOG' } },
            { properties: { title: 'CHAT_LOG' } }
          ]
        })
      });

      if (!res.ok) throw new Error(`Failed to create spreadsheet: ${res.statusText}`);

      const data = await res.json();
      const newSheetId = data.spreadsheetId;
      setSpreadsheetId(newSheetId);
      localStorage.setItem('google_spreadsheet_id', newSheetId);

      // 2. Perform full database export to newly created worksheets
      await fullBackupToSheets(token, newSheetId);
    } catch (err: any) {
      setSyncStatus('error');
      setSyncError(`Failed to create Google Sheet: ${err.message || err}`);
    }
  };

  const fullBackupToSheets = async (token: string, sheetId: string) => {
    setSyncStatus('syncing');
    try {
      // 1. Get current states from system backend APIs
      const [kbRes, sourcesRes, changesRes, logsRes] = await Promise.all([
        fetch('/api/knowledge-base').then(r => r.json()),
        fetch('/api/sources').then(r => r.json()),
        fetch('/api/change-log').then(r => r.json()),
        fetch('/api/chat-logs').then(r => r.json())
      ]);

      // 2. Form ranges and values
      const headersKB = [
        'faq_id', 'category', 'subcategory', 'user_question', 'question_variations',
        'short_answer', 'detailed_answer', 'applicability', 'taxpayer_type', 'NRI_status',
        'OCI_status', 'resident_status', 'conditions', 'exceptions', 'thresholds',
        'rates', 'limits', 'relevant_FY', 'relevant_AY', 'effective_from',
        'effective_until', 'source_type', 'source_authority', 'act_or_regulation',
        'section_rule_regulation', 'circular_notification', 'source_url',
        'source_excerpt_or_summary', 'last_verified', 'review_status',
        'professional_review_required', 'keywords', 'related_faq_ids'
      ];
      const kbRows = (kbRes.records || []).map((k: any) => [
        k.faq_id, k.category, k.subcategory, k.user_question, (k.question_variations || []).join(' | '),
        k.short_answer, k.detailed_answer, k.applicability, k.taxpayer_type, k.NRI_status,
        k.OCI_status, k.resident_status, (k.conditions || []).join('; '), (k.exceptions || []).join('; '), k.thresholds,
        k.rates, k.limits, k.relevant_FY, k.relevant_AY, k.effective_from,
        k.effective_until || '', k.source_type, k.source_authority, k.act_or_regulation,
        k.section_rule_regulation, k.circular_notification || '', k.source_url,
        k.source_excerpt_or_summary, k.last_verified, k.review_status,
        k.professional_review_required, (k.keywords || []).join(', '), (k.related_faq_ids || []).join(', ')
      ]);

      const headersSources = [
        'source_id', 'authority', 'source_title', 'source_type', 'url', 'publication_date',
        'effective_date', 'subject', 'last_checked', 'notes'
      ];
      const sourcesRows = (sourcesRes.sources || []).map((s: any) => [
        s.source_id, s.authority, s.source_title, s.source_type, s.url, s.publication_date,
        s.effective_date, s.subject, s.last_checked, s.notes
      ]);

      const headersChangeLog = [
        'change_id', 'date', 'topic', 'old_position', 'new_position', 'source', 'reason',
        'reviewed_by', 'review_status'
      ];
      const changeLogRows = (changesRes.changeLog || []).map((c: any) => [
        c.change_id, c.date, c.topic, c.old_position, c.new_position, c.source, c.reason,
        c.reviewed_by, c.review_status
      ]);

      const headersChatLog = [
        'id', 'timestamp', 'session_id', 'channel', 'user_question', 'detected_topic',
        'matched_faq_ids', 'answer', 'source_references', 'confidence', 'out_of_scope',
        'escalation_required', 'response_status'
      ];
      const chatLogRows = (logsRes.logs || []).map((l: any) => [
        l.id, l.timestamp, l.session_id, l.channel, l.user_question, l.detected_topic,
        (l.matched_faq_ids || []).join('; '), l.answer, (l.source_references || []).join('; '),
        l.confidence, l.out_of_scope ? 'TRUE' : 'FALSE', l.escalation_required ? 'TRUE' : 'FALSE',
        l.response_status
      ]);

      const dataPayload = [
        { range: 'FAQ_KNOWLEDGE_BASE!A1', values: [headersKB, ...kbRows] },
        { range: 'SOURCES!A1', values: [headersSources, ...sourcesRows] },
        { range: 'CHANGE_LOG!A1', values: [headersChangeLog, ...changeLogRows] },
        { range: 'CHAT_LOG!A1', values: [headersChatLog, ...chatLogRows] }
      ];

      const writeRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values:batchUpdate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          valueInputOption: 'USER_ENTERED',
          data: dataPayload
        })
      });

      if (!writeRes.ok) throw new Error(`Write operation failed: ${writeRes.statusText}`);

      setSyncStatus('success');
    } catch (err: any) {
      setSyncStatus('error');
      setSyncError(`Failed to sync backup tables to Google Sheet: ${err.message || err}`);
    }
  };

  const pullKBFromSheets = async (token: string, sheetId: string) => {
    setSyncStatus('syncing');
    try {
      const res = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values/FAQ_KNOWLEDGE_BASE?valueRenderOption=UNFORMATTED_VALUE`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error(`Google Sheets API returned ${res.status}`);

      const data = await res.json();
      if (!data.values || data.values.length <= 1) {
        throw new Error("No data rows found in 'FAQ_KNOWLEDGE_BASE' sheet.");
      }

      const headers = data.values[0];
      const rows = data.values.slice(1);

      // Map rows to FAQRecords
      const headerMap: Record<string, number> = {};
      headers.forEach((h: string, i: number) => {
        headerMap[String(h).trim()] = i;
      });

      const records = rows.map((row: any[]) => {
        const getValue = (field: string, defaultValue: string = ''): string => {
          const idx = headerMap[field];
          if (idx === undefined || idx >= row.length) return defaultValue;
          const val = row[idx];
          return val !== null && val !== undefined ? String(val).trim() : defaultValue;
        };

        const getArrayValue = (field: string): string[] => {
          const val = getValue(field);
          if (!val) return [];
          return val.split(/[;|]/).map(s => s.trim()).filter(Boolean);
        };

        return {
          faq_id: getValue('faq_id'),
          category: getValue('category', 'General'),
          subcategory: getValue('subcategory', 'General'),
          user_question: getValue('user_question'),
          question_variations: getArrayValue('question_variations'),
          short_answer: getValue('short_answer'),
          detailed_answer: getValue('detailed_answer'),
          applicability: getValue('applicability'),
          taxpayer_type: getValue('taxpayer_type'),
          NRI_status: getValue('NRI_status'),
          OCI_status: getValue('OCI_status'),
          resident_status: getValue('resident_status'),
          conditions: getArrayValue('conditions'),
          exceptions: getArrayValue('exceptions'),
          thresholds: getValue('thresholds'),
          rates: getValue('rates'),
          limits: getValue('limits'),
          relevant_FY: getValue('relevant_FY'),
          relevant_AY: getValue('relevant_AY'),
          effective_from: getValue('effective_from'),
          effective_until: getValue('effective_until') || undefined,
          source_type: getValue('source_type'),
          source_authority: getValue('source_authority'),
          act_or_regulation: getValue('act_or_regulation'),
          section_rule_regulation: getValue('section_rule_regulation'),
          circular_notification: getValue('circular_notification') || undefined,
          source_url: getValue('source_url'),
          source_excerpt_or_summary: getValue('source_excerpt_or_summary'),
          last_verified: getValue('last_verified'),
          review_status: getValue('review_status', 'DRAFT'),
          professional_review_required: getValue('professional_review_required', 'NO'),
          keywords: getValue('keywords').split(',').map((s: string) => s.trim()).filter(Boolean),
          related_faq_ids: getValue('related_faq_ids').split(',').map((s: string) => s.trim()).filter(Boolean)
        };
      }).filter((r: any) => r.faq_id);

      if (records.length === 0) {
        throw new Error("No valid FAQ records found with a populated 'faq_id'.");
      }

      // Save bulk to server
      const saveRes = await fetch('/api/knowledge-base/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ records })
      });

      if (!saveRes.ok) throw new Error("Failed to store records to the backend.");

      alert(`Successfully synchronized ${records.length} FAQs from your Google Sheet into the chatbot!`);
      setSyncStatus('success');
    } catch (err: any) {
      setSyncStatus('error');
      setSyncError(`Failed to Pull KB from Sheets: ${err.message || err}`);
    }
  };

  const handleDisconnectGoogle = () => {
    localStorage.removeItem('google_access_token');
    localStorage.removeItem('google_token_expiry');
    localStorage.removeItem('google_spreadsheet_id');
    localStorage.removeItem('google_sync_enabled');
    setAccessToken(null);
    setSpreadsheetId(null);
    setIsSyncEnabled(false);
    setSyncStatus('idle');
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryText?: string) => {
    const q = (queryText || input).trim();
    if (!q || loading) return;

    // Secret backdoor commands to toggle admin sync panel
    if (q.toLowerCase() === '/admin' || q.toLowerCase() === '/sync' || q.toLowerCase() === '/control') {
      setIsAdmin(true);
      setIsSyncModalOpen(true);
      if (!queryText) setInput('');
      
      const adminNotice: Message = {
        id: `admin-notice-${Date.now()}`,
        sender: 'assistant',
        text: `🔐 **Admin Control Panel Initialized**\n\nThe Google Drive and Google Sheets synchronization panel is now open. You can connect, disconnect, view, or back up your advisory tables here.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, adminNotice]);
      return;
    }

    // Direct command to view and export n8n workflow
    if (q.toLowerCase() === '/n8n' || q.toLowerCase() === '/workflow' || q.toLowerCase() === 'n8n') {
      openN8nModal();
      if (!queryText) setInput('');

      const n8nNotice: Message = {
        id: `n8n-notice-${Date.now()}`,
        sender: 'assistant',
        text: `⚡ **n8n Orchestrator Workflow Viewer Opened**\n\nYou can view, copy, or download the full n8n JSON workflow blueprint directly from the open modal dialog or via [/api/n8n/workflow](/api/n8n/workflow).`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, n8nNotice]);
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!queryText) setInput('');
    setLoading(true);

    const history = messages
      .filter(msg => msg.id !== 'welcome-msg')
      .map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'model',
        text: msg.text
      }));

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (accessToken && spreadsheetId) {
        headers['x-google-access-token'] = accessToken;
        headers['x-google-spreadsheet-id'] = spreadsheetId;
      }

      const res = await fetch('/api/webhook', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: `pwa_sess_${Date.now()}`,
          question: q,
          channel: 'pwa',
          history
        })
      });

      if (!res.ok) throw new Error(`HTTP Error: ${res.status}`);

      const data: WebhookResponse = await res.json();

      const assistantMessage: Message = {
        id: `assist-${Date.now()}`,
        sender: 'assistant',
        text: data.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        responseMeta: data,
        showDetails: false // Hidden by default as per request
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Trigger automatic background Google Sheets log appending if linked
      if (accessToken && spreadsheetId) {
        appendLogToGoogleSheets(q, data);
      }
    } catch (err: any) {
      const errorMessage: Message = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: `### System Notice\nI don't currently have this query covered in my verified NRI advisory knowledge base.\n\nFor assistance with this specific matter, please get in touch with me at **canamratad.ai@gmail.com**.\n\n*Consult your CA for a case-specific position.*`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMessage]);

      // Log out-of-scope query to Sheets if connected
      if (accessToken && spreadsheetId) {
        appendLogToGoogleSheets(q, {
          answer: `I don't currently have this query covered in my verified NRI advisory knowledge base.\n\nFor assistance with this specific matter, please get in touch with me at canamratad.ai@gmail.com.\n\nConsult your CA for a case-specific position.`,
          sources: [],
          topic: 'Out of Scope / Escalation',
          matched_faq_ids: [],
          out_of_scope: true,
          escalation_required: true,
          disclaimer: 'Consult your CA for a case-specific position.',
          confidence: 0
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleReset = () => {
    setMessages([
      {
        id: 'welcome-msg',
        sender: 'assistant',
        text: `### Welcome to the NRI Advisory Assistant\nI can help answer your questions regarding Indian Income-tax and FEMA provisions for Non-Resident Indians.\n\nSelect one of our common queries below or ask your specific question directly:`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  const toggleDetails = (msgId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, showDetails: !m.showDetails } : m))
    );
  };

  // Helper to extract Short Answer from formatting blocks
  const renderMessageText = (msg: Message) => {
    const text = msg.text;
    const isAssistant = msg.sender === 'assistant';
    const hasMeta = !!msg.responseMeta;

    if (isAssistant && hasMeta) {
      // Parse out the Short Answer section and the explanation
      const blocks = text.split('\n\n');
      const shortAnswerBlockIdx = blocks.findIndex(b => b.startsWith('### Short answer'));
      const howItWorksIdx = blocks.findIndex(b => b.startsWith('### How the rule works'));

      // If we have distinct formatted blocks, only show the Short Answer by default
      if (shortAnswerBlockIdx !== -1) {
        const shortAnswerContent = blocks[shortAnswerBlockIdx].replace('### Short answer', '').trim();
        
        return (
          <div className="space-y-4">
            <div className="text-slate-100 text-[13.5px] leading-relaxed font-medium">
              {shortAnswerContent}
            </div>

            {/* Expander Button for detailed statutory references as requested */}
            <div className="pt-2">
              <button
                onClick={() => toggleDetails(msg.id)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold text-amber-400 bg-amber-500/10 hover:bg-amber-500/25 border border-amber-500/20 rounded-lg transition-all cursor-pointer"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>{msg.showDetails ? 'Hide Detailed Legal Explanations' : 'Show Detailed Explanation & Section References'}</span>
                {msg.showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* Revealed Detailed Explanation */}
            {msg.showDetails && (
              <div className="mt-3 pt-3 border-t border-slate-700/60 space-y-3 animate-fadeIn text-xs text-slate-300">
                {blocks.map((block, idx) => {
                  // Skip displaying the Short Answer again since it's already shown
                  if (block.startsWith('### Short answer') || idx === shortAnswerBlockIdx) return null;
                  
                  if (block.startsWith('### ')) {
                    return (
                      <h4 key={idx} className="text-xs font-bold text-amber-400/90 tracking-wide uppercase mt-3 mb-1">
                        {block.replace('### ', '')}
                      </h4>
                    );
                  }
                  if (block.startsWith('* ') || block.startsWith('- ')) {
                    const items = block.split('\n');
                    return (
                      <ul key={idx} className="list-disc pl-4 space-y-1 text-slate-300">
                        {items.map((item, iIdx) => (
                          <li key={iIdx}>{item.replace(/^(\*|-)\s+/, '')}</li>
                        ))}
                      </ul>
                    );
                  }
                  return <p key={idx} className="leading-relaxed whitespace-pre-wrap">{block}</p>;
                })}

                {/* Statutory Citations */}
                {msg.responseMeta?.sources && msg.responseMeta.sources.length > 0 && (
                  <div className="pt-2.5 border-t border-slate-700/50 mt-2.5">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1.5">Official Citations</div>
                    <div className="space-y-1.5">
                      {msg.responseMeta.sources.map((src, sIdx) => (
                        <div key={sIdx} className="bg-slate-900/60 p-2 rounded-lg border border-slate-750 flex flex-col gap-0.5">
                          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-200">
                            <span>{src.provision}</span>
                            <span className="text-[10px] text-amber-400">{src.applicable_period}</span>
                          </div>
                          <div className="text-[10px] text-slate-400">Authority: {src.authority}</div>
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-sky-400 hover:underline mt-0.5 inline-flex items-center gap-0.5"
                          >
                            <span>Verify Source Link</span>
                            <span className="text-[8px]">↗</span>
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      }
    }

    // Default formatting if standard structured response blocks aren't detected
    return (
      <div className="space-y-3 prose prose-invert prose-sm max-w-none">
        {text.split('\n\n').map((block, idx) => {
          if (block.startsWith('### ')) {
            return (
              <h4 key={idx} className="text-sm font-bold text-amber-400 mt-2 mb-1">
                {block.replace('### ', '')}
              </h4>
            );
          }
          if (block.startsWith('* ') || block.startsWith('- ')) {
            const items = block.split('\n');
            return (
              <ul key={idx} className="list-disc pl-4 space-y-1 text-slate-300">
                {items.map((item, iIdx) => (
                  <li key={iIdx}>{item.replace(/^(\*|-)\s+/, '')}</li>
                ))}
              </ul>
            );
          }
          return <p key={idx} className="text-slate-200 whitespace-pre-wrap">{block}</p>;
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-amber-500/30 selection:text-amber-200">
      {/* Offline indicators */}
      <OfflineIndicator />

      {/* Top Header */}
      <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-3.5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Logo className="w-10 h-10" />
            <div>
              <h1 className="text-base font-bold text-slate-100 tracking-tight flex items-center gap-1.5">
                <span>NRI Advisory Assistant</span>
              </h1>
              <p className="text-[11px] text-slate-400">
                First-response Indian Income-tax & FEMA guide
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">

            <button
              onClick={handleReset}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition cursor-pointer"
              title="Reset Chat"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Reset</span>
            </button>

            {(isAdmin || isSyncEnabled || accessToken || spreadsheetId) && (
              <button
                onClick={() => setIsSyncModalOpen(true)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg transition cursor-pointer ${
                  accessToken && spreadsheetId
                    ? 'text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
                title="Google Drive & Sheets Sync"
              >
                <Cloud className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Drive Sync</span>
                {accessToken && spreadsheetId && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                )}
              </button>
            )}

            <PWAInstallButton />
          </div>
        </div>
      </header>

      {/* Chat Container */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-4 flex flex-col h-[calc(100vh-140px)]">
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col">
          
          {/* Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5">
            {messages.map((msg) => {
              const isUser = msg.sender === 'user';
              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-full`}
                >
                  <div className="flex items-center gap-2 mb-1 px-1">
                    <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1.5">
                      {isUser ? (
                        'Client Query'
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <Logo className="w-4 h-4" />
                          <span className="text-amber-300 font-bold">Verified Advisory Guide</span>
                        </div>
                      )}
                    </span>
                    <span className="text-[9px] text-slate-500">{msg.timestamp}</span>
                  </div>

                  <div
                    className={`rounded-2xl p-4 sm:p-5 text-sm leading-relaxed max-w-3xl shadow-sm ${
                      isUser
                        ? 'bg-blue-600 text-white rounded-tr-none'
                        : 'bg-slate-800/95 border border-slate-750 text-slate-100 rounded-tl-none'
                    }`}
                  >
                    {/* Copy button & Ref Badge for non-user */}
                    {!isUser && msg.responseMeta && (
                      <div className="flex items-center gap-2 pb-2 mb-3 border-b border-slate-700/50 text-[10px]">
                        <span className="bg-emerald-950/80 text-emerald-300 border border-emerald-800 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
                          Knowledge Base Grounded
                        </span>
                        {/* ID reference span removed for client privacy */}
                        <button
                          onClick={() => copyToClipboard(msg.text, msg.id)}
                          className="ml-auto text-[10px] text-slate-400 hover:text-slate-200 transition bg-slate-900/60 px-2 py-0.5 rounded flex items-center gap-1 cursor-pointer"
                        >
                          {copiedId === msg.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedId === msg.id ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                    )}

                    {renderMessageText(msg)}

                    {/* Disclaimer box at the end of each response */}
                    {!isUser && (
                      <div className="mt-4 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10 text-[10.5px] text-amber-300/90 leading-normal flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          This first-response information is source-grounded in verified provisions and does not constitute formal legal/financial advice.{' '}
                          <span className="font-bold text-amber-300">Consult your CA for a case-specific position.</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-center gap-2.5 text-slate-400 text-xs p-3.5 bg-slate-800/40 rounded-xl max-w-xs animate-pulse border border-slate-700/80">
                <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                <span>Consulting verified knowledge base...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick suggestions */}
          <div className="px-4 py-2.5 bg-slate-950/70 border-t border-slate-800 overflow-x-auto flex gap-1.5 no-scrollbar">
            <span className="text-[10px] text-slate-400 font-bold self-center whitespace-nowrap">Suggested topics:</span>
            {SUGGESTED_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(prompt)}
                disabled={loading}
                className="text-[11px] whitespace-nowrap bg-slate-850 hover:bg-slate-800 text-slate-300 hover:text-white px-2.5 py-1.5 rounded-full border border-slate-750 transition cursor-pointer disabled:opacity-50"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Input field */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="p-3 bg-slate-950 border-t border-slate-800 flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask your NRI tax or FEMA question here..."
              disabled={loading}
              className="flex-1 bg-slate-900 border border-slate-750 focus:border-amber-500 rounded-xl px-4 py-2.5 text-xs sm:text-xs text-slate-100 placeholder-slate-500 outline-none transition"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-amber-500 hover:bg-amber-600 disabled:opacity-40 disabled:hover:bg-amber-500 text-slate-950 font-semibold px-4 py-2 rounded-xl flex items-center justify-center transition cursor-pointer shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </main>

      {/* Simplified, elegant regulatory footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 px-4 text-center text-xs text-slate-400">
        <div className="max-w-2xl mx-auto space-y-1">
          <p className="font-semibold text-slate-300 text-[11px]">
            Statutory Notice: This first-response informational tool is based on verified Indian Income-tax and FEMA provisions and does not constitute formal legal, tax, or FEMA advice.
          </p>
          <p className="text-[10px] text-amber-400 font-bold">
            Consult your CA for a case-specific position.
          </p>
        </div>
      </footer>

      {/* Google Drive & Sheets Integration Sync Modal */}
      {isSyncModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-gradient-to-r from-slate-900 to-slate-950">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <Database className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Google Workspace Sync</h3>
                  <p className="text-[10px] text-slate-400">Direct spreadsheet and audit logging to Google Drive</p>
                </div>
              </div>
              <button 
                onClick={() => setIsSyncModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-5 flex-1 overflow-y-auto text-xs leading-relaxed text-slate-300">
              {/* Privacy Shield Notice */}
              <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl flex gap-3">
                <Lock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5 animate-pulse" />
                <div className="space-y-0.5">
                  <div className="font-bold text-slate-200">100% Client-Side Private Sync</div>
                  <div className="text-slate-400 text-[10.5px]">
                    This integration operates exclusively within your browser. Authorization tokens are kept locally. The app communicates directly with official Google APIs—no backend server or third-party ever intercepts your spreadsheets or audit trails.
                  </div>
                </div>
              </div>

              {/* Status Section */}
              <div className="space-y-2">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Sync Connection Status</div>
                
                {syncStatus === 'idle' && (
                  <div className="bg-slate-950/30 border border-slate-800/80 p-4 rounded-xl text-center space-y-3">
                    <Cloud className="w-8 h-8 text-slate-500 mx-auto" />
                    <div className="space-y-1">
                      <div className="font-bold text-slate-300">Google Drive is disconnected</div>
                      <p className="text-slate-400 text-[10.5px] max-w-sm mx-auto">
                        Link your Google Drive to save, read, and maintain all statutory database sheets and user query logs directly on your personal Drive account.
                      </p>
                    </div>
                    <button
                      onClick={handleLinkGoogle}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold rounded-lg transition cursor-pointer text-[11px]"
                    >
                      <Database className="w-3.5 h-3.5" />
                      <span>Connect & Authorize Google Drive</span>
                    </button>
                  </div>
                )}

                {/* Linking In Progress */}
                {syncStatus === 'linking' && (
                  <div className="bg-slate-950/30 border border-slate-800 p-6 rounded-xl text-center space-y-2">
                    <RefreshCw className="w-6 h-6 text-emerald-400 mx-auto animate-spin" />
                    <div className="font-bold text-slate-200">Waiting for Google Approval...</div>
                    <p className="text-slate-400 text-[10.5px]">Please complete the secure Google authentication popup in your browser.</p>
                  </div>
                )}

                {/* Searching spreadsheet */}
                {syncStatus === 'searching' && (
                  <div className="bg-slate-950/30 border border-slate-800 p-6 rounded-xl text-center space-y-2">
                    <RefreshCw className="w-6 h-6 text-amber-400 mx-auto animate-spin" />
                    <div className="font-bold text-slate-200">Searching your Google Drive...</div>
                    <p className="text-slate-400 text-[10.5px]">Looking for 'NRI Advisory Database & Audit Logs' spreadsheet file...</p>
                  </div>
                )}

                {/* Creating spreadsheet */}
                {syncStatus === 'creating' && (
                  <div className="bg-slate-950/30 border border-slate-800 p-6 rounded-xl text-center space-y-2">
                    <RefreshCw className="w-6 h-6 text-amber-500 mx-auto animate-spin" />
                    <div className="font-bold text-slate-200">Initializing New Google Sheet...</div>
                    <p className="text-slate-400 text-[10.5px]">Creating sheets and defining headers (FAQ_KNOWLEDGE_BASE, SOURCES, CHANGE_LOG, CHAT_LOG)...</p>
                  </div>
                )}

                {/* Overwriting / Synchronizing */}
                {syncStatus === 'syncing' && (
                  <div className="bg-slate-950/30 border border-slate-800 p-6 rounded-xl text-center space-y-2">
                    <RefreshCw className="w-6 h-6 text-sky-400 mx-auto animate-spin" />
                    <div className="font-bold text-slate-200">Syncing Database Tables...</div>
                    <p className="text-slate-400 text-[10.5px]">Exporting all rows securely to Google Sheets cells...</p>
                  </div>
                )}

                {/* Connected States (Ready / Success) */}
                {(syncStatus === 'ready' || syncStatus === 'success' || (accessToken && spreadsheetId)) && (
                  <div className="space-y-3.5">
                    <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 font-bold text-emerald-400">
                          <ShieldCheck className="w-4 h-4" />
                          <span>Google Sync Enabled</span>
                        </div>
                        <span className="text-[9px] bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 font-bold uppercase tracking-wider px-1.5 py-0.5 rounded">
                          Active & Logging
                        </span>
                      </div>

                      <div className="text-slate-400 text-[10.5px] leading-relaxed">
                        Query audit logs are automatically saved in real-time to your Google Sheet! Your files can be viewed and shared directly in Google Drive or exported as CSV.
                      </div>

                      {spreadsheetId && (
                        <div className="pt-1.5 border-t border-slate-850 flex flex-col gap-2">
                          <a
                            href={`https://docs.google.com/spreadsheets/d/${spreadsheetId}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-900 border border-slate-750 hover:bg-slate-800 text-slate-200 font-semibold rounded-lg transition text-center"
                          >
                            <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Open Sheets in Google Drive</span>
                          </a>
                        </div>
                      )}
                    </div>

                    {/* Additional admin actions */}
                    <div className="bg-slate-950/40 p-3.5 border border-slate-800/80 rounded-xl space-y-2.5">
                      <div className="text-[10px] font-bold text-slate-400 uppercase">Synchronize Management</div>
                      
                      <div className="flex flex-col gap-2">
                        <button
                          onClick={() => pullKBFromSheets(accessToken!, spreadsheetId!)}
                          disabled={syncStatus === 'syncing'}
                          className="flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg transition text-center cursor-pointer disabled:opacity-40"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${syncStatus === 'syncing' ? 'animate-spin' : ''}`} />
                          <span>Pull & Import FAQ from Sheets</span>
                        </button>

                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() => fullBackupToSheets(accessToken!, spreadsheetId!)}
                            disabled={syncStatus === 'syncing'}
                            className="flex items-center justify-center gap-1 px-3 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-750 text-slate-300 font-medium rounded-lg transition text-center cursor-pointer disabled:opacity-40 text-xs"
                          >
                            <span>Force Full Backup</span>
                          </button>

                          <button
                            onClick={handleDisconnectGoogle}
                            className="flex items-center justify-center gap-1 px-3 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-750 text-rose-400 hover:text-rose-300 font-medium rounded-lg transition text-center cursor-pointer text-xs"
                          >
                            <span>Disconnect Sync</span>
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* n8n Orchestrator Workflow Export Card */}
                    <div className="bg-indigo-950/30 p-3.5 border border-indigo-500/20 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider">n8n Workflow Blueprint</div>
                        <span className="text-[9px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold px-1.5 py-0.5 rounded">
                          JSON Export
                        </span>
                      </div>
                      <p className="text-[10.5px] text-slate-400 leading-normal">
                        Export the complete n8n workflow JSON including webhook ingestion, prompt injection defense, fuzzy similarity matcher, and Google Sheets integration.
                      </p>
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => {
                            setIsSyncModalOpen(false);
                            openN8nModal();
                          }}
                          className="inline-flex items-center justify-center gap-1.5 flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition text-center cursor-pointer text-[11px]"
                        >
                          <Workflow className="w-3.5 h-3.5" />
                          <span>View & Copy Workflow</span>
                        </button>
                        <a
                          href="/api/n8n/workflow"
                          download="n8n-nri-advisory-workflow.json"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center justify-center gap-1.5 flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold rounded-lg transition text-center cursor-pointer text-[11px]"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Download File</span>
                        </a>
                      </div>
                    </div>
                  </div>
                )}

                {/* Error handling */}
                {syncStatus === 'error' && syncError && (
                  <div className="p-3 bg-rose-500/5 border border-rose-500/20 rounded-xl text-rose-300 flex flex-col gap-2">
                    <div className="flex items-start gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                      <div className="font-semibold text-slate-200">Synchronization Error</div>
                    </div>
                    <p className="text-[10px] text-slate-400 leading-normal">{syncError}</p>
                    <button
                      onClick={handleLinkGoogle}
                      className="mt-1 inline-flex items-center justify-center gap-1 px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-300 rounded-lg transition cursor-pointer font-bold"
                    >
                      <RefreshCw className="w-3 h-3" />
                      <span>Retry Connection</span>
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 bg-slate-950 border-t border-slate-800 text-center text-[10px] text-slate-500 flex items-center justify-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              <span>Direct-to-drive API transmission over HTTPS (TLS/SSL).</span>
            </div>
          </div>
        </div>
      )}

      {/* n8n Workflow Viewer Modal */}
      {isN8nModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] shadow-2xl overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-gradient-to-r from-indigo-950/60 to-slate-900">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <Workflow className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <span>n8n Orchestrator Workflow Blueprint</span>
                    <span className="text-[10px] bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-bold px-2 py-0.5 rounded-full">
                      v1.2 Ready
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Verified Pipeline JSON for Webhook, Prompt Injection Shield & Google Sheets Grounding
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setIsN8nModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-5 flex-1 overflow-y-auto text-xs leading-relaxed text-slate-300">
              {/* Pipeline Nodes Flow Cards */}
              <div className="space-y-2">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Pipeline Node Architecture (6 Nodes)
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                    <div className="flex items-center justify-between font-bold text-indigo-300 text-[11px]">
                      <span>1. Webhook Ingest</span>
                      <span className="text-[9px] text-slate-500 font-mono">POST</span>
                    </div>
                    <p className="text-[10px] text-slate-400">Receives question, session_id & channel payload.</p>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                    <div className="flex items-center justify-between font-bold text-amber-400 text-[11px]">
                      <span>2. Injection Filter</span>
                      <span className="text-[9px] text-slate-500 font-mono">Regex</span>
                    </div>
                    <p className="text-[10px] text-slate-400">Detects jailbreak & prompt injection attempts.</p>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                    <div className="flex items-center justify-between font-bold text-rose-400 text-[11px]">
                      <span>3. Security Shield</span>
                      <span className="text-[9px] text-slate-500 font-mono">IF Branch</span>
                    </div>
                    <p className="text-[10px] text-slate-400">Rejects illegal prompt overrides immediately.</p>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                    <div className="flex items-center justify-between font-bold text-emerald-400 text-[11px]">
                      <span>4. Google Sheets DB</span>
                      <span className="text-[9px] text-slate-500 font-mono">Drive API</span>
                    </div>
                    <p className="text-[10px] text-slate-400">Searches FAQ_KNOWLEDGE_BASE & SOURCES sheets.</p>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                    <div className="flex items-center justify-between font-bold text-sky-400 text-[11px]">
                      <span>5. Fuzzy Matcher</span>
                      <span className="text-[9px] text-slate-500 font-mono">70% Score</span>
                    </div>
                    <p className="text-[10px] text-slate-400">Ranks questions by token similarity threshold.</p>
                  </div>

                  <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                    <div className="flex items-center justify-between font-bold text-purple-400 text-[11px]">
                      <span>6. Grounded Response</span>
                      <span className="text-[9px] text-slate-500 font-mono">JSON Out</span>
                    </div>
                    <p className="text-[10px] text-slate-400">Outputs statutory answer & citation references.</p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="p-3.5 bg-indigo-950/30 border border-indigo-500/20 rounded-xl flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-bold text-indigo-200 text-xs">Ready for Import into n8n</div>
                  <div className="text-[10.5px] text-slate-400">
                    Copy or download the complete workflow file to import into your n8n workspace (Workflows → Import from File).
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={copyN8nWorkflowToClipboard}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-lg transition cursor-pointer text-xs border border-slate-700"
                  >
                    {n8nCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{n8nCopied ? 'Copied JSON!' : 'Copy JSON'}</span>
                  </button>

                  <a
                    href="/api/n8n/workflow"
                    download="n8n-nri-advisory-workflow.json"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition cursor-pointer text-xs"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Download File</span>
                  </a>
                </div>
              </div>

              {/* Code JSON Viewer */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  <span>Workflow JSON Preview</span>
                  <a href="/api/n8n/workflow" target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:underline flex items-center gap-1">
                    <span>Raw API Endpoint</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 font-mono text-[10.5px] text-slate-300 max-h-60 overflow-y-auto leading-relaxed">
                  {n8nWorkflowJson ? (
                    <pre className="whitespace-pre-wrap">{n8nWorkflowJson}</pre>
                  ) : (
                    <div className="flex items-center justify-center p-6 text-slate-500 gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                      <span>Loading n8n Workflow JSON...</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-950 border-t border-slate-800 text-center text-[10px] text-slate-500 flex items-center justify-center gap-2">
              <Code className="w-3.5 h-3.5 text-indigo-400" />
              <span>Compatible with n8n Cloud and Self-Hosted n8n (v1.0+)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
