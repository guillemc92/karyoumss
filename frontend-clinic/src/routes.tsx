import { Navigate, Route, Routes } from 'react-router-dom';
import { SampleListPage } from './clinic/pages/SampleListPage';
import { SampleFormPage } from './clinic/pages/SampleFormPage';
import { SampleDetailPage } from './clinic/pages/SampleDetailPage';
import { SampleRegisterPage } from './clinic/pages/SampleRegisterPage';
import { DegradedModePage } from './clinic/pages/DegradedModePage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/clinic/samples" replace />} />
      <Route path="/clinic/samples" element={<SampleListPage />} />
      <Route path="/clinic/samples/register" element={<SampleRegisterPage />} />
      <Route path="/clinic/samples/new" element={<SampleFormPage />} />
      <Route path="/clinic/samples/:id" element={<SampleDetailPage />} />
      <Route path="/clinic/samples/:id/edit" element={<SampleFormPage />} />
      <Route path="/clinic/degraded" element={<DegradedModePage />} />
    </Routes>
  );
}
