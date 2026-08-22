import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AccountMenu } from "@/components/account-menu";
import { DismissOpportunityButton } from "@/components/dismiss-opportunity-button";
import { AuditTrail } from "@/components/audit-trail";
import { DemoSetupButton } from "@/components/demo-setup-button";
import { OpportunityWorkflowActions } from "@/components/opportunity-workflow-actions";
import { PitchEditor } from "@/components/pitch-editor";
import { internalApiUrl } from "@/lib/api";
import type { Client } from "@/lib/client-types";
import type { Opportunity } from "@/lib/opportunity-types";
import {
  statusLabels,
  urgencyLabels,
  urgencyLevel,
} from "@/lib/opportunity-presentation";

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
            <DemoSetupButton initiallyReady={isDemoWorkspaceReady(clients)} />
            <Link className="button button-secondary" href="/app/media">
              Media feed
            </Link>
            <Link className="button" href="/app/clients/new">
              Add client
            </Link>
            <AccountMenu name={identity.name} email={identity.email} />
          </div>
        </header>
        <section aria-labelledby="opportunities-heading">
          <h2 id="opportunities-heading">Opportunities</h2>
          {opportunities.length ? (
            <ul className="opportunity-list">
              {opportunities.map((opportunity) => {
                const urgency = urgencyLevel(opportunity.deadline);
                return (
                  <li key={opportunity.id} className={`urgency-${urgency}`}>
                    <div className="opportunity-heading">
                      <div>
                        <p className="eyebrow">
                          {opportunity.client_name} ·{" "}
                          {opportunity.client_company}
                        </p>
                        <h3>{opportunity.headline}</h3>
                      </div>
                      <span className={`status status-${opportunity.status}`}>
                        {statusLabels[opportunity.status]}
                      </span>
                    </div>
                    <p>
                      {opportunity.source}
                      {opportunity.journalist
                        ? ` · ${opportunity.journalist}`
                        : ""}
                    </p>
                    <p className="detected-time">
                      Detected {formatTime(opportunity.detected_at)}
                    </p>
                    {opportunity.deadline ? (
                      <div className="deadline">
                        {urgency !== "none" ? (
                          <strong>{urgencyLabels[urgency]}</strong>
                        ) : null}
                        <span>Deadline {formatTime(opportunity.deadline)}</span>
                      </div>
                    ) : null}
                    {opportunity.relevance_score !== null ? (
                      <div className="relevance">
                        <strong>{opportunity.relevance_score}% relevant</strong>
                        <p>{opportunity.relevance_reason}</p>
                      </div>
                    ) : null}
                    {opportunity.analysis_error ? (
                      <p role="alert">{opportunity.analysis_error}</p>
                    ) : null}
                    {opportunity.status === "ready" ? (
                      <PitchEditor
                        opportunityId={opportunity.id}
                        initialContent={opportunity.pitch?.content ?? ""}
                        generationError={opportunity.pitch_error}
                      />
                    ) : null}
                    {opportunity.status !== "ready" && opportunity.pitch ? (
                      <div className="pitch-readonly">
                        <strong>Pitch</strong>
                        <p>{opportunity.pitch.content}</p>
                      </div>
                    ) : null}
                    {opportunity.send_error ? (
                      <p role="alert">{opportunity.send_error}</p>
                    ) : null}
                    {opportunity.delivery ? (
                      <p className="delivery-status">
                        Sent via {opportunity.delivery.provider} on{" "}
                        {formatTime(opportunity.delivery.sent_at)}
                      </p>
                    ) : null}
                    <div className="opportunity-footer">
                      <div className="topics">
                        {opportunity.matched_topics.map((topic) => (
                          <span key={topic}>{topic}</span>
                        ))}
                      </div>
                      <div className="opportunity-controls">
                        {opportunity.status === "new" ||
                        opportunity.status === "ready" ? (
                          <DismissOpportunityButton
                            opportunityId={opportunity.id}
                          />
                        ) : null}
                        <OpportunityWorkflowActions
                          opportunityId={opportunity.id}
                          status={opportunity.status}
                          hasPitch={opportunity.pitch !== null}
                        />
                      </div>
                    </div>
                    <AuditTrail opportunityId={opportunity.id} />
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="empty-state">
              <h3>No opportunities yet</h3>
              <p>
                Load the demo workspace, or add a client and ingest media to
                detect relevant matches.
              </p>
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

function isDemoWorkspaceReady(clients: Client[]): boolean {
  const demoClients = new Set([
    "nadia rahman|vertexai labs",
    "mariam al noor|gulffin advisory",
    "samir qureshi|launchbridge",
  ]);
  const clientKeys = new Set(
    clients.map((client) =>
      `${client.name}|${client.company}`.toLocaleLowerCase(),
    ),
  );
  return [...demoClients].every((demoClient) => clientKeys.has(demoClient));
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
