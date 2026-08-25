import { Link } from 'react-router-dom';
import { MessageSquareText, RotateCcw } from 'lucide-react';
import { useFinancials } from '../../context/FinancialsContext';
import PeerCompareToggle from '../peer/PeerCompareToggle';

export default function TopBar({ onOpenChat }) {
  const { financials, displayUnit, setDisplayUnit, resetFile } = useFinancials();

  return (
    <header className="bg-ink text-paper sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        <Link to="/" className="font-heading font-semibold tracking-tight text-paper hover:text-verdigris">
          {financials?.company || 'CFO Dashboard'}
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <div className="hidden sm:flex items-center rounded-lg overflow-hidden border border-graphite text-xs font-mono-figures">
            {['L', 'Cr'].map((u) => (
              <button
                key={u}
                onClick={() => setDisplayUnit(u)}
                className={`px-2.5 py-1.5 ${displayUnit === u ? 'bg-verdigris text-paper' : 'bg-graphite text-mist hover:text-paper'}`}
              >
                {u === 'L' ? '₹ Lakhs' : '₹ Crore'}
              </button>
            ))}
          </div>

          <PeerCompareToggle />

          <button
            onClick={resetFile}
            className="flex items-center gap-1.5 text-xs sm:text-sm font-body text-mist hover:text-paper px-2 py-1.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-verdigris"
            title="Load a different workbook"
          >
            <RotateCcw size={14} />
            <span className="hidden sm:inline">Change file</span>
          </button>

          <button
            onClick={onOpenChat}
            className="flex items-center gap-1.5 text-xs sm:text-sm font-body bg-verdigris text-paper px-3 py-1.5 rounded-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-verdigris focus:ring-offset-2 focus:ring-offset-ink"
          >
            <MessageSquareText size={14} />
            Ask CFO Copilot
          </button>
        </div>
      </div>
    </header>
  );
}
