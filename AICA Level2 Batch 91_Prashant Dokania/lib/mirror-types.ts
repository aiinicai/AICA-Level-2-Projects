export type Pattern = {
  title: string;
  observation: string;
  suggestion: string;
  tone: "strength" | "growth";
};

export type Analysis = {
  transcript: string;
  summary: string;
  goalReflection: string;
  metrics: {
    airtimePercent: number;
    questionsAsked: number;
    iLanguage: number;
    youLanguage: number;
    fillerWords: number;
    ledWith: "problem" | "context" | "unclear";
  };
  patterns: Pattern[];
};

export const EMPTY_ANALYSIS: Analysis = {
  transcript: "",
  summary: "",
  goalReflection: "",
  metrics: {
    airtimePercent: 0,
    questionsAsked: 0,
    iLanguage: 0,
    youLanguage: 0,
    fillerWords: 0,
    ledWith: "unclear",
  },
  patterns: [],
};
