import { Route, Routes } from 'react-router';

import { DashboardPage } from '../features/dashboard/DashboardPage';
import { MainLayout } from '../layouts/MainLayout';

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
