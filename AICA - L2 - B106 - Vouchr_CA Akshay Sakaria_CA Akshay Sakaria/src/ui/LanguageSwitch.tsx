// U7 — a labelled language choice (besides the small अ/A header button), on More and on the staff home.
import { useStore } from '../data/store';
import { useTr } from '../i18n';

export function LanguageSwitch() {
  const st = useStore();
  const tr = useTr();
  const lang = st.s.lang;
  return (
    <div className="card pad row between wrap">
      <span id="lang-label" className="small"><b>{tr('Language')}</b> · भाषा</span>
      <div className="seg" role="radiogroup" aria-labelledby="lang-label">
        <button role="radio" aria-checked={lang === 'en'} className={lang === 'en' ? 'on' : ''} onClick={() => st.setLang('en')}>English</button>
        <button role="radio" aria-checked={lang === 'hi'} className={lang === 'hi' ? 'on' : ''} onClick={() => st.setLang('hi')}>हिंदी</button>
      </div>
    </div>
  );
}
