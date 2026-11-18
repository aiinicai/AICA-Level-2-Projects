import { Link, useSearchParams } from 'react-router-dom';
import { can, useApp } from '../state';
import { AppIcon } from '../components/icons';
import { filterQuery, visibleGroups } from '../components/nav';
import { Empty } from '../components/ui';
import { TallySyncCard } from '../components/TallySync';

/** Good morning / afternoon / evening, by the time in India. */
function greeting() {
  const hour = Number(new Intl.DateTimeFormat('en-IN', { hour: 'numeric', hour12: false, timeZone: 'Asia/Kolkata' }).format(new Date()));
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
}

/** The Tally MIS home, as its own launcher: one tile per page, grouped. */
export function HomePage() {
  const { user, company, demoMode } = useApp();
  const qs = filterQuery(useSearchParams()[0]);
  return (
    <div className="launch">
      <div className="hello">
        <h1>{greeting()}</h1>
        <p>{company ? `Choose what to look at for ${company.name}.` : 'Sync a company from Tally to get started.'}</p>
      </div>
      {!company && (can(user, 'analyst') ? <TallySyncCard /> : <Empty>No company has been synced in this session yet. Ask an administrator to sync one.</Empty>)}
      <div className="grps">
      {visibleGroups(user, demoMode).map((g) => (
        <section key={g.key} className="grp" aria-labelledby={`grp-${g.key}`}>
          <h2 id={`grp-${g.key}`}>{g.label}</h2>
          <ul className="tiles">
            {g.items.map((n) => (
              <li key={n.to}>
                <Link className="tile" to={`${n.to}${qs}`}>
                  <span className="ic"><AppIcon name={n.icon} /></span>
                  <span className="lab">{n.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
      </div>
    </div>
  );
}
