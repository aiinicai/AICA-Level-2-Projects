export type Quote = { text: string; author: string };

export const QUOTES: Quote[] = [
  { text: "Quality is never an accident; it is always the result of intelligent effort.", author: "John Ruskin" },
  { text: "What gets measured gets managed.", author: "Peter Drucker" },
  { text: "The secret of getting ahead is getting started.", author: "Mark Twain" },
  { text: "Integrity is doing the right thing, even when no one is watching.", author: "C.S. Lewis" },
  { text: "Small daily improvements are the key to staggering long-term results.", author: "Robin Sharma" },
  { text: "It always seems impossible until it's done.", author: "Nelson Mandela" },
  { text: "Without data, you're just another person with an opinion.", author: "W. Edwards Deming" },
  { text: "Discipline is the bridge between goals and accomplishment.", author: "Jim Rohn" },
  { text: "Trust, but verify.", author: "Russian proverb" },
  { text: "If you want to go fast, go alone. If you want to go far, go together.", author: "African proverb" },
  { text: "Excellence is not an act, but a habit.", author: "Will Durant" },
  { text: "The best way to predict the future is to create it.", author: "Peter Drucker" },
  { text: "Price is what you pay. Value is what you get.", author: "Warren Buffett" },
  { text: "Do the hard jobs first. The easy jobs will take care of themselves.", author: "Dale Carnegie" },
  { text: "A goal without a plan is just a wish.", author: "Antoine de Saint-Exupéry" },
  { text: "Learning never exhausts the mind.", author: "Leonardo da Vinci" },
  { text: "Efficiency is doing things right; effectiveness is doing the right things.", author: "Peter Drucker" },
  { text: "Success is the sum of small efforts, repeated day in and day out.", author: "Robert Collier" },
  { text: "The expert in anything was once a beginner.", author: "Helen Hayes" },
  { text: "Transparency is the currency of trust.", author: "Unknown" },
  { text: "Act as if what you do makes a difference. It does.", author: "William James" },
  { text: "Opportunities don't happen. You create them.", author: "Chris Grosser" },
  { text: "Well done is better than well said.", author: "Benjamin Franklin" },
  { text: "Believe you can and you're halfway there.", author: "Theodore Roosevelt" },
  { text: "Great things are done by a series of small things brought together.", author: "Vincent van Gogh" },
  { text: "Accountability breeds response-ability.", author: "Stephen Covey" },
  { text: "Continuous improvement is better than delayed perfection.", author: "Mark Twain" },
  { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
  { text: "Plans are nothing; planning is everything.", author: "Dwight D. Eisenhower" },
  { text: "Change is the end result of all true learning.", author: "Leo Buscaglia" },
  { text: "Start where you are. Use what you have. Do what you can.", author: "Arthur Ashe" },
];

/** Same quote for everyone on a given calendar day; changes at midnight. */
export function quoteForDate(date: Date, offset = 0): Quote {
  const start = Date.UTC(date.getFullYear(), 0, 0);
  const day = Math.floor((Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - start) / 86400000);
  const idx = (((day + date.getFullYear() * 7 + offset) % QUOTES.length) + QUOTES.length) % QUOTES.length;
  return QUOTES[idx]!;
}
