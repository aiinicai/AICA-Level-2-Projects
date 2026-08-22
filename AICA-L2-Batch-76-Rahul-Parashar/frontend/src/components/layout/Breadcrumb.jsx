import { Link, useLocation } from 'react-router-dom';
import { breadcrumbTrail } from '../../routes';

export default function Breadcrumb() {
  const location = useLocation();
  const trail = breadcrumbTrail(location.pathname);

  return (
    <nav aria-label="Breadcrumb" className="flex items-center flex-wrap gap-x-1 font-body text-sm">
      {trail.map((item, i) => {
        const isLast = i === trail.length - 1;
        return (
          <span key={item.path} className="flex items-center">
            {i > 0 && <span className="text-mist mx-1">›</span>}
            {isLast ? (
              <span className="text-ink font-medium border-b-[3px] border-verdigris pb-0.5">{item.label}</span>
            ) : (
              <Link to={item.path} className="text-slate hover:text-verdigris">
                {item.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
