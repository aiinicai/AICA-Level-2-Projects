import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import TopBar from './TopBar';
import SectionNav from './SectionNav';
import ChatWidget from '../chat/ChatWidget';

export default function AppShell() {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="min-h-screen bg-stone">
      <TopBar onOpenChat={() => setChatOpen(true)} />
      <SectionNav />
      <main>
        <Outlet />
      </main>
      <ChatWidget open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
