export interface SourceItem {
  id: string;
  name: string;
  fileType: 'PDF' | 'DOCX' | 'XLSX' | 'CSV' | 'TXT' | 'MD' | 'IMAGE';
  sizeBytes: number;
  charCount: number;
  preview: string;
  text: string;
  createdAt: string;
  isGenerated?: boolean;
}

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sourcesGrounded?: string[];
  sourceItemsGrounded?: SourceItem[];
}

export interface LmStudioConfig {
  baseUrl: string;
  activeModel: string;
  temperature: number;
  isConnected: boolean;
  statusMessage: string;
}

export type ArtifactType = 'report' | 'video_overview' | 'quiz' | 'datatable' | 'note' | 'study_guide';

export interface StudioNote {
  id: string;
  title: string;
  content: string;
  type: ArtifactType;
  sourcesCount: number;
  sourceNames: string[];
  promptUsed?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface SourceLocationInfo {
  pageNumber: number | string;
  sectionTitle: string;
  locationLabel: string;
  snippet: string;
  matchedKeywords: string[];
  charOffset: number;
  lineNumber: number;
  totalLength: number;
}
