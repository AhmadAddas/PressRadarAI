"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { publicApiUrl } from "@/lib/api";
import type {
  MediaSource,
  MediaSourceKind,
  MediaSourceSuggestion,
} from "@/lib/media-source-types";

export function MediaSourceManager({
  sources,
  suggestions,
}: Readonly<{
  sources: MediaSource[];
  suggestions: MediaSourceSuggestion[];
}>) {
  const router = useRouter();
  const [filter, setFilter] = useState<MediaSourceKind | "all">("all");
  const [open, setOpen] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState("");
  const visibleSources = sources.filter(
    (source) => filter === "all" || source.kind === filter,
  );
  const visibleSuggestions = suggestions.filter(
    (source) => filter === "all" || source.kind === filter,
  );

  async function ingest() {
    await request(
      `${publicApiUrl}/media/ingest`,
      { method: "POST" },
      (result) => {
        const counts = result as { created: number; duplicates: number };
        setMessage(
          counts.created
            ? `Added ${counts.created} media items.`
            : `${counts.duplicates} media items were already ingested.`,
        );
      },
    );
  }

  async function addSuggestion(source: MediaSourceSuggestion) {
    await createSource(source);
  }

  async function addRss(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await createSource({
      name: String(data.get("name")),
      kind: "rss",
      url: String(data.get("url")),
      provider: null,
    });
  }

  async function createSource(source: MediaSourceSuggestion) {
    await request(`${publicApiUrl}/media/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(source),
    });
  }

  async function remove(sourceId: string) {
    await request(`${publicApiUrl}/media/sources/${sourceId}`, {
      method: "DELETE",
    });
  }

  async function request(
    url: string,
    init: RequestInit,
    onSuccess?: (result: unknown) => void,
  ) {
    setWorking(true);
    setMessage("");
    try {
      const response = await fetch(url, { ...init, credentials: "include" });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        setMessage(payload?.detail ?? "Unable to update media sources.");
        return;
      }
      const result = response.status === 204 ? null : await response.json();
      onSuccess?.(result);
      router.refresh();
    } catch {
      setMessage("PressRadar is temporarily unavailable.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="source-manager">
      <div className="source-toolbar">
        <button type="button" onClick={ingest} disabled={working}>
          {working ? "Working…" : "Ingest media"}
        </button>
        <button
          className="button-secondary"
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls="media-source-options"
        >
          Media options
        </button>
      </div>
      {message ? <p role="status">{message}</p> : null}
      {open ? (
        <section className="source-options" id="media-source-options">
          <label>
            Filter sources
            <select
              value={filter}
              onChange={(event) =>
                setFilter(event.target.value as MediaSourceKind | "all")
              }
            >
              <option value="all">All</option>
              <option value="rss">RSS</option>
              <option value="api">API</option>
            </select>
          </label>
          <div className="source-list">
            <h2>Configured sources</h2>
            {visibleSources.length ? (
              <ul>
                {visibleSources.map((source) => (
                  <li key={source.id}>
                    <span>
                      <strong>{source.name}</strong>
                      <small>{source.kind.toUpperCase()}</small>
                    </span>
                    <button
                      className="button-danger"
                      type="button"
                      onClick={() => remove(source.id)}
                      disabled={working}
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No sources match this filter.</p>
            )}
          </div>
          <div className="source-list">
            <h2>Suggested UAE sources</h2>
            <ul>
              {visibleSuggestions.map((source) => (
                <li key={`${source.kind}-${source.name}`}>
                  <span>
                    <strong>{source.name}</strong>
                    <small>{source.kind.toUpperCase()}</small>
                  </span>
                  <button
                    className="button-secondary"
                    type="button"
                    onClick={() => addSuggestion(source)}
                    disabled={working}
                  >
                    Add
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <form className="source-form" onSubmit={addRss}>
            <h2>Add RSS source</h2>
            <label>
              Source name
              <input name="name" required maxLength={100} />
            </label>
            <label>
              HTTPS feed URL
              <input name="url" type="url" pattern="https://.*" required />
            </label>
            <button type="submit" disabled={working}>
              Add RSS source
            </button>
          </form>
        </section>
      ) : null}
    </div>
  );
}
