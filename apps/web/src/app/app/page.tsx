import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { SignOutButton } from "@/components/signout-button";
import { internalApiUrl } from "@/lib/api";

type Identity = { name: string; email: string; workspace_id: string };

export default async function ApplicationPage() {
  const response = await fetch(`${internalApiUrl}/auth/me`, {
    headers: { cookie: (await cookies()).toString() },
    cache: "no-store",
  }).catch(() => null);
  if (!response?.ok) {
    redirect("/signin");
  }

  const identity = (await response.json()) as Identity;
  return (
    <main>
      <section className="card">
        <p className="eyebrow">Authenticated workspace</p>
        <h1>Welcome, {identity.name}</h1>
        <p>{identity.email}</p>
        <p className="workspace-id">Workspace: {identity.workspace_id}</p>
        <SignOutButton />
      </section>
    </main>
  );
}
