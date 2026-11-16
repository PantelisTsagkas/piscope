import type { Metadata } from "next";

import { SearchView } from "@/components/search/search-view";
import { ClientPage } from "@/components/shared/client-page";

export const metadata: Metadata = { title: "Sequence Search" };

export default function Page() {
  return (
    <ClientPage>
      <SearchView />
    </ClientPage>
  );
}
