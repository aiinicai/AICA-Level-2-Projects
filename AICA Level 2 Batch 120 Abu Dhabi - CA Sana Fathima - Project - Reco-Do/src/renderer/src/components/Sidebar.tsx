import { useId } from 'react'
import { NavLink } from 'react-router-dom'
import { MODULES } from '@shared/modules'
import { TOOLS } from '@shared/tools'
import { WORKSPACE } from '@/pages/workspace/sections'
import { cn } from '@/lib/cn'
import { useAppInfo } from '@/lib/appInfo'

function Item({ to, children, end }: { to: string; children: React.ReactNode; end?: boolean }): React.JSX.Element {
  return (
    <li>
      <NavLink
        to={to}
        end={end}
        className={({ isActive }) =>
          cn(
            'mb-0.5 flex items-center justify-between gap-2 rounded-md px-2.5 py-[7px] text-[13.5px] short:py-[5px] min-[1200px]:px-3 text-[#DCE5EF] outline-none hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-teal/70',
            isActive && 'bg-navy-2 font-semibold text-white hover:bg-navy-2'
          )
        }
      >
        {children}
      </NavLink>
    </li>
  )
}

function Group({ title, children }: { title: string; children: React.ReactNode }): React.JSX.Element {
  const id = useId()
  return (
    <div role="group" aria-labelledby={id}>
      <div id={id} className="px-2.5 pt-4 pb-1.5 text-[11px] short:pt-3 short:pb-1 min-[1200px]:px-3 tracking-[1.6px] text-[#8FA3B8]">
        {title}
      </div>
      <ul>{children}</ul>
    </div>
  )
}

export function Sidebar(): React.JSX.Element {
  const info = useAppInfo()
  return (
    <aside className="flex w-[212px] flex-none flex-col overflow-y-auto bg-navy px-3 py-5 short:py-4 min-[1200px]:w-[230px] min-[1200px]:px-4">
      <div className="pb-5 short:pb-3 text-[22px] font-extrabold tracking-tight text-white" aria-label="Reco-Do">
        Reco-<span className="text-teal">Do</span>
      </div>
      <nav aria-label="Main">
        <ul>
          <Item to="/" end>
            Dashboard
          </Item>
        </ul>
        <Group title="MODULES">
          {MODULES.map((m) => (
            <Item key={m.id} to={`/module/${m.id}`}>
              {m.name}
              {m.status === 'phase2' && (
                <span className="rounded border border-[#6B5A2E] px-1.5 text-[9.5px] font-semibold text-[#F2C66D]">
                  P2<span className="sr-only"> (coming in Phase 2)</span>
                </span>
              )}
            </Item>
          ))}
        </Group>
        <Group title="TOOLS">
          {TOOLS.map((t) => (
            <Item key={t.id} to={`/tools/${t.id}`}>
              {t.name}
            </Item>
          ))}
        </Group>
        <Group title="WORKSPACE">
          {WORKSPACE.map((w) => (
            <Item key={w.id} to={`/workspace/${w.id}`}>
              {w.name}
            </Item>
          ))}
        </Group>
      </nav>
      <div className="mt-auto px-2.5 pt-5 text-[11px] text-[#8FA3B8] short:pt-3 min-[1200px]:px-3">{info ? `Reco-Do v${info.version}` : ' '}</div>
    </aside>
  )
}
