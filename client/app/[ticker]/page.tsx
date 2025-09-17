import { DashboardLayout } from '@/components/overnight-options/dashboard-layout';
import ErrorBoundary from '@/components/error-boundary';

interface TickerPageProps {
  params: Promise<{
    ticker: string;
  }>;
}

export default async function TickerPage({ params }: TickerPageProps) {
  const { ticker } = await params;

  return (
    <ErrorBoundary>
      <DashboardLayout initialTicker={ticker.toUpperCase()} />
    </ErrorBoundary>
  );
}