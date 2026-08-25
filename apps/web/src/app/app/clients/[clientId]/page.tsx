import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { ClientForm } from "@/components/client-form";
import { internalApiUrl } from "@/lib/api";
import type { Client } from "@/lib/client-types";

export default async function ClientPage({
  params,
}: Readonly<{ params: Promise<{ clientId: string }> }>) {
  const { clientId } = await params;
  const response = await fetch(
    `${internalApiUrl}/clients/${encodeURIComponent(clientId)}`,
    {
      headers: { cookie: (await cookies()).toString() },
      cache: "no-store",
    },
  ).catch(() => null);
  if (response?.status === 401 || response === null) {
    redirect("/signin");
  }
  if (response.status === 404) {
    notFound();
  }
  if (!response.ok) {
    throw new Error("Unable to load client");
  }
  const client = (await response.json()) as Client;

  return (
    <main id="main-content" className="page-shell" tabIndex={-1}>
      <section className="wide-card">
        <p className="eyebrow">Client management</p>
        <h1>Edit {client.name}</h1>
        <ClientForm client={client} />
      </section>
    </main>
  );
}
