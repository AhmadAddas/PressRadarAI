import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AccountMenu } from "@/components/account-menu";
import { DismissOpportunityButton } from "@/components/dismiss-opportunity-button";
import { AuditTrail } from "@/components/audit-trail";
import { DemoSetupButton } from "@/components/demo-setup-button";
import { OpportunityWorkflowActions } from "@/components/opportunity-workflow-actions";
import { PitchEditor } from "@/components/pitch-editor";
import { PaginatedSelectableList } from "@/components/paginated-selectable-list";
import { ExpandableText } from "@/components/expandable-text";
import { LocalAIMenu } from "@/components/local-ai-menu";
import { internalApiUrl } from "@/lib/api";
import type { Client } from "@/lib/client-types";
import type { Opportunity } from "@/lib/opportunity-types";
import {
  statusLabels,
  urgencyLabels,
  urgencyLevel,
} from "@/lib/opportunity-presentation";

type Identity = {
  name: string;
  email: string;
  workspace_id: string;
  workspace_kind: "demo" | "prod";
};

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
        <header className="dashboard-header">
          <div className="dashboard-top-row">
            <div>
              <p className="eyebrow">{identity.name}&apos;s workspace</p>
              <h1>Opportunity dashboard</h1>
            </div>
            <AccountMenu name={identity.name} email={identity.email} />
          </div>
          <div className="actions dashboard-actions">
            <LocalAIMenu />
            <div className="dashboard-primary-actions">
              <DemoSetupButton workspaceKind={identity.workspace_kind} />
              <Link className="button button-secondary" href="/app/media">
                Media feed
              </Link>
              <Link className="button" href="/app/clients/new">
                Add client
              </Link>
            </div>
          </div>
        </header>
        <section aria-labelledby="opportunities-heading">
          <h2 id="opportunities-heading">Opportunities</h2>
          {opportunities.length ? (
            <PaginatedSelectableList
              noun="opportunity"
              endpoint="opportunities"
              className="opportunity-list"
              items={opportunities.map((opportunity) => {
                const urgency = urgencyLevel(opportunity.deadline);
                return {
                  id: opportunity.id,
                  label: opportunity.headline,
                  content: (
                    <article className={`urgency-${urgency}`}>
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
                          <span>
                            Deadline {formatTime(opportunity.deadline)}
                          </span>
                        </div>
                      ) : null}
                      {opportunity.relevance_score !== null ? (
                        <div className="relevance">
                          <strong>
                            {opportunity.relevance_score}% relevant
                          </strong>
                          <ExpandableText
                            text={opportunity.relevance_reason ?? ""}
                          />
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
                          actions={
                            <>
                              <DismissOpportunityButton
                                opportunityId={opportunity.id}
                              />
                              <OpportunityWorkflowActions
                                opportunityId={opportunity.id}
                                status={opportunity.status}
                                hasPitch={opportunity.pitch !== null}
                                clientEmail={
                                  clients.find(
                                    (client) =>
                                      client.id === opportunity.client_id,
                                  )?.email
                                }
                              />
                            </>
                          }
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
                          {opportunity.status === "new" ? (
                            <DismissOpportunityButton
                              opportunityId={opportunity.id}
                            />
                          ) : null}
                          {opportunity.status !== "ready" ? (
                            <OpportunityWorkflowActions
                              opportunityId={opportunity.id}
                              status={opportunity.status}
                              hasPitch={opportunity.pitch !== null}
                              clientEmail={
                                clients.find(
                                  (client) =>
                                    client.id === opportunity.client_id,
                                )?.email
                              }
                            />
                          ) : null}
                        </div>
                      </div>
                      <AuditTrail opportunityId={opportunity.id} />
                      {opportunity.client_deleted ||
                      opportunity.media_deleted ? (
                        <p className="orphan-notice">
                          Original{" "}
                          {opportunity.client_deleted &&
                          opportunity.media_deleted
                            ? "client and media item"
                            : opportunity.client_deleted
                              ? "client"
                              : "media item"}{" "}
                          deleted.{" "}
                          <a href="#orphaned-records">Why is this shown?</a>
                        </p>
                      ) : null}
                    </article>
                  ),
                };
              })}
            />
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
            <PaginatedSelectableList
              noun="client"
              endpoint="clients"
              className="client-list"
              items={clients.map((client) => ({
                id: client.id,
                label: client.name,
                content: (
                  <div className="client-card-content">
                    <strong>{client.name}</strong>
                    <span>{client.company || "No company added"}</span>
                    <small>
                      {client.monitoring_rules.length} monitoring rules
                    </small>
                    <Link
                      className="client-edit-link"
                      href={`/app/clients/${client.id}`}
                      aria-label={`Edit ${client.name}`}
                    >
                      <span aria-hidden="true">✎</span> Edit
                    </Link>
                  </div>
                ),
              }))}
            />
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
        <aside className="orphan-explanation" id="orphaned-records">
          <h2>About orphaned records</h2>
          <p>
            PressRadar keeps an opportunity&apos;s historical details when its
            original client or media item is deleted. This protects your review
            and pitch history without restoring the deleted record.
          </p>
        </aside>
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
