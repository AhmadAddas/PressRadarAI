import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { internalApiUrl } from "@/lib/api";

export default async function ProtectedLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const response = await fetch(`${internalApiUrl}/auth/me`, {
    headers: { cookie: (await cookies()).toString() },
    cache: "no-store",
  }).catch(() => null);
  if (!response?.ok) {
    redirect("/signin");
  }
  const identity = (await response.json()) as { onboarding_completed: boolean };
  if (!identity.onboarding_completed) {
    redirect("/onboarding");
  }
  return children;
}
