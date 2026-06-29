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
    <div className="flex min-h-screen flex-col bg-stone-100 text-stone-800 md:flex-row">
      {/* Mobile top bar: the sidebar is hidden on phones, so brand + sign-out live here. */}
      <header className="flex items-center justify-between border-b border-stone-200 bg-white px-4 py-3 md:hidden">
        <div className="flex items-center gap-2">
          <Leaf className="h-6 w-6 text-emerald-600" />
          <span className="text-lg font-semibold">Green Thumb</span>
        </div>
        <a
          href={logoutUrl()}
          aria-label="Sign out"
          className="flex items-center gap-1 text-sm text-stone-500 hover:text-stone-800"
        >
          <LogOut className="h-5 w-5" />
        </a>
      </header>

      {/* Desktop sidebar. */}
      <aside className="hidden w-56 flex-col border-r border-stone-200 bg-white md:flex">
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

      {/* pb-20 keeps content clear of the fixed mobile bottom nav. */}
      <main className="flex-1 overflow-y-auto p-4 pb-20 md:p-8 md:pb-8">
        <Outlet />
      </main>

      {/* Mobile bottom nav: thumb-reachable tab bar standing in for the sidebar. */}
      <nav className="fixed inset-x-0 bottom-0 z-10 flex border-t border-stone-200 bg-white md:hidden">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-1 py-2 text-xs font-medium ${
                isActive ? 'text-emerald-700' : 'text-stone-500'
              }`
            }
          >
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
