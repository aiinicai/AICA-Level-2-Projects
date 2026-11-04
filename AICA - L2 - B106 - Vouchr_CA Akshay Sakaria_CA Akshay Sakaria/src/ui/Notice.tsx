// The privacy notice (DPDP Rules r.3), filled with the firm, client and contact. Used at sign-on, from the login page and in Privacy.
import { useStore } from '../data/store';
import { fillNotice, NOTICE } from '../data/privacyNotice';
import type { Lang } from '../data/types';
import { NOTICE_VERSION } from '../lib/consent';

export function useNoticeVars() {
  const { s, client } = useStore();
  const f = s.firm;
  const contact = [f.privacyContactName, f.privacyEmail, f.privacyPhone].filter(Boolean).join(', ');
  return {
    firm: f.name,
    client: client?.name ?? (s.lang === 'hi' ? 'उसके क्लाइंट' : 'its clients'),
    contact: contact || (s.lang === 'hi' ? `${f.name} (संपर्क विवरण फ़र्म जोड़ेगी)` : `${f.name} (contact details to be added by the firm)`),
    contactMissing: !contact
  };
}

export function NoticeView({ lang, compact }: { lang: Lang; compact?: boolean }) {
  const v = useNoticeVars();
  const n = NOTICE[lang];
  return (
    <div className="notice stack" style={{ gap: 10, maxHeight: compact ? 340 : undefined, overflowY: compact ? 'auto' : undefined }} tabIndex={0} aria-label={n.heading}>
      <h2>{n.heading}</h2>
      <p className="small" style={{ margin: 0 }}>{fillNotice(n.intro, v)}</p>
      {n.sections.map((sec) => (
        <section key={sec.title}>
          <h3>{sec.title}</h3>
          <ul className="small" style={{ margin: '4px 0 0', paddingLeft: 18 }}>{sec.points.map((p) => <li key={p}>{fillNotice(p, v)}</li>)}</ul>
        </section>
      ))}
      <div className="tiny muted">Notice version {NOTICE_VERSION} · Digital Personal Data Protection Act, 2023</div>
    </div>
  );
}
