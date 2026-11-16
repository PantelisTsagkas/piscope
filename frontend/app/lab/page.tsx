import type { Metadata } from "next";

import { LabView } from "@/components/analysis/lab-view";
import { ClientPage } from "@/components/shared/client-page";

export const metadata: Metadata = { title: "Statistical Lab" };

export default function Page() {
  return (
    <ClientPage>
      <LabView />
    </ClientPage>
  );
}
