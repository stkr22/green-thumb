import { Suspense } from 'react';
import { NavLink, Outlet, useNavigation } from 'react-router';
import { CalendarDays, LayoutDashboard, Leaf, LogOut, MapPin, Sprout, UserCircle } from 'lucide-react';

import { logoutUrl } from '../api/client';
import { useMe } from '../api/hooks/useProfile';
import { PageSkeleton } from './Skeleton';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/plants', label: 'Plants', icon: Leaf },
  { to: '/species', label: 'Species', icon: Sprout },
  { to: '/locations', label: 'Locations', icon: MapPin },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/profile', label: 'Profile', icon: UserCircle },
];

export function Layout() {
  // App renders the router only after this query succeeded, so it's cached.
  const { data: user } = useMe();
  // Lazy route chunks load before the new page renders; show that something
  // is happening instead of a seemingly ignored click.
  const navigating = useNavigation().state === 'loading';

  return (
    // min-h-dvh, not min-h-screen: on phones 100vh is the height with the
    // browser toolbar hidden, so the page overflowed the visible area and the
    // fixed bottom nav jumped around as the toolbar slid in and out.
    <div className="flex min-h-dvh flex-col bg-stone-100 text-stone-800 md:flex-row">
      {navigating && (
        <div role="progressbar" aria-label="Loading page" className="fixed inset-x-0 top-0 z-50 h-0.5 animate-pulse bg-emerald-500" />
      )}
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
          <p className="truncate text-sm font-medium">{user?.display_name}</p>
          <a
            href={logoutUrl()}
            className="mt-2 flex items-center gap-2 text-sm text-stone-500 hover:text-stone-800"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </a>
        </div>
      </aside>

      {/* The document is the only scroll container (a nested one confuses mobile
          browsers' handling of fixed elements). The bottom padding keeps content
          clear of the fixed nav, including its safe-area padding. */}
      <main className="flex-1 p-4 pb-[calc(5rem+env(safe-area-inset-bottom))] md:p-8 md:pb-8">
        {/* Loaders have usually filled the cache, so this rarely shows; it
            catches a page suspending on data its loader didn't await. */}
        <Suspense fallback={<PageSkeleton />}>
          <Outlet />
        </Suspense>
      </main>

      {/* Mobile bottom nav: thumb-reachable tab bar standing in for the sidebar. */}
      {/* Padded by the safe-area inset so tabs clear the iPhone home indicator. */}
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-10 flex border-t border-stone-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden"
      >
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
