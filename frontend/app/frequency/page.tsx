import type { Metadata } from "next";

import { FrequencyView } from "@/components/analysis/frequency-view";
import { ClientPage } from "@/components/shared/client-page";

export const metadata: Metadata = { title: "Frequency Analysis" };

export default function Page() {
  return (
    <ClientPage>
      <FrequencyView />
    </ClientPage>
  );
}
