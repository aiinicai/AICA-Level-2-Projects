import React from 'react';
import { User } from '../types';
import { MOCK_USERS } from '../data/mockData';
import { 
  ShieldCheck, 
  Lock, 
  User as UserIcon, 
  ArrowRight, 
  CheckCircle2, 
  XCircle, 
  Eye, 
  EyeOff, 
  Award, 
  Building2, 
  Sparkles,
  Scale,
  Cpu,
  BarChart3,
  Layers,
  Check,
  Globe2,
  ExternalLink,
  Download
} from 'lucide-react';

interface LandingLoginScreenProps {
  onLoginSuccess: (user: User) => void;
}

export const LandingLoginScreen: React.FC<LandingLoginScreenProps> = ({ onLoginSuccess }) => {
  const [isRegisterMode, setIsRegisterMode] = React.useState<boolean>(false);
  const [username, setUsername] = React.useState<string>('zayed.dhaheri@paras-advisory.ae');
  const [password, setPassword] = React.useState<string>('Audit@2026');
  const [showPassword, setShowPassword] = React.useState<boolean>(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // Password validation checks (8+ chars, 1 uppercase, 1 special character)
  const hasMinLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password);
  const isPasswordValid = hasMinLength && hasUppercase && hasSpecialChar;

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!username.trim()) {
      setErrorMessage('Please enter your username or registered enterprise email address.');
      return;
    }

    if (!isPasswordValid) {
      setErrorMessage('Password must contain at least 8 characters with at least one uppercase letter and one special character.');
      return;
    }

    const matchedUser = MOCK_USERS.find(
      (u) => u.email.toLowerCase() === username.trim().toLowerCase() ||
             u.fullName.toLowerCase() === username.trim().toLowerCase() ||
             u.employeeIdCode.toLowerCase() === username.trim().toLowerCase()
    );

    if (matchedUser) {
      onLoginSuccess(matchedUser);
    } else {
      const newUser: User = {
        id: `emp-${Date.now()}`,
        employeeIdCode: `EMP-0${Math.floor(100 + Math.random() * 900)}`,
        fullName: username.includes('@') ? username.split('@')[0].replace('.', ' ').toUpperCase() : username,
        email: username.includes('@') ? username : `${username.toLowerCase()}@paras-advisory.ae`,
        avatarUrl: '',
        role: 'employee',
        departmentId: 'dept-audit',
        departmentName: 'Statutory Audit & Assurance',
        managerId: 'emp-tariq',
        managerName: 'Tariq Al Hammadi',
        joiningDate: '2024-01-15',
        tenureYears: 2.8,
        currentDesignation: 'Chartered Audit Senior Consultant',
        payGradeLevel: 'Grade L4 - Senior Specialist',
        status: 'Active',
        officeLocation: 'Al Maryah Tower, Abu Dhabi',
        baseSalaryAED: 28000,
      };
      onLoginSuccess(newUser);
    }
  };

  const handleQuickDemoSelect = (user: User) => {
    setUsername(user.email);
    setPassword('Audit@2026');
    onLoginSuccess(user);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans selection:bg-teal-500/30 selection:text-teal-200">
      {/* Top Enterprise Navigation Header (Style of Oracle Cloud, SAP SuccessFactors, Zoho One, TallyPrime) */}
      <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800/80 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Wordmark */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-700 via-blue-900 to-teal-600 flex items-center justify-center text-white font-black text-xl shadow-md border border-teal-500/30">
              P
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-extrabold tracking-tight text-white leading-tight">
                  PARAS <span className="text-teal-400">ADVISORY</span>
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-teal-300 border border-slate-700 font-mono">
                  ENTERPRISE HCM
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-medium block leading-none mt-0.5">
                Performance & Human Capital Intelligence Cloud
              </span>
            </div>
          </div>

          {/* Enterprise Capabilities Ticker */}
          <div className="hidden md:flex items-center gap-6 text-xs text-slate-400 font-medium">
            <span className="flex items-center gap-1.5 hover:text-slate-200 transition-colors">
              <Cpu className="w-3.5 h-3.5 text-teal-400" />
              <span>4-Pillar Valuation Matrix</span>
            </span>
            <span className="flex items-center gap-1.5 hover:text-slate-200 transition-colors">
              <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
              <span>Intellectual Capital Ledger</span>
            </span>
            <span className="flex items-center gap-1.5 hover:text-slate-200 transition-colors">
              <Scale className="w-3.5 h-3.5 text-rose-400" />
              <span>UAE Labor Law Decree 33/2021</span>
            </span>
          </div>

          {/* Quick Demo & Capstone Download Buttons */}
          <div className="flex items-center gap-3">
            <a
              href="/paras_advisory_capstone.zip"
              download="paras_advisory_capstone.zip"
              className="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/35 border border-blue-500/40 text-blue-300 font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
              title="Download clean capstone zip (33 files, no node_modules) ready for GitHub"
            >
              <Download className="w-3.5 h-3.5 text-blue-400" />
              <span>Download .ZIP</span>
            </a>
            <button
              type="button"
              onClick={() => handleQuickDemoSelect(MOCK_USERS[3])}
              className="px-3.5 py-1.5 rounded-lg bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/40 text-teal-300 font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-teal-400" />
              <span>1-Click Jury Demo</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Landing & Authentication Showcase */}
      <main className="flex-1 flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          
          {/* Left Column: Software Landing Showcase & Picture Depicting HR Performance (7 cols) */}
          <div className="lg:col-span-7 flex flex-col justify-between space-y-6">
            
            {/* Tagline Box: Highlighting Human Capital and Intellectual Capital */}
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-teal-300 font-medium shadow-inner">
                <Award className="w-3.5 h-3.5 text-teal-400" />
                <span>Human Capital & Intellectual Asset Intelligence</span>
                <span className="text-slate-600">•</span>
                <span className="text-slate-400">Abu Dhabi Financial District</span>
              </div>

              {/* Tagline depicting the core philosophy */}
              <h1 className="text-3xl sm:text-4xl lg:text-[40px] font-black text-white tracking-tight leading-[1.18]">
                Where <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 via-teal-200 to-blue-400">Human Talent</span> Meets <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-300 to-teal-300">Intellectual Capital</span>.
              </h1>

              <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-2xl">
                Capital is more than balance sheets — <strong className="text-white font-bold">Human Capital</strong> and <strong className="text-white font-bold">Intellectual Mastery</strong> are the true engines of organizational endurance. Paras Advisory HCM unites objective delivery analytics, statutory two-tier mentorship, and retentive loyalty multipliers in one unified enterprise architecture.
              </p>
            </div>

            {/* Generated High-Resolution Image Depicting HR Performance */}
            <div className="relative rounded-2xl overflow-hidden border border-slate-800 shadow-2xl group bg-slate-900">
              <img
                src="/src/assets/images/hr_performance_landing_1792331010173.jpg"
                alt="Workforce Performance and Intellectual Capital Analytics Showcase - Paras Advisory"
                referrerPolicy="no-referrer"
                className="w-full h-72 sm:h-80 md:h-[350px] object-cover object-center transform transition-transform duration-700 group-hover:scale-102"
              />
              
              {/* Overlay Vignette with Floating Enterprise Value Cards */}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent flex flex-col justify-end p-6">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="px-3 py-2 rounded-xl bg-slate-900/90 backdrop-blur-md border border-slate-700/80 shadow-lg text-xs">
                    <span className="text-[10px] text-teal-400 uppercase font-bold tracking-wider block">
                      Intellectual Asset Retention
                    </span>
                    <span className="text-sm font-extrabold text-white tabular-nums">
                      +15% Senior Merit Multiplier
                    </span>
                  </div>

                  <div className="px-3 py-2 rounded-xl bg-slate-900/90 backdrop-blur-md border border-slate-700/80 shadow-lg text-xs">
                    <span className="text-[10px] text-blue-400 uppercase font-bold tracking-wider block">
                      Workforce Performance SLA
                    </span>
                    <span className="text-sm font-extrabold text-white tabular-nums">
                      92.4% Real Turnaround
                    </span>
                  </div>

                  <div className="px-3 py-2 rounded-xl bg-slate-900/90 backdrop-blur-md border border-slate-700/80 shadow-lg text-xs">
                    <span className="text-[10px] text-emerald-400 uppercase font-bold tracking-wider block">
                      Chartered Bonus Incentives
                    </span>
                    <span className="text-sm font-extrabold text-white tabular-nums">
                      AED 15,000.00 / Cert
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Enterprise Software League Proof Bar (Oracle, SAP, Zoho, Tally Benchmark) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Enterprise Grade</div>
                <div className="text-slate-200 font-bold mt-0.5">SAP & Oracle Ready</div>
                <div className="text-[10px] text-slate-500 mt-0.5">HCM Data Architecture</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Sovereign Compliance</div>
                <div className="text-teal-300 font-bold mt-0.5">UAE Decree 33/2021</div>
                <div className="text-[10px] text-slate-500 mt-0.5">MOHRE & ADGM Law</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Audit Documentation</div>
                <div className="text-slate-200 font-bold mt-0.5">ISA 230 Compliant</div>
                <div className="text-[10px] text-slate-500 mt-0.5">SHA-256 Tamper-Proof</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Practice Scale</div>
                <div className="text-slate-200 font-bold mt-0.5">50 SME Specialists</div>
                <div className="text-[10px] text-slate-500 mt-0.5">AED 450K L&D Budget</div>
              </div>
            </div>

          </div>

          {/* Right Column: High-Grade Enterprise Login & Persona Switcher (5 cols) */}
          <div className="lg:col-span-5 flex flex-col justify-between bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
            <div>
              {/* Login Header */}
              <div className="pb-5 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white tracking-tight">
                    {isRegisterMode ? 'Register New Staff Profile' : 'Sign in to Enterprise HCM'}
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {isRegisterMode 
                      ? 'Create credentials compliant with corporate password policy'
                      : 'Access sovereign performance appraisals & governance'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsRegisterMode(!isRegisterMode);
                    setErrorMessage(null);
                  }}
                  className="text-xs font-semibold text-teal-400 hover:text-teal-300 transition-colors cursor-pointer"
                >
                  {isRegisterMode ? 'Sign In' : 'Register'}
                </button>
              </div>

              {/* Login Form */}
              <form onSubmit={handleLoginSubmit} className="mt-5 space-y-4 text-xs">
                {errorMessage && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                {/* Email / Username */}
                <div className="space-y-1.5">
                  <label className="font-semibold text-slate-300 block">
                    Corporate Email / Staff ID:
                  </label>
                  <div className="relative">
                    <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="e.g. zayed.dhaheri@paras-advisory.ae"
                      className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-700 bg-slate-800/80 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 text-xs font-sans"
                      required
                    />
                  </div>
                </div>

                {/* Password with Eye toggle */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="font-semibold text-slate-300 block">
                      Enterprise Password:
                    </label>
                    <span className="text-[11px] text-slate-400">Default: <code className="text-teal-300 font-mono">Audit@2026</code></span>
                  </div>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Minimum 8 characters with Capital & Symbol"
                      className="w-full pl-9 pr-10 py-2.5 rounded-xl border border-slate-700 bg-slate-800/80 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500 text-xs font-mono"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  {/* Password Security Policy Checklist */}
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/60 mt-2 space-y-1.5 text-[11px]">
                    <div className="font-bold text-slate-400 uppercase tracking-wider text-[10px]">
                      Enterprise Security Directive:
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className={`flex items-center gap-1.5 ${hasMinLength ? 'text-teal-400' : 'text-slate-500'}`}>
                        {hasMinLength ? <CheckCircle2 className="w-3.5 h-3.5" /> : <div className="w-3.5 h-3.5 rounded-full border border-slate-600" />}
                        <span>8+ Chars</span>
                      </div>
                      <div className={`flex items-center gap-1.5 ${hasUppercase ? 'text-teal-400' : 'text-slate-500'}`}>
                        {hasUppercase ? <CheckCircle2 className="w-3.5 h-3.5" /> : <div className="w-3.5 h-3.5 rounded-full border border-slate-600" />}
                        <span>1+ Capital</span>
                      </div>
                      <div className={`flex items-center gap-1.5 ${hasSpecialChar ? 'text-teal-400' : 'text-slate-500'}`}>
                        {hasSpecialChar ? <CheckCircle2 className="w-3.5 h-3.5" /> : <div className="w-3.5 h-3.5 rounded-full border border-slate-600" />}
                        <span>1+ Symbol</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Submit Sign In Button */}
                <button
                  type="submit"
                  disabled={!isPasswordValid}
                  className={`w-full py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md ${
                    isPasswordValid
                      ? 'bg-gradient-to-r from-teal-600 to-blue-700 hover:from-teal-500 hover:to-blue-600 text-white cursor-pointer'
                      : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                  }`}
                >
                  <span>{isRegisterMode ? 'Register & Enter Platform' : 'Sign In to Performance Suite'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            </div>

            {/* Jury & Evaluator 1-Click Role Exploration Box */}
            <div className="mt-6 pt-5 border-t border-slate-800">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center justify-between">
                <span>Select Persona to Explore Live System:</span>
                <span className="text-teal-400 font-semibold">1-Click Test</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-left">
                {/* Mansoor - Managing Partner */}
                <button
                  type="button"
                  onClick={() => handleQuickDemoSelect(MOCK_USERS[0])}
                  className="p-2.5 rounded-xl border border-slate-800 hover:border-blue-500/50 bg-slate-800/40 hover:bg-slate-800 transition-all text-xs text-left cursor-pointer group"
                >
                  <div className="font-bold text-white group-hover:text-blue-300 transition-colors truncate">
                    Mansoor Al Nuaimi
                  </div>
                  <div className="text-[10px] text-blue-400">Senior Managing Partner</div>
                  <div className="text-[9px] text-slate-400 mt-0.5">Firm governance & executive reviews</div>
                </button>

                {/* Mariam - HR Director */}
                <button
                  type="button"
                  onClick={() => handleQuickDemoSelect(MOCK_USERS[1])}
                  className="p-2.5 rounded-xl border border-slate-800 hover:border-teal-500/50 bg-slate-800/40 hover:bg-slate-800 transition-all text-xs text-left cursor-pointer group"
                >
                  <div className="font-bold text-white group-hover:text-teal-300 transition-colors truncate">
                    Mariam Al Shamsi
                  </div>
                  <div className="text-[10px] text-teal-400">Head of People & Governance</div>
                  <div className="text-[9px] text-slate-400 mt-0.5">AED 450k budget & legal notices</div>
                </button>

                {/* Tariq - Audit Partner / Manager */}
                <button
                  type="button"
                  onClick={() => handleQuickDemoSelect(MOCK_USERS[2])}
                  className="p-2.5 rounded-xl border border-slate-800 hover:border-indigo-500/50 bg-slate-800/40 hover:bg-slate-800 transition-all text-xs text-left cursor-pointer group"
                >
                  <div className="font-bold text-white group-hover:text-indigo-300 transition-colors truncate">
                    Tariq Al Hammadi
                  </div>
                  <div className="text-[10px] text-indigo-400">Audit Partner & Practice Lead</div>
                  <div className="text-[9px] text-slate-400 mt-0.5">Evaluates team, matrices & SLAs</div>
                </button>

                {/* Zayed - Senior Auditor */}
                <button
                  type="button"
                  onClick={() => handleQuickDemoSelect(MOCK_USERS[3])}
                  className="p-2.5 rounded-xl border border-slate-800 hover:border-emerald-500/50 bg-slate-800/40 hover:bg-slate-800 transition-all text-xs text-left cursor-pointer group"
                >
                  <div className="font-bold text-white group-hover:text-emerald-300 transition-colors truncate">
                    Zayed Al Dhaheri
                  </div>
                  <div className="text-[10px] text-emerald-400">Senior Audit Specialist</div>
                  <div className="text-[9px] text-slate-400 mt-0.5">AED 15k bonus & growth hub</div>
                </button>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-500" />
                  <span>256-Bit Encrypted Session</span>
                </span>
                <span>Abu Dhabi Global Market (ADGM)</span>
              </div>
            </div>

          </div>

        </div>
      </main>

      {/* Enterprise Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/60 py-4 px-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-300">Paras Accounting & Auditing Advisory</span>
            <span>•</span>
            <span>Licensed by ADGM & UAE Ministry of Human Resources and Emiratisation (MOHRE)</span>
          </div>
          <div className="text-slate-400">
            AICA Capstone Project Assessment • Standard SME Practice Edition (50 Staff)
          </div>
        </div>
      </footer>
    </div>
  );
};
