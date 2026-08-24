"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, startTransition, useEffect, useState } from "react";

import { publicApiUrl } from "@/lib/api";
import type { Client } from "@/lib/client-types";

export function ClientForm({ client }: Readonly<{ client?: Client }>) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pendingBody, setPendingBody] = useState<ClientPayload | null>(null);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(
      () => setCountdown((value) => value - 1),
      1000,
    );
    return () => window.clearTimeout(timer);
  }, [countdown]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const body: ClientPayload = {
      name: String(form.get("name") ?? "").trim(),
      company: optional(form.get("company")),
      website: website(form.get("website")),
      industry: optional(form.get("industry")),
      description: optional(form.get("description")),
      location: optional(form.get("location")),
      expertise: commaList(form.get("expertise")),
      spokesperson_name: optional(form.get("spokesperson_name")),
      spokesperson_title: optional(form.get("spokesperson_title")),
      keywords: commaList(form.get("keywords")),
      excluded_keywords: commaList(form.get("excluded_keywords")),
      preferred_topics: commaList(form.get("preferred_topics")),
      tone: optional(form.get("tone")),
      monitoring_rules: lineList(form.get("monitoring_rules")),
    };

    const missing = importantMissingFields(body);
    if (!client && missing.length) {
      setPendingBody(body);
      setMissingFields(missing);
      setCountdown(5);
      return;
    }
    await save(body);
  }

  async function save(body: ClientPayload) {
    setSubmitting(true);
    try {
      const response = await fetch(
        `${publicApiUrl}/clients${client ? `/${client.id}` : ""}`,
        {
          method: client ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(body),
        },
      );
      if (!response.ok) {
        setError("Check the client details and try again.");
        return;
      }
      const saved = (await response.json()) as Client;
      router.push(`/app/clients/${saved.id}`);
      startTransition(() => router.refresh());
    } catch {
      setError("PressRadar is temporarily unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmIncompleteClient() {
    if (!pendingBody || countdown > 0) return;
    const body = pendingBody;
    setPendingBody(null);
    await save(body);
  }

  return (
    <form className="client-form" onSubmit={submit}>
      <div className="form-grid">
        <TextField
          label="Client name"
          name="name"
          value={client?.name}
          required
        />
        <TextField label="Company" name="company" value={client?.company} />
        <TextField
          label="Website"
          name="website"
          type="url"
          value={client?.website}
          autoUrl
        />
        <TextField label="Industry" name="industry" value={client?.industry} />
        <TextField label="Location" name="location" value={client?.location} />
        <TextField
          label="Spokesperson"
          name="spokesperson_name"
          value={client?.spokesperson_name}
        />
        <TextField
          label="Spokesperson title"
          name="spokesperson_title"
          value={client?.spokesperson_title}
        />
        <TextField label="Tone" name="tone" value={client?.tone} />
      </div>
      <TextArea
        label="Description"
        name="description"
        value={client?.description}
      />
      <TextField
        label="Expertise (comma separated)"
        name="expertise"
        value={client?.expertise}
      />
      <TextField
        label="Keywords (comma separated)"
        name="keywords"
        value={client?.keywords}
      />
      <TextField
        label="Excluded keywords (comma separated)"
        name="excluded_keywords"
        value={client?.excluded_keywords}
      />
      <TextField
        label="Preferred topics (comma separated)"
        name="preferred_topics"
        value={client?.preferred_topics}
      />
      <TextArea
        label="Monitoring rules (one phrase per line)"
        name="monitoring_rules"
        value={client?.monitoring_rules}
      />
      {error ? <p role="alert">{error}</p> : null}
      <div className="actions">
        <button type="submit" disabled={submitting} aria-busy={submitting}>
          {client ? "Save changes" : "Create client"}
        </button>
        <Link className="button button-secondary" href="/app">
          Cancel
        </Link>
      </div>
      {pendingBody ? (
        <div className="modal-backdrop" role="presentation">
          <div
            className="confirmation-modal"
            role="alertdialog"
            aria-modal="true"
          >
            <strong>Create this client with incomplete context?</strong>
            <p>
              {formatList(missingFields)} will be empty. You can add them later,
              but matching and pitch context may be less accurate.
            </p>
            <div className="actions">
              <button
                type="button"
                disabled={countdown > 0 || submitting}
                onClick={confirmIncompleteClient}
              >
                {countdown > 0 ? `Confirm in ${countdown}s` : "Create anyway"}
              </button>
              <button
                className="button-secondary"
                type="button"
                disabled={submitting}
                onClick={() => setPendingBody(null)}
              >
                Continue editing
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </form>
  );
}

type FieldProps = {
  label: string;
  name: string;
  value?: string | string[] | null;
  type?: string;
  required?: boolean;
  autoUrl?: boolean;
};

function TextField({
  label,
  name,
  value,
  type = "text",
  required = false,
  autoUrl = false,
}: FieldProps) {
  return (
    <label>
      {label}
      <input
        name={name}
        type={type}
        defaultValue={Array.isArray(value) ? value.join(", ") : (value ?? "")}
        required={required}
        onBlur={
          autoUrl
            ? (event) => {
                event.currentTarget.value =
                  website(event.currentTarget.value) ?? "";
              }
            : undefined
        }
      />
    </label>
  );
}

type ClientPayload = {
  name: string;
  company: string | null;
  website: string | null;
  industry: string | null;
  description: string | null;
  location: string | null;
  expertise: string[];
  spokesperson_name: string | null;
  spokesperson_title: string | null;
  keywords: string[];
  excluded_keywords: string[];
  preferred_topics: string[];
  tone: string | null;
  monitoring_rules: string[];
};

function website(value: FormDataEntryValue | string | null): string | null {
  const text = optional(value);
  if (!text || /^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
}

function importantMissingFields(body: ClientPayload): string[] {
  return [
    ["company", body.company],
    ["website", body.website],
    ["expertise", body.expertise.length],
    ["monitoring rules", body.monitoring_rules.length],
  ]
    .filter(([, value]) => !value)
    .map(([label]) => String(label));
}

function formatList(items: string[]): string {
  if (items.length < 2) return items[0] ?? "Some fields";
  return `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

function TextArea({ label, name, value }: FieldProps) {
  return (
    <label>
      {label}
      <textarea
        name={name}
        defaultValue={Array.isArray(value) ? value.join("\n") : (value ?? "")}
      />
    </label>
  );
}

function optional(value: FormDataEntryValue | null): string | null {
  const text = typeof value === "string" ? value.trim() : "";
  return text || null;
}

function commaList(value: FormDataEntryValue | null): string[] {
  return split(value, /,/);
}

function lineList(value: FormDataEntryValue | null): string[] {
  return split(value, /\r?\n/);
}

function split(value: FormDataEntryValue | null, separator: RegExp): string[] {
  return typeof value === "string"
    ? value
        .split(separator)
        .map((item) => item.trim())
        .filter(Boolean)
    : [];
}
