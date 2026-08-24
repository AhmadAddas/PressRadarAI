import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { PageTranslator } from "@/components/page-translator";
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
  return <PageTranslator>{children}</PageTranslator>;
}
