// Shown at sign-on until the user agrees to the current privacy notice. DPDP Act s.6(1): consent must be a clear
// affirmative action — so nothing is pre-ticked and the user taps "I agree". Using Vouchr requires it; AI is a separate,
// optional choice. A client admin also accepts the company's data-processing terms here (unless the CA firm already
// recorded them from the signed engagement letter).
import { useState } from 'react';
import { useStore } from '../data/store';
import type { Lang } from '../data/types';
import { CLIENT_TERMS, fillNotice } from '../data/privacyNotice';
import { useTr } from '../i18n';
import { clientConsent } from '../lib/consent';
import { fmtDate, setDateLocale, todayIso } from '../lib/dates';
import { useAttempt } from '../ui/common';
import { NoticeView, useNoticeVars } from '../ui/Notice';

export function ConsentGate() {
  const st = useStore();
  const { me, client, s } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const vars = useNoticeVars();
  const [lang, setLang] = useState<Lang>(s.lang);
  const [agree, setAgree] = useState(false);
  const [adult, setAdult] = useState(false);
  const [ai, setAi] = useState(false);
  const [terms, setTerms] = useState(false);
  const [companyAi, setCompanyAi] = useState(false);
  if (!me) return null;
  setDateLocale(lang); // the app shell (which normally sets this) is not shown yet
  const needTerms = me.role === 'client_admin' && !!me.clientId && clientConsent(s.consents, me.clientId, todayIso()).state === 'missing';
  const ready = agree && adult && (!needTerms || terms);

  return (
    <div className="consent-wrap">
      <div className="card pad stack consent-card">
        <div className="row between wrap">
          <b>{tr('Before you start')}</b>
          <div className="seg" role="radiogroup" aria-label={tr('Language')}>
            <button role="radio" aria-checked={lang === 'en'} className={lang === 'en' ? 'on' : ''} onClick={() => { setLang('en'); st.setLang('en'); }}>English</button>
            <button role="radio" aria-checked={lang === 'hi'} className={lang === 'hi' ? 'on' : ''} onClick={() => { setLang('hi'); st.setLang('hi'); }}>हिंदी</button>
          </div>
        </div>
        <NoticeView lang={lang} compact />
        {client?.engagementEndsOn && <div className="tiny muted">{tr('Valid until the engagement ends on {date}, unless you withdraw earlier.', { date: fmtDate(client.engagementEndsOn) })}</div>}

        <div className="stack" style={{ gap: 8 }}>
          <label className="row small consent-check"><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} /> <span className="req">{tr('I have read the privacy notice and agree to my personal data being processed as described, to use Vouchr.')}</span></label>
          <label className="row small consent-check"><input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} /> <span className="req">{tr('I am 18 years of age or older.')}</span></label>
          <label className="row small consent-check"><input type="checkbox" checked={ai} onChange={(e) => setAi(e.target.checked)} /> <span>{tr('Optional: I agree to AI assistance (Google Gemini) as described. I can switch it off any time.')}</span></label>
          {needTerms && (
            <div className="card pad stack" style={{ gap: 8, background: 'var(--surface-2)' }}>
              <b className="small">{tr('For your company')}</b>
              <label className="row small consent-check"><input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} /> <span className="req">{fillNotice(CLIENT_TERMS[lang], vars)}</span></label>
              <label className="row small consent-check"><input type="checkbox" checked={companyAi} onChange={(e) => setCompanyAi(e.target.checked)} /> <span>{tr('Optional: allow AI assistance for our company’s documents.')}</span></label>
            </div>
          )}
        </div>
        <div className="row wrap">
          <button className="btn" onClick={st.logout}>{tr('Decline and sign out')}</button>
          <button className="btn primary grow" disabled={!ready} onClick={() => attempt(() => st.giveConsent({ lang, ai, ageConfirmed: adult, clientTerms: needTerms ? { ai: companyAi } : undefined }))}>{tr('I agree')}</button>
        </div>
        <div className="tiny muted">{tr('You can withdraw consent or switch AI off at any time from “Privacy & consent”.')}</div>
      </div>
    </div>
  );
}

/** Company consent withdrawn or engagement ended — client users cannot continue. */
export function ConsentBlocked({ reason }: { reason: 'withdrawn' | 'expired' }) {
  const { logout, s } = useStore();
  const tr = useTr();
  return (
    <div className="consent-wrap">
      <div className="card pad stack consent-card">
        <h2>{reason === 'withdrawn' ? tr('Your company has withdrawn its consent') : tr('Your company’s engagement has ended')}</h2>
        <p className="small">{tr('Vouchr cannot be used for your company until this is renewed. Records the law requires are kept. Please contact {firm}.', { firm: s.firm.name })}</p>
        <button className="btn primary" onClick={logout}>{tr('Sign out')}</button>
      </div>
    </div>
  );
}
