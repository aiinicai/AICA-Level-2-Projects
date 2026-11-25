"use client";

import { signOut } from "next-auth/react";

export default function SignOutButton() {
  return (
    <button
      onClick={() => signOut({ callbackUrl: "/login" })}
      className="mt-2 text-xs text-steel hover:underline"
    >
      Sign out
    </button>
  );
}
