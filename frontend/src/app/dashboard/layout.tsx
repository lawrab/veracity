import DashboardLayout from '@/components/DashboardLayout';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { Toaster } from 'react-hot-toast';

export default function Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <WebSocketProvider>
      <DashboardLayout>{children}</DashboardLayout>
      <Toaster />
    </WebSocketProvider>
  );
}