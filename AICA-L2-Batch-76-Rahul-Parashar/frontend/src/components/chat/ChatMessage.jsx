export default function ChatMessage({ role, content }) {
  const isUser = role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm font-body whitespace-pre-wrap ${
          isUser ? 'bg-verdigris text-paper' : 'bg-stone text-ink border border-line'
        }`}
      >
        {content}
      </div>
    </div>
  );
}
