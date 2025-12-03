import { useParams } from "react-router-dom";
import { CollectionPapersView } from "../components/CollectionPapersView";

export function CollectionPapersViewRoute() {
  const { collectionId } = useParams<{ collectionId: string }>();

  if (!collectionId) {
    return <div>Collection ID is required</div>;
  }

  return <CollectionPapersView collectionId={collectionId} />;
}

