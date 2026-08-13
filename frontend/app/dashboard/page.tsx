import { CallAnalyticsDashboard } from '@/components/CallAnalyticsDashboard';

export const metadata = {
  title: 'Call Analytics Dashboard | Bharat Voice AI',
  description: 'Voice Agent Performance Dashboard — Real-time call analytics from SQLite',
};

export default function DashboardPage() {
  return (
    <main className="bg-background min-h-screen py-8">
      <CallAnalyticsDashboard />
    </main>
  );
}
