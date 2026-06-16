import { NavLink, Outlet } from 'react-router-dom';
import { CalendarDays, LayoutDashboard, Leaf, LogOut, MapPin, UserCircle } from 'lucide-react';

import { logoutUrl } from '../api/client';
import type { UserRead } from '../api/types';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/plants', label: 'Plants', icon: Leaf },
  { to: '/locations', label: 'Locations', icon: MapPin },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/profile', label: 'Profile', icon: UserCircle },
];

export function Layout({ user }: { user: UserRead }) {
  return (
    <div className="flex min-h-screen bg-stone-100 text-stone-800">
      <aside className="flex w-56 flex-col border-r border-stone-200 bg-white">
        <div className="flex items-center gap-2 px-5 py-5">
          <Leaf className="h-6 w-6 text-emerald-600" />
          <span className="text-lg font-semibold">Green Thumb</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? 'bg-emerald-50 text-emerald-700' : 'text-stone-600 hover:bg-stone-50'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-stone-200 px-5 py-4">
          <p className="truncate text-sm font-medium">{user.display_name}</p>
          <a
            href={logoutUrl()}
            className="mt-2 flex items-center gap-2 text-sm text-stone-500 hover:text-stone-800"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </a>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
