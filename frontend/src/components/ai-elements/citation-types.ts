export interface Citation {
  number?: number;
  title?: string;
  url: string;
  text?: string;
}

export interface CitationsData {
  title?: string;
  citations: Citation | Citation[]; // Support both single object and array
}

