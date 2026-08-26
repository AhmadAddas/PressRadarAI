"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, startTransition, useEffect, useId, useState } from "react";

import { publicApiUrl } from "@/lib/api";
import { AccessibleDialog } from "@/components/accessible-dialog";
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
      name: capitalizeFirst(String(form.get("name") ?? "").trim()),
      company: optional(form.get("company")),
      website: website(form.get("website")),
      email: optional(form.get("email")),
      phone: optional(form.get("phone")),
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
    if (missing.length) {
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
      router.push("/app");
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
          label="Client/Account Name"
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
          pattern="https?://([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}(:[0-9]{1,5})?([/?#].*)?"
          placeholder="https://example.com"
          validationMessage="Enter a valid website domain, such as example.com."
        />
        <TextField
          label="Email"
          name="email"
          type="email"
          value={client?.email}
          validationMessage="Enter a valid email address."
        />
        <TextField
          label="Phone number"
          name="phone"
          type="tel"
          value={client?.phone}
          pattern="\+[1-9][0-9]{7,14}"
          placeholder="+971501234567"
          validationMessage="Use international format, such as +971501234567."
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
        <TextField
          label="Tone"
          name="tone"
          value={client?.tone}
          hint="Tone guides how Local AI analyzes ingested media and writes relevance explanations and pitch drafts."
        />
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
        <AccessibleDialog
          title={`${client ? "Save" : "Create"} this client with incomplete context?`}
          description={
            <>
              {formatList(missingFields)} will be empty. You can add them later,
              but matching and pitch context may be less accurate.
            </>
          }
          onClose={() => setPendingBody(null)}
        >
          <div className="actions">
            <button
              type="button"
              disabled={countdown > 0 || submitting}
              onClick={confirmIncompleteClient}
            >
              {countdown > 0
                ? `Confirm in ${countdown}s`
                : client
                  ? "Save anyway"
                  : "Create anyway"}
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
        </AccessibleDialog>
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
  pattern?: string;
  placeholder?: string;
  validationMessage?: string;
  hint?: string;
};

function TextField({
  label,
  name,
  value,
  type = "text",
  required = false,
  autoUrl = false,
  pattern,
  placeholder,
  validationMessage,
  hint,
}: FieldProps) {
  const [invalid, setInvalid] = useState(false);
  const inputId = useId();
  const hintId = useId();

  function updateValidity(input: HTMLInputElement) {
    setInvalid(Boolean(input.value) && !input.validity.valid);
  }

  return (
    <div className="form-field">
      <span className="field-label-row">
        <label htmlFor={inputId}>{label}</label>
        {invalid && validationMessage ? (
          <span className="field-validation-error" role="alert">
            {validationMessage}
          </span>
        ) : null}
        {hint ? (
          <span className="field-help">
            <button
              className="field-help-trigger"
              type="button"
              aria-label={`About ${label}`}
              aria-describedby={hintId}
            >
              i
            </button>
            <span className="field-help-text" id={hintId} role="tooltip">
              {hint}
            </span>
          </span>
        ) : null}
      </span>
      <input
        id={inputId}
        name={name}
        type={type}
        defaultValue={Array.isArray(value) ? value.join(", ") : (value ?? "")}
        required={required}
        pattern={pattern}
        placeholder={placeholder}
        aria-invalid={invalid || undefined}
        aria-describedby={hint ? hintId : undefined}
        onInvalid={(event) => {
          event.preventDefault();
          updateValidity(event.currentTarget);
        }}
        onInput={(event) => {
          if (invalid) updateValidity(event.currentTarget);
        }}
        onBlur={
          autoUrl
            ? (event) => {
                event.currentTarget.value =
                  website(event.currentTarget.value) ?? "";
                updateValidity(event.currentTarget);
              }
            : validationMessage
              ? (event) => updateValidity(event.currentTarget)
              : undefined
        }
      />
    </div>
  );
}

type ClientPayload = {
  name: string;
  company: string | null;
  website: string | null;
  email: string | null;
  phone: string | null;
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
    ["Company", body.company],
    ["Website", body.website],
    ["Email", body.email],
    ["Phone number", body.phone],
    ["Expertise", body.expertise.length],
    ["Monitoring rules", body.monitoring_rules.length],
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

function capitalizeFirst(value: string): string {
  return value ? `${value.charAt(0).toUpperCase()}${value.slice(1)}` : value;
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
