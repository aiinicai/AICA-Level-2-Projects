import { useState } from 'react';
import { useStore } from '../data/store';
import { NoticeView } from '../ui/Notice';
import { useTr } from '../i18n';
import { BRAND } from '../brand';
import { Initials } from '../ui/common';
import { Icon } from '../ui/Icon';

const ROLE_LABEL = { super_admin: 'Super admin · CA firm', client_admin: 'Client admin', sub_user: 'Staff (sub-user)' };

// What the product actually does — shown as a slow capability strip (pauses on hover, static for reduced motion)
const CAPABILITIES = ['Snap a bill', 'e-Invoice QR', 'GST split', 'TDS u/s 393', 'RCM', 'Blocked credit 17(5)', 'UPI & bank payments', 'GSTR-2B reco', 'Tally XML', 'Google Drive filing', 'Hindi & English'];

export function Login() {
  const tr = useTr();
  const { s, login } = useStore();
  const [notice, setNotice] = useState(false);
  return (
    <div className="login">
      <section className="auth-story" aria-label={BRAND.name}>
        <div className="mini-brand" style={{ display: 'flex' }}>
          <img src="/icon.svg" alt="" width={44} height={44} style={{ borderRadius: 12, boxShadow: 'var(--sh-glow)' }} />
          <div><b style={{ fontFamily: 'var(--font-display)', fontSize: 20, letterSpacing: '-.02em' }}>{BRAND.name}</b><div className="eyebrow">{tr('For CA firms & their clients')}</div></div>
        </div>
        <h1 className="display">{tr('Every bill,')} <span className="grad-text">{tr('booked right.')}</span></h1>
        <p>{tr('Staff snap the bill. Vouchr reads it, works out GST, TDS and RCM, files it in Google Drive and gets it ready for Tally — your CA team just checks.')}</p>

        {/* product scene: a bill becoming a checked ledger entry (illustrative, built from the app's own UI) */}
        <div className="scene" aria-hidden="true">
          <div className="scene-card scene-bill">
            <div className="row between"><b className="small">Paper House</b><span className="badge ok">QR</span></div>
            <div className="scene-line" style={{ width: '70%' }} /><div className="scene-line" style={{ width: '90%' }} /><div className="scene-line" style={{ width: '55%' }} />
            <div className="scene-row"><span className="muted">{tr('Bill total')}</span><b className="num">₹1,180.00</b></div>
          </div>
          <div className="scene-card scene-ledger">
            <div className="row between"><b className="small">{tr('Ready for Tally')}</b><span className="badge ok">{tr('Checked')}</span></div>
            <div className="scene-row"><span>{tr('Printing & Stationery')}</span><span className="num">₹1,000.00</span></div>
            <div className="scene-row"><span>CGST 9% + SGST 9%</span><span className="num">₹180.00</span></div>
            <div className="scene-row"><span>TDS</span><span className="muted">{tr('Not applicable')}</span></div>
            <div className="scene-row"><span>📁 FY 2026-27 / Bills</span><span className="badge brand">Drive</span></div>
          </div>
        </div>

        <div className="marquee" aria-hidden="true">
          <div className="marquee-track">
            {[...CAPABILITIES, ...CAPABILITIES].map((c, i) => <span key={i} className="chip"><Icon name="check" size={14} /> {tr(c)}</span>)}
          </div>
        </div>
      </section>

      <div className="card login-card stack lg">
        <div className="row mini-brand">
          <img src="/icon.svg" alt="" width={44} height={44} style={{ borderRadius: 12 }} />
          <div>
            <h1>{BRAND.name}</h1>
            <div className="muted small">{BRAND.tagline}</div>
          </div>
        </div>
        <div>
          <h2 style={{ fontSize: 22 }}>{tr('Sign in')}</h2>
          <div className="muted small" style={{ marginTop: 4 }}>{tr('Choose who you are to continue.')}</div>
        </div>
        <div className="banner info">
          <Icon name="info" size={18} />
          <span>{tr('Demo mode — pick a role to explore. Real sign-in (email OTP via Supabase Auth) replaces this screen once the backend is connected.')}</span>
        </div>
        <div className="stack" style={{ gap: 10 }}>
          {s.users.filter((u) => u.active !== false).map((u) => {
            const c = s.clients.find((x) => x.id === u.clientId);
            return (
              <button key={u.id} className="role-btn" onClick={() => login(u.id)}>
                <Initials name={u.name} />
                <div className="grow">
                  <div style={{ fontWeight: 680 }}>{u.name}</div>
                  <div className="muted small">{tr(ROLE_LABEL[u.role])}{c ? ` · ${c.name}` : ''}</div>
                </div>
                <Icon name="chevron" size={18} />
              </button>
            );
          })}
        </div>
        <div className="dpdp-note" role="note"><Icon name="shield" size={14} /><span>{tr('Your data is handled under the Digital Personal Data Protection Act, 2023. You will be asked to read and agree to our privacy notice before first use.')} <button className="linkish" onClick={() => setNotice(!notice)}>{notice ? tr('Hide notice') : tr('Read the privacy notice')}</button></span></div>
        {notice && <NoticeView lang={s.lang} compact />}
      </div>
    </div>
  );
}
