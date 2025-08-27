import { DashboardLayout } from '@/components/overnight-options/dashboard-layout';
import ErrorBoundary from '@/components/error-boundary';

export default function Dashboard() {
  return (
    <ErrorBoundary>
      <DashboardLayout />
    </ErrorBoundary>
  );
}