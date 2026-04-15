import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Stethoscope,
  HeartPulse,
  Route as RouteIcon,
  Settings,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}

const NAV: NavItem[] = [
  { to: '/', label: 'Tableau de bord', icon: LayoutDashboard },
  { to: '/routes', label: 'Tournées', icon: RouteIcon },
  { to: '/patients', label: 'Patients', icon: Users },
  { to: '/caregivers', label: 'Soignants', icon: Stethoscope },
  { to: '/pathologies', label: 'Pathologies', icon: HeartPulse },
  { to: '/settings', label: 'Paramètres', icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-card px-3 py-5">
      <div className="flex items-center gap-2 px-3 pb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-soft">
          <Activity className="h-5 w-5" aria-hidden />
        </div>
        <div className="flex flex-col">
          <span className="text-base font-semibold tracking-tight">ICY</span>
          <span className="text-xs text-muted-foreground">Tournées santé</span>
        </div>
      </div>
      <nav aria-label="Navigation principale" className="flex flex-1 flex-col gap-1">
        {NAV.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary-700'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )
              }
            >
              <Icon className="h-5 w-5" aria-hidden />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="mt-4 rounded-xl bg-muted/60 p-3 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">Version MVP</p>
        <p className="mt-0.5">Données fictives uniquement.</p>
      </div>
    </aside>
  );
}
