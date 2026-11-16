import type { Metadata } from "next";

import { AboutView } from "@/components/analysis/about-view";
import { ClientPage } from "@/components/shared/client-page";

export const metadata: Metadata = { title: "About" };

export default function Page() {
  return (
    <ClientPage>
      <AboutView />
    </ClientPage>
  );
}
