import { createFileRoute } from "@tanstack/react-router";
import Landing from "@/components/screens/Landing";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "3CD Helper – Tax Audit Assistant for CAs" },
      { name: "description", content: "Prepare Form 3CD Clause 44 (GST-wise expenditure break-up) and Clause 31 (loans & deposits) from Tally, Busy, Excel or any accounting data." },
      { property: "og:title", content: "3CD Helper – Tax Audit Assistant for CAs" },
      { property: "og:description", content: "Prepare Form 3CD Clause 44 (GST-wise expenditure break-up) and Clause 31 (loans & deposits) from Tally, Busy, Excel or any accounting data." },
    ],
  }),
  component: Landing,
});
