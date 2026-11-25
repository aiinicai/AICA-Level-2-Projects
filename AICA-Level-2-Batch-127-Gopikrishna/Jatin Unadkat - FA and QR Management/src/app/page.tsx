import { redirect } from "next/navigation";
import { requireSession } from "@/lib/rbac";

export default async function RootPage() {
  // Goes through requireSession (not next-auth's auth() directly) so this
  // page also honors DISABLE_AUTH_FOR_TESTING — see src/lib/rbac.ts.
  await requireSession();
  redirect("/dashboard");
}
