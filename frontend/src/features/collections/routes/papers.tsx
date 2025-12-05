import { CollectionPapersView } from "../components/CollectionPapersView";

export function PapersView() {
  // Show all papers (no collection filter)
  return <CollectionPapersView collectionId={null} />;
}
