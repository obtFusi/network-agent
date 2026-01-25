import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PipelineList } from '@/components/PipelineList';
import { PipelineDetail } from '@/components/PipelineDetail';
import { ApprovalQueue } from '@/components/ApprovalQueue';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<PipelineList />} />
          <Route path="pipelines/:id" element={<PipelineDetail />} />
          <Route path="approvals" element={<ApprovalQueue />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
