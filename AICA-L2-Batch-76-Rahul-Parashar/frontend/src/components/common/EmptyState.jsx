import { FileWarning } from 'lucide-react';

export default function EmptyState({ message = 'Data not available.' }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6 bg-paper rounded-lg border border-line">
      <FileWarning size={28} className="text-mist mb-3" />
      <p className="font-body text-slate text-sm max-w-md">{message}</p>
    </div>
  );
}
