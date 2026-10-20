export type Mode = "free" | "topic" | "read" | "twister" | "script";

export const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: "free", label: "Free speak", hint: "Talk about anything" },
  { id: "topic", label: "Topic", hint: "60 seconds, random topic" },
  { id: "read", label: "Read aloud", hint: "Compared against the text" },
  { id: "twister", label: "Twisters", hint: "Graded by difficulty" },
  { id: "script", label: "Voice-over", hint: "Paste your own script" },
];

export const TOPICS = [
  "Describe your ideal weekend.",
  "What's a skill you'd love to master and why?",
  "Explain your job to a ten-year-old.",
  "The best piece of advice you've ever received.",
  "A place that changed how you see the world.",
  "Should remote work be the default? Argue one side.",
  "Walk me through your morning routine.",
  "A book, film or song that stayed with you.",
  "Pitch a product you wish existed.",
  "What does a good leader do differently?",
];

export const PASSAGES = [
  "The quiet harbour woke slowly. Fishermen untangled their nets while gulls circled above, waiting patiently for scraps. By eight o'clock the market was alive with voices, bargaining over the freshest catch of the morning.",
  "Clear communication is less about big words and more about deliberate choices. Pause before key ideas, finish your sentences, and let silence do some of the work for you.",
  "Our quarterly results show steady growth across every region. Customer retention improved by twelve percent, and we plan to expand the team in the spring to support new markets.",
];

export const TWISTERS: { level: 1 | 2 | 3; text: string }[] = [
  { level: 1, text: "Red lorry, yellow lorry." },
  { level: 1, text: "Unique New York, unique New York." },
  { level: 1, text: "A proper copper coffee pot." },
  { level: 2, text: "She sells seashells by the seashore." },
  { level: 2, text: "How can a clam cram in a clean cream can?" },
  { level: 2, text: "Fresh French fried fly fritters." },
  { level: 3, text: "Peter Piper picked a peck of pickled peppers; a peck of pickled peppers Peter Piper picked." },
  { level: 3, text: "The sixth sick sheikh's sixth sheep's sick." },
  { level: 3, text: "Pad kid poured curd pulled cod." },
];

export const WARMUP = [
  { title: "Box breathing", seconds: 30, body: "Inhale 4 · hold 4 · exhale 4 · hold 4. Shoulders down, belly soft." },
  { title: "Lip trills", seconds: 20, body: "Blow air through relaxed lips so they buzz. Slide your pitch up and down." },
  { title: "Jaw & tongue", seconds: 20, body: "Gently open wide, then circle your tongue around your teeth both ways." },
  { title: "Over-articulate", seconds: 20, body: "Say “ma-may-me-mo-moo”, “ta-tay-tee-toe-too” with exaggerated lips." },
  { title: "Tongue twisters", seconds: 30, body: "Red lorry, yellow lorry · Unique New York · A proper copper coffee pot. Slow, then faster." },
];

export const pick = <T,>(a: T[]) => a[Math.floor(Math.random() * a.length)]!;
