import type { Metadata } from "next";

import { ExperimentsView } from "@/components/analysis/experiments-view";
import { ClientPage } from "@/components/shared/client-page";

export const metadata: Metadata = { title: "Experiments" };

export default function Page() {
  return (
    <ClientPage>
      <ExperimentsView />
    </ClientPage>
  );
}
