"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { publicApiUrl } from "@/lib/api";
import type { Client } from "@/lib/client-types";

export function ClientForm({ client }: Readonly<{ client?: Client }>) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    const body = {
      name: form.get("name"),
      company: form.get("company"),
      website: optional(form.get("website")),
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
      router.refresh();
    } catch {
      setError("PressRadar is temporarily unavailable.");
    } finally {
      setSubmitting(false);
    }
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
        <TextField
          label="Company"
          name="company"
          value={client?.company}
          required
        />
        <TextField
          label="Website"
          name="website"
          type="url"
          value={client?.website}
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
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : client ? "Save changes" : "Create client"}
        </button>
        <Link className="button button-secondary" href="/app">
          Cancel
        </Link>
      </div>
    </form>
  );
}

type FieldProps = {
  label: string;
  name: string;
  value?: string | string[] | null;
  type?: string;
  required?: boolean;
};

function TextField({
  label,
  name,
  value,
  type = "text",
  required = false,
}: FieldProps) {
  return (
    <label>
      {label}
      <input
        name={name}
        type={type}
        defaultValue={Array.isArray(value) ? value.join(", ") : (value ?? "")}
        required={required}
      />
    </label>
  );
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
