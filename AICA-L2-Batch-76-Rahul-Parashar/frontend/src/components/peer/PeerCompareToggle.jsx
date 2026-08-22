import { useState } from 'react';
import { Users } from 'lucide-react';
import { useFinancials } from '../../context/FinancialsContext';
import PeerUploadPanel from './PeerUploadPanel';

export default function PeerCompareToggle() {
  const [open, setOpen] = useState(false);
  const { peer } = useFinancials();

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={`flex items-center gap-1.5 text-xs sm:text-sm font-body px-2.5 py-1.5 rounded-lg border focus:outline-none focus:ring-2 focus:ring-verdigris ${
          peer ? 'border-verdigris text-verdigris' : 'border-graphite text-mist hover:text-paper'
        }`}
      >
        <Users size={14} />
        <span className="hidden sm:inline">{peer ? `vs ${peer.name}` : 'Compare peer'}</span>
      </button>
      {open && <PeerUploadPanel onClose={() => setOpen(false)} />}
    </>
  );
}
