// Short DPDP Act 2023 notices at the points where personal data enters or leaves Vouchr. Each links to "Privacy & consent".
import { Link } from 'react-router-dom';
import { useStore } from '../data/store';
import { useTr } from '../i18n';
import { Icon } from './Icon';
import { useAiStatus } from '../lib/ai';

export const DPDP_NOTES = {
  bills: 'Bills can contain personal data (names, PAN, phone numbers). Upload only business bills — they are used only for accounting and tax, as set out in our privacy notice.',
  voice: 'Your recording is sent to Google Gemini only to fill this form; Vouchr does not keep the audio.',
  import: 'Upload only data your company is entitled to share. Personal data in it is handled as set out in our privacy notice (DPDP Act 2023).',
  ai: 'AI: only the data needed for this task is sent to Google Gemini (paid service), and only with your consent.',
  export: 'This file contains personal data (vendor names, PAN). Share it only with people who need it and delete copies you no longer need.',
  users: 'The new person will see the privacy notice and must agree at their first sign-in.',
  vendor: 'For individual vendors, name, PAN and phone number are personal data — record only what tax compliance needs.'
} as const;

export function DpdpNote({ kind }: { kind: keyof typeof DPDP_NOTES }) {
  const tr = useTr();
  const { me } = useStore();
  return (
    <>
    {kind === 'ai' && <FreeTierWarning />}
    <div className="dpdp-note" role="note">
      <Icon name="shield" size={14} />
      <span>{tr(DPDP_NOTES[kind])}{me && <> <Link to="/privacy" className="linkish">{tr('Privacy & consent')}</Link></>}</span>
    </div>
    </>
  );
}

/** Gemini free tier: Google may use what is sent to improve its products — so dummy data only. */
function FreeTierWarning() {
  const tr = useTr();
  const ai = useAiStatus();
  if (!ai.freeTier) return null;
  return <div className="banner warn small" role="alert"><Icon name="alert" size={16} /><span><b>{tr('Gemini FREE tier — test with dummy data only.')}</b> {tr('Google may use what is sent on the free tier to improve its products. Never use real client bills until billing is switched on.')}</span></div>;
}
