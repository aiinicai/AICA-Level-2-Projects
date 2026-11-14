import { Link } from 'react-router-dom';
import { useTr } from '../i18n';
import { useStore } from '../data/store';
import { useAdminSections } from '../ui/Shell';
import { Icon } from '../ui/Icon';
import { PageHead } from '../ui/common';
import { LanguageSwitch } from '../ui/LanguageSwitch';

/** Mobile home for every admin screen that does not fit in the bottom bar. */
export function More() {
  const tr = useTr();
  const { client, me } = useStore();
  const { sections } = useAdminSections();
  return (
    <div className="content narrow stack">
      <PageHead title={tr('More')} sub={me?.role === 'super_admin' ? `${tr('Client')}: ${client?.name}` : client?.name} />
      {sections.map((sec, i) => (
        <div key={i} className="card">
          {sec.title && <div className="card-head"><h3>{tr(sec.title)}</h3></div>}
          <div className="list">
            {sec.items.map((n) => (
              <Link key={n.to} to={n.to} className="list-item">
                <Icon name={n.icon} size={18} />
                <span className="grow">{tr(n.label)}</span>
                {n.count ? <span className="nav-count">{n.count}</span> : null}
                <Icon name="chevron" size={16} />
              </Link>
            ))}
          </div>
        </div>
      ))}
      <LanguageSwitch />
    </div>
  );
}
