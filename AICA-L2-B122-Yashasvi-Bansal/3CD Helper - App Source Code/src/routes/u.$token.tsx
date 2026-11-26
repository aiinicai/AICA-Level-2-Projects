import { createFileRoute } from "@tanstack/react-router";
import { ClientUpload } from "@/components/screens/ClientUpload";

function Page() {
  const { token } = Route.useParams();
  return <ClientUpload token={token} />;
}

// Public: a client opens the upload link from WhatsApp without an account.
export const Route = createFileRoute("/u/$token")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Upload data · 3CD Helper" },
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
  component: Page,
});
