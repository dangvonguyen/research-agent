import type { RouteObject } from "react-router-dom";
import { CollectionPapersViewRoute } from "./routes/collection-papers";
import { CollectionsView } from "./routes/collections";
import { CollectionsOverviewView } from "./routes/collections-overview";
import { PapersView } from "./routes/papers";

export const collectionsRoutes: RouteObject[] = [
  {
    path: "/collections",
    children: [
      {
        index: true,
        Component: CollectionsOverviewView,
      },
      {
        path: "overview",
        Component: CollectionsOverviewView,
      },
      {
        path: "papers",
        Component: PapersView,
      },
      {
        path: "list",
        Component: CollectionsView,
      },
      {
        path: ":collectionId",
        Component: CollectionPapersViewRoute,
      },
    ],
  },
];
