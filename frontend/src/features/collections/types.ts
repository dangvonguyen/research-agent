import type { CollectionResponse as APICollection } from "@/api";

export interface Collection
  extends Omit<APICollection, "created_at" | "updated_at"> {
  id: string;
  paperCount: number;
  lastUpdated: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  venue?: string | null;
  abstract: string | null;
  source_type: "upload" | "url";
  source_url?: string | null;
  file_path?: string | null;
  parsed: boolean;
  created_at: Date;
  updated_at: Date;
  keywords?: string[];
  tags?: string[];
  collectionIds?: string[];
  collection_names?: string[];
}

export interface CollectionsLoaderData {
  collections: Collection[];
}
