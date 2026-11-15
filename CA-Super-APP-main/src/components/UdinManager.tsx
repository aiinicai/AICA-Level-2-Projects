import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  KeyRound, 
  Copy, 
  Check, 
  ExternalLink, 
  Edit3, 
  UserCheck, 
  Eye, 
  EyeOff, 
  X, 
  Sparkles,
  Zap,
  Bookmark
} from 'lucide-react';

interface UdinManagerProps {
  isOpen?: boolean;
  onClose?: () => void;
  isEmbedded?: boolean;
}

export const UdinManager: React.FC<UdinManagerProps> = ({ isOpen, onClose, isEmbedded = false }) => {
  const { udinPartners, updateUdinCredentials } = useApp();

  const [activePartnerKey, setActivePartnerKey] = useState<'partner1' | 'partner2'>('partner1');
  const [showPassword, setShowPassword] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [autoFillTriggered, setAutoFillTriggered] = useState(false);

  // Edit credentials state
  const [isEditing, setIsEditing] = useState(false);
  const [editUserId, setEditUserId] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editMembershipNo, setEditMembershipNo] = useState('');
  const [editPartnerName, setEditPartnerName] = useState('');

  if (!isEmbedded && !isOpen) return null;

  const currentPartner = udinPartners[activePartnerKey];

  const handleCopy = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => {
      setCopiedField(null);
    }, 2000);
  };

  const handleOpenEdit = () => {
    setEditUserId(currentPartner.userId);
    setEditPassword(currentPartner.passwordHash);
    setEditMembershipNo(currentPartner.membershipNo);
    setEditPartnerName(currentPartner.name);
    setIsEditing(true);
  };

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    updateUdinCredentials(activePartnerKey, {
      userId: editUserId.trim(),
      passwordHash: editPassword.trim(),
      membershipNo: editMembershipNo.trim(),
      name: editPartnerName.trim()
    });
    setIsEditing(false);
  };

  // Direct Auto-Login Action: Prepares credentials, copies to clipboard, and opens https://udin.icai.org
  const handleDirectLaunchUdin = () => {
    // Copy password to clipboard so user can simply paste into the password box or use auto-fill
    navigator.clipboard.writeText(currentPartner.passwordHash);
    setAutoFillTriggered(true);

    // Open ICAI UDIN official portal in new tab
    window.open('https://udin.icai.org/', '_blank');
  };

  // 1-Click Bookmarklet script that fills User ID and Password automatically on udin.icai.org
  const autoFillBookmarklet = `javascript:(function(){var u=document.querySelector('input[type=text],#userName,#txtUserName,#UserName,#username');var p=document.querySelector('input[type=password],#password,#txtPassword,#Password');if(u){u.value='${currentPartner.userId}';u.dispatchEvent(new Event('input',{bubbles:true}));}if(p){p.value='${currentPartner.passwordHash}';p.dispatchEvent(new Event('input',{bubbles:true}));}})();`;

  const content = (
    <div className={`w-full bg-white rounded-2xl ${isEmbedded ? 'border border-amber-300 shadow-xs' : 'shadow-2xl border border-amber-200 max-w-2xl max-h-[92vh] flex flex-col'} overflow-hidden`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-white/10 backdrop-blur-xs">
            <KeyRound className="w-5 h-5 text-amber-200" />
          </div>
          <div>
            <h2 className="text-base font-black leading-tight text-white">ICAI UDIN Portal Direct Assistant</h2>
            <p className="text-xs text-amber-200 font-medium">Automatic Credential Injection &amp; Fast Launch for Firm Partners</p>
          </div>
        </div>
        {!isEmbedded && onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-amber-100 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <div className="p-5 sm:p-6 overflow-y-auto space-y-4">
        {/* Partner Selection Tabs (Partner 1 and Partner 2) */}
        <div className="grid grid-cols-2 gap-3 p-1.5 bg-amber-50 rounded-xl border border-amber-200">
          <button
            type="button"
            onClick={() => {
              setActivePartnerKey('partner1');
              setIsEditing(false);
              setAutoFillTriggered(false);
            }}
            className={`p-3 rounded-xl text-left transition-all cursor-pointer ${
              activePartnerKey === 'partner1'
                ? 'bg-white text-amber-950 shadow-xs border border-amber-300 ring-2 ring-amber-500/40'
                : 'text-amber-900 hover:text-amber-950 hover:bg-amber-100/60'
            }`}
          >
            <div className="flex items-center space-x-1.5 text-xs font-black">
              <UserCheck className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>Partner 1: CA Rishu Garg</span>
            </div>
            <div className="text-[11px] text-amber-800/80 mt-0.5 font-medium">
              User ID: <strong className="text-amber-950 font-mono">{udinPartners.partner1.userId}</strong>
            </div>
          </button>

          <button
            type="button"
            onClick={() => {
              setActivePartnerKey('partner2');
              setIsEditing(false);
              setAutoFillTriggered(false);
            }}
            className={`p-3 rounded-xl text-left transition-all cursor-pointer ${
              activePartnerKey === 'partner2'
                ? 'bg-white text-amber-950 shadow-xs border border-amber-300 ring-2 ring-amber-500/40'
                : 'text-amber-900 hover:text-amber-950 hover:bg-amber-100/60'
            }`}
          >
            <div className="flex items-center space-x-1.5 text-xs font-black">
              <UserCheck className="w-4 h-4 text-amber-700 shrink-0" />
              <span>Partner 2: CA Mohit Singla</span>
            </div>
            <div className="text-[11px] text-amber-800/80 mt-0.5 font-medium">
              User ID: <strong className="text-amber-950 font-mono">{udinPartners.partner2.userId}</strong>
            </div>
          </button>
        </div>

        {!isEditing ? (
          <div className="bg-amber-50/40 rounded-2xl p-4 sm:p-5 border border-amber-200 space-y-4">
            <div className="flex items-center justify-between border-b border-amber-200/80 pb-3">
              <div>
                <h3 className="font-extrabold text-amber-950 text-sm">{currentPartner.name}</h3>
                <p className="text-[11px] text-amber-800 font-medium">
                  ICAI Member No: <span className="font-mono font-bold text-amber-950">{currentPartner.membershipNo}</span>
                </p>
              </div>

              {/* Edit Credentials Button */}
              <button
                type="button"
                onClick={handleOpenEdit}
                className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-amber-900 bg-amber-100 hover:bg-amber-200 border border-amber-300 transition-colors cursor-pointer"
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Edit Credentials</span>
              </button>
            </div>

            {/* Credentials Fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* User ID */}
              <div className="bg-white p-3 rounded-xl border border-amber-200">
                <span className="text-[10px] font-bold text-amber-800/80 block mb-1 uppercase tracking-wider">
                  UDIN USER ID / MEMBERSHIP NO
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-black text-amber-950 text-sm tracking-wide">
                    {currentPartner.userId}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopy(currentPartner.userId, 'userId')}
                    className="p-1.5 rounded-lg text-amber-700 hover:text-amber-950 hover:bg-amber-100 cursor-pointer"
                    title="Copy User ID"
                  >
                    {copiedField === 'userId' ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Password */}
              <div className="bg-white p-3 rounded-xl border border-amber-200">
                <span className="text-[10px] font-bold text-amber-800/80 block mb-1 uppercase tracking-wider">
                  UDIN PORTAL PASSWORD
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-black text-amber-950 text-sm">
                    {showPassword ? currentPartner.passwordHash : '••••••••••••'}
                  </span>
                  <div className="flex items-center space-x-1">
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="p-1.5 rounded-lg text-amber-700 hover:text-amber-950 hover:bg-amber-100 cursor-pointer"
                      title={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleCopy(currentPartner.passwordHash, 'password')}
                      className="p-1.5 rounded-lg text-amber-700 hover:text-amber-950 hover:bg-amber-100 cursor-pointer"
                      title="Copy Password"
                    >
                      {copiedField === 'password' ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Direct Launch to ICAI UDIN Site Button */}
            <div className="space-y-2 pt-1">
              <button
                type="button"
                onClick={handleDirectLaunchUdin}
                className="w-full py-3 px-4 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-white rounded-xl text-sm font-black shadow-md transition-all flex items-center justify-center space-x-2 active:scale-98 cursor-pointer"
              >
                <Zap className="w-4 h-4 text-amber-200" />
                <span>Direct Login to ICAI UDIN Site ({currentPartner.name.split(' ')[1] || 'Partner'})</span>
                <ExternalLink className="w-4 h-4" />
              </button>

              <p className="text-[11px] text-center text-amber-900/80 font-medium">
                Directly opens <strong>https://udin.icai.org/</strong> in a new tab with User ID &amp; Password copied. Your only task at the portal is to enter the Captcha.
              </p>
            </div>

            {/* Auto-Fill Bookmarklet Helper */}
            <div className="p-3 bg-white rounded-xl border border-amber-200 text-xs text-amber-950 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold flex items-center space-x-1 text-amber-950">
                  <Bookmark className="w-3.5 h-3.5 text-amber-700" />
                  <span>1-Click Auto-Fill Shortcut for Browser Bookmarks</span>
                </span>
                <button
                  type="button"
                  onClick={() => handleCopy(autoFillBookmarklet, 'bookmarklet')}
                  className="text-[11px] font-bold text-amber-800 hover:text-amber-950 underline flex items-center space-x-1 cursor-pointer"
                >
                  {copiedField === 'bookmarklet' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedField === 'bookmarklet' ? 'Script Copied!' : 'Copy Script'}</span>
                </button>
              </div>
              <p className="text-[11px] text-amber-800/80 leading-relaxed">
                Drag this link to your browser Bookmarks Bar: <a href={autoFillBookmarklet} onClick={e => e.preventDefault()} className="font-bold text-amber-900 underline hover:text-amber-950 bg-amber-100 px-1.5 py-0.5 rounded cursor-grab">⚡ AutoFill UDIN ({currentPartner.userId})</a>. When on the ICAI UDIN login page, simply click the bookmark to insert both User ID &amp; Password in 1 second!
              </p>
            </div>

            {autoFillTriggered && (
              <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-xl text-xs text-emerald-950 flex items-start space-x-2 animate-in fade-in">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-emerald-900">
                    UDIN Portal Opened in New Tab!
                  </div>
                  <div className="text-[11px] text-emerald-800 mt-0.5">
                    User ID: <strong className="font-mono">{currentPartner.userId}</strong> • Password is ready to paste (<kbd className="px-1 py-0.2 bg-white rounded border border-emerald-300 font-mono text-[10px]">Ctrl+V</kbd>). At the portal, simply type the Captcha and submit!
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Edit Credentials Form */
          <form onSubmit={handleSaveEdit} className="bg-amber-50/40 rounded-2xl p-4 sm:p-5 border border-amber-200 space-y-3.5 text-xs text-amber-950">
            <div className="flex items-center justify-between border-b border-amber-200 pb-2">
              <h3 className="font-bold text-amber-950 text-xs">
                Update UDIN Credentials for {activePartnerKey === 'partner1' ? 'Partner 1 (CA Rishu Garg)' : 'Partner 2 (CA Mohit Singla)'}
              </h3>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="text-xs text-amber-800 hover:text-amber-950 font-semibold cursor-pointer"
              >
                Cancel
              </button>
            </div>

            <div>
              <label className="block text-xs font-bold text-amber-950 mb-1">Partner Full Name</label>
              <input
                type="text"
                value={editPartnerName}
                onChange={e => setEditPartnerName(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-amber-500 font-semibold text-amber-950"
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-amber-950 mb-1">Membership No</label>
                <input
                  type="text"
                  value={editMembershipNo}
                  onChange={e => setEditMembershipNo(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono font-bold text-amber-950"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-amber-950 mb-1">UDIN Portal User ID</label>
                <input
                  type="text"
                  value={editUserId}
                  onChange={e => setEditUserId(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono font-bold text-amber-950"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-amber-950 mb-1">UDIN Portal Password</label>
              <input
                type="text"
                value={editPassword}
                onChange={e => setEditPassword(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono font-bold text-amber-950"
                required
              />
            </div>

            <div className="pt-2 flex items-center justify-end space-x-2">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-3 py-1.5 border border-amber-300 text-amber-900 rounded-xl text-xs font-semibold hover:bg-amber-100 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-white rounded-xl text-xs font-bold shadow-xs transition-all flex items-center space-x-1 cursor-pointer"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Save Credentials</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );

  if (isEmbedded) {
    return content;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      {content}
    </div>
  );
};
