import type { Metadata } from "next";

import { ExplorerView } from "@/components/explorer/explorer-view";
import { ClientPage } from "@/components/shared/client-page";

export const metadata: Metadata = { title: "Digit Explorer" };

export default function Page() {
  return (
    <ClientPage>
      <ExplorerView />
    </ClientPage>
  );
}
