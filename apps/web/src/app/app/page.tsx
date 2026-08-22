import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { SignOutButton } from "@/components/signout-button";
import { internalApiUrl } from "@/lib/api";
import type { Client } from "@/lib/client-types";

type Identity = { name: string; email: string; workspace_id: string };

export default async function ApplicationPage() {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(`${internalApiUrl}/auth/me`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  }).catch(() => null);
  if (!response?.ok) {
    redirect("/signin");
  }

  const identity = (await response.json()) as Identity;
  const clientsResponse = await fetch(`${internalApiUrl}/clients`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (!clientsResponse.ok) {
    throw new Error("Unable to load clients");
  }
  const clients = (await clientsResponse.json()) as Client[];
  return (
    <main className="page-shell">
      <section className="wide-card">
        <header className="page-header">
          <div>
            <p className="eyebrow">{identity.name}&apos;s workspace</p>
            <h1>Clients</h1>
          </div>
          <div className="actions">
            <Link className="button" href="/app/clients/new">
              Add client
            </Link>
            <SignOutButton />
          </div>
        </header>
        {clients.length ? (
          <ul className="client-list">
            {clients.map((client) => (
              <li key={client.id}>
                <Link href={`/app/clients/${client.id}`}>
                  <strong>{client.name}</strong>
                  <span>{client.company}</span>
                  <small>
                    {client.monitoring_rules.length} monitoring rules
                  </small>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <h2>No clients yet</h2>
            <p>
              Add the first client to define their profile and monitoring rules.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
