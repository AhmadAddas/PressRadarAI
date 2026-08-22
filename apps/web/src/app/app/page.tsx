import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { SignOutButton } from "@/components/signout-button";
import { DismissOpportunityButton } from "@/components/dismiss-opportunity-button";
import { internalApiUrl } from "@/lib/api";
import type { Client } from "@/lib/client-types";
import type { Opportunity } from "@/lib/opportunity-types";

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
  const opportunitiesResponse = await fetch(`${internalApiUrl}/opportunities`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (!opportunitiesResponse.ok) {
    throw new Error("Unable to load opportunities");
  }
  const opportunities = (await opportunitiesResponse.json()) as Opportunity[];
  return (
    <main className="page-shell">
      <section className="wide-card">
        <header className="page-header">
          <div>
            <p className="eyebrow">{identity.name}&apos;s workspace</p>
            <h1>Opportunity dashboard</h1>
          </div>
          <div className="actions">
            <Link href="/app/media">Media feed</Link>
            <Link className="button" href="/app/clients/new">
              Add client
            </Link>
            <SignOutButton />
          </div>
        </header>
        <section aria-labelledby="opportunities-heading">
          <h2 id="opportunities-heading">Opportunities</h2>
          {opportunities.length ? (
            <ul className="opportunity-list">
              {opportunities.map((opportunity) => (
                <li
                  key={opportunity.id}
                  className={opportunity.deadline ? "urgent" : undefined}
                >
                  <div className="opportunity-heading">
                    <div>
                      <p className="eyebrow">
                        {opportunity.client_name} · {opportunity.client_company}
                      </p>
                      <h3>{opportunity.headline}</h3>
                    </div>
                    <span className="status">{opportunity.status}</span>
                  </div>
                  <p>
                    {opportunity.source}
                    {opportunity.journalist
                      ? ` · ${opportunity.journalist}`
                      : ""}
                  </p>
                  {opportunity.deadline ? (
                    <strong className="deadline">
                      Deadline {formatTime(opportunity.deadline)}
                    </strong>
                  ) : null}
                  <div className="opportunity-footer">
                    <div className="topics">
                      {opportunity.matched_topics.map((topic) => (
                        <span key={topic}>{topic}</span>
                      ))}
                    </div>
                    {opportunity.status === "new" ? (
                      <DismissOpportunityButton
                        opportunityId={opportunity.id}
                      />
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">
              <h3>No opportunities yet</h3>
              <p>Add a client, then ingest media to detect relevant matches.</p>
            </div>
          )}
        </section>
        <section aria-labelledby="clients-heading">
          <h2 id="clients-heading">Clients</h2>
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
                Add the first client to define their profile and monitoring
                rules.
              </p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
