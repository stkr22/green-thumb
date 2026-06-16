import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { loginUrl } from './api/client';
import { useMe } from './api/hooks/useProfile';
import { Layout } from './components/Layout';
import { CalendarPage } from './pages/CalendarPage';
import { DashboardPage } from './pages/DashboardPage';
import { LocationsPage } from './pages/LocationsPage';
import { PlantDetailPage } from './pages/PlantDetailPage';
import { PlantNewPage } from './pages/PlantNewPage';
import { PlantsPage } from './pages/PlantsPage';
import { ProfilePage } from './pages/ProfilePage';

export function App() {
  // Cookie-based auth: probe the session on load. The API client redirects to
  // /auth/login on 401, so an unauthenticated visit bounces through Zitadel.
  const { data: me, isLoading, isError } = useMe();

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-stone-500">Signing you in…</div>;
  }
  if (isError || !me) {
    // The 401 redirect normally fires first; this covers network errors.
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-stone-600">You need to sign in to manage your plants.</p>
        <a href={loginUrl()} className="btn-primary">
          Sign in
        </a>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout user={me} />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/plants" element={<PlantsPage />} />
          <Route path="/plants/new" element={<PlantNewPage />} />
          <Route path="/plants/:id" element={<PlantDetailPage />} />
          <Route path="/locations" element={<LocationsPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
