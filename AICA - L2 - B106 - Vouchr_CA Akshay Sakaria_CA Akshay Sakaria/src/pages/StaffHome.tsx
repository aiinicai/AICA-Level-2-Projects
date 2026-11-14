import { Link, useNavigate } from 'react-router-dom';
import { useStore } from '../data/store';
import { useT } from '../i18n';
import { outstanding } from '../lib/alerts';
import { fmtDate } from '../lib/dates';
import { fmtInr } from '../lib/money';
import { Icon } from '../ui/Icon';
import { Empty, StatusBadge } from '../ui/common';
import { ReceiptArt } from '../ui/Art';
import { useTr } from '../i18n';
import { LanguageSwitch } from '../ui/LanguageSwitch';

export function StaffHome() {
  const { me, scoped } = useStore();
  const t = useT();
  const nav = useNavigate();
  const tr = useTr();
  const mine = scoped.expenses.filter((e) => e.createdBy === me?.id).slice(0, 6);
  const returned = scoped.expenses.filter((e) => e.createdBy === me?.id && e.status === 'rejected');
  const dueCount = scoped.expenses.filter((e) => e.status !== 'rejected' && outstanding(e, scoped.payments) > 0).length;

  return (
    <div className="content narrow stack lg">
      <div>
        <div className="muted small">{t('hello')},</div>
        <h1>{me?.name.split(' ')[0]} 👋</h1>
      </div>

      {returned.length > 0 && (
        <Link to={`/capture?edit=${returned[0].id}`} className="banner danger" style={{ textDecoration: 'none' }}>
          <Icon name="alert" size={18} />
          <span className="grow"><b>{returned.length} × {t('status_rejected')}</b> — {returned[0].vendorName}: {returned[0].reviewNote}</span>
          <b>{t('fixResubmit')} →</b>
        </Link>
      )}

      <button className="hero-snap" onClick={() => nav('/capture?mode=photo')}>
        <div className="hero-copy">
          <b>{t('snap')}</b>
          <span>{t('snapHint')}</span>
          <span className="hero-cta"><Icon name="camera" size={18} /> {tr('Open camera')}</span>
        </div>
        <div className="hero-art" aria-hidden="true"><ReceiptArt /><div className="scanline" /></div>
      </button>

      <div className="alt-actions">
        <button className="btn lg" onClick={() => nav('/capture?mode=file')}><Icon name="upload" /> {t('uploadFile')}</button>
        <button className="btn lg" onClick={() => nav('/capture?mode=manual')}><Icon name="pen" /> {t('typeIt')}</button>
      </div>

      {dueCount > 0 && (
        <Link to="/dues" className="card pad row">
          <div className="avatar" style={{ background: 'var(--warn-soft)', color: 'var(--warn)', border: 'none' }}><Icon name="wallet" /></div>
          <div className="grow"><b>{dueCount}</b> <span className="muted">{t('dues')}</span></div>
          <Icon name="chevron" />
        </Link>
      )}

      <div className="card">
        <div className="card-head"><h2>{t('recent')}</h2><Link to="/entries" className="linkish small">{t('entries')} →</Link></div>
        {mine.length === 0 ? <Empty art="tray">{t('noEntries')}</Empty> : (
          <div className="list">
            {mine.map((e) => (
              <Link key={e.id} to={e.status === 'rejected' ? `/capture?edit=${e.id}` : '/entries'} className="list-item">
                {e.imageDataUrl ? <img className="photo-thumb" style={{ width: 40, height: 52 }} src={e.imageDataUrl} alt="" /> : <div className="avatar"><Icon name="list" size={18} /></div>}
                <div className="grow">
                  <div className="ellipsis" style={{ fontWeight: 600 }}>{e.vendorName}</div>
                  <div className="muted tiny">{fmtDate(e.invoiceDate)}{e.invoiceNo ? ` · #${e.invoiceNo}` : ''}</div>
                </div>
                <div className="right">
                  <div className="num" style={{ fontWeight: 650 }}>{fmtInr(e.totalAmount)}</div>
                  <StatusBadge status={e.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
      <LanguageSwitch />
    </div>
  );
}
