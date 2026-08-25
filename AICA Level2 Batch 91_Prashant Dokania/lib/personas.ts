export type PersonaId =
  | "spouse"
  | "professional"
  | "colleague"
  | "recruiter"
  | "teachers"
  | "parent"
  | "kids"
  | "friends"
  | "neighbor";

export type Persona = {
  id: PersonaId;
  label: string;
  blurb: string;
  lens: string;
};

export const PERSONAS: Persona[] = [
  {
    id: "spouse",
    label: "Spouse",
    blurb: "Intimate, ongoing",
    lens: "Look for softness of opening, ownership language over blame, repair attempts, curiosity about their inner world, and whether space was left for them to speak. Directness matters less than warmth and non-defensiveness.",
  },
  {
    id: "professional",
    label: "Professional",
    blurb: "Authority or expertise — manager, lawyer, doctor",
    lens: "Look for leading with the bottom line before context, calibrated confidence rather than over-apologising or overclaiming, brevity, concrete asks, question sufficiency — did you ask enough to actually understand — and hedging language that dilutes the point.",
  },
  {
    id: "colleague",
    label: "Colleague",
    blurb: "Peer, collaborative",
    lens: "Look for shared framing, invitation to co-solve, air-time balance, and whether feedback was specific rather than personal.",
  },
  {
    id: "recruiter",
    label: "Recruiter / Interviewer",
    blurb: "Being evaluated",
    lens: "Look for structured answers, concrete evidence and outcomes, self-advocacy without inflation, filler under pressure, and questions asked back.",
  },
  {
    id: "teachers",
    label: "Teachers",
    blurb: "A teacher or mentor, and you're the student",
    lens: "Look for whether you named the specific thing you were stuck on, asked a real question instead of apologising, showed the work you had already tried, and checked what to do next. Being unsure is fine here. Being vague is what costs you the answer.",
  },
  {
    id: "parent",
    label: "Parent",
    blurb: "Long history, old patterns",
    lens: "Look for boundary-setting without hostility, staying in the present rather than old scorekeeping, and I-language.",
  },
  {
    id: "kids",
    label: "Kids",
    blurb: "Teaching moments",
    lens: "Look for short sentences, calm tone words, curiosity before correction, and whether a choice or reason was offered instead of a directive.",
  },
  {
    id: "friends",
    label: "Friends & Family",
    blurb: "Casual, personal, no performance",
    lens: "Look for reciprocity — did the sharing go both ways — and for being present: following up on what they said, easy warmth, humour, and not slipping into advice-giving or updates-only mode. Nothing here is about performance.",
  },
  {
    id: "neighbor",
    label: "Neighbor / Acquaintance",
    blurb: "Low stakes, first impressions",
    lens: "Look for warmth in the opening, question-to-statement ratio, and whether you left doors open for the relationship to continue.",
  },
];

// Older saved sessions may carry retired persona ids.
const LEGACY: Record<string, PersonaId> = {
  wife: "spouse",
  manager: "professional",
  lawyer: "professional",
  doctor: "professional",
};

export function personaOf(id: string): Persona {
  const resolved = LEGACY[id] ?? id;
  return PERSONAS.find((p) => p.id === resolved) ?? (PERSONAS[0] as Persona);
}
