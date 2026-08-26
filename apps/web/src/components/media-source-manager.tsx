"use client";

import { usePathname, useRouter } from "next/navigation";
import { FormEvent, startTransition, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";
import { AccessibleDialog } from "@/components/accessible-dialog";
import {
  ingestionSummary,
  type IngestionCounts,
} from "@/lib/ingestion-summary";
import type {
  MediaSource,
  MediaSourceKind,
  MediaSourceSuggestion,
} from "@/lib/media-source-types";

export function MediaSourceManager({
  sources,
  suggestions,
  initialFilter = "all",
}: Readonly<{
  sources: MediaSource[];
  suggestions: MediaSourceSuggestion[];
  initialFilter?: MediaSourceKind | "all";
}>) {
  const router = useRouter();
  const pathname = usePathname();
  const [filter, setFilter] = useState<MediaSourceKind | "all">(initialFilter);
  const [open, setOpen] = useState(false);
  const [working, setWorking] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<MediaSource | null>(null);
  const [sourcePage, setSourcePage] = useState(1);
  const [suggestionPage, setSuggestionPage] = useState(1);
  const managerRef = useRef<HTMLDivElement>(null);
  const visibleSources = sources.filter(
    (source) => filter === "all" || source.kind === filter,
  );
  const visibleSuggestions = suggestions.filter(
    (source) => filter === "all" || source.kind === filter,
  );
  const pageSize = 5;
  const sourcePageCount = Math.max(
    1,
    Math.ceil(visibleSources.length / pageSize),
  );
  const suggestionPageCount = Math.max(
    1,
    Math.ceil(visibleSuggestions.length / pageSize),
  );
  const currentSourcePage = Math.min(sourcePage, sourcePageCount);
  const currentSuggestionPage = Math.min(suggestionPage, suggestionPageCount);
  const pagedSources = visibleSources.slice(
    (currentSourcePage - 1) * pageSize,
    currentSourcePage * pageSize,
  );
  const pagedSuggestions = visibleSuggestions.slice(
    (currentSuggestionPage - 1) * pageSize,
    currentSuggestionPage * pageSize,
  );

  useEffect(() => {
    if (!open) return;

    function dismiss(event: PointerEvent | KeyboardEvent) {
      if (
        event.type === "keydown" &&
        (event as KeyboardEvent).key === "Escape"
      ) {
        setOpen(false);
        return;
      }
      if (
        event.type === "pointerdown" &&
        !managerRef.current?.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", dismiss);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", dismiss);
    };
  }, [open]);

  async function ingest() {
    toast.info(
      "Switching Local AI to Qwen for media analysis and pitch generation.",
    );
    setIngesting(true);
    const loadingToast = toast.loading(
      "Ingesting media and analyzing opportunities…",
    );
    await request(
      `${publicApiUrl}/media/ingest`,
      { method: "POST" },
      (result) => {
        toast.success(ingestionSummary(result as IngestionCounts));
      },
      false,
    );
    toast.dismiss(loadingToast);
    setIngesting(false);
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
      provider: data.get("journalistRequests") ? "journalist_requests" : null,
    });
  }

  async function createSource(source: MediaSourceSuggestion) {
    await request(`${publicApiUrl}/media/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(source),
    });
  }

  async function remove() {
    if (!pendingDelete) return;
    const removed = await request(
      `${publicApiUrl}/media/sources/${pendingDelete.id}`,
      { method: "DELETE" },
    );
    if (removed) setPendingDelete(null);
  }

  async function request(
    url: string,
    init: RequestInit,
    onSuccess?: (result: unknown) => void,
    lockControls = true,
  ) {
    if (lockControls) setWorking(true);
    try {
      const response = await fetch(url, { ...init, credentials: "include" });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        toast.error(payload?.detail ?? "Unable to update media sources.");
        return false;
      }
      const result = response.status === 204 ? null : await response.json();
      onSuccess?.(result);
      startTransition(() => router.refresh());
      return true;
    } catch {
      toast.error("PressRadar is temporarily unavailable.");
      return false;
    } finally {
      if (lockControls) setWorking(false);
    }
  }

  return (
    <div className="source-manager" ref={managerRef}>
      <div className="source-toolbar">
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
      {open ? (
        <section className="source-options" id="media-source-options">
          <label>
            Filter sources
            <select
              value={filter}
              onChange={(event) => {
                const nextFilter = event.target.value as
                  | MediaSourceKind
                  | "all";
                setFilter(nextFilter);
                setSourcePage(1);
                setSuggestionPage(1);
                const query =
                  nextFilter === "all" ? "" : `?source=${nextFilter}`;
                router.replace(`${pathname}${query}`, { scroll: false });
              }}
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
                {pagedSources.map((source) => (
                  <li key={source.id}>
                    <span>
                      <strong>{source.name}</strong>
                      <small>
                        {source.provider === "journalist_requests"
                          ? "JOURNALIST REQUESTS · RSS"
                          : source.kind.toUpperCase()}
                      </small>
                    </span>
                    <button
                      className="button-danger"
                      type="button"
                      onClick={() => setPendingDelete(source)}
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
            <PaginationControls
              label="configured sources"
              page={currentSourcePage}
              pageCount={sourcePageCount}
              setPage={setSourcePage}
            />
          </div>
          <div className="source-list">
            <h2>Suggested UAE sources</h2>
            <ul>
              {pagedSuggestions.map((source) => (
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
            <PaginationControls
              label="source suggestions"
              page={currentSuggestionPage}
              pageCount={suggestionPageCount}
              setPage={setSuggestionPage}
            />
          </div>
          {filter !== "api" ? (
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
              <label className="checkbox-label">
                <input name="journalistRequests" type="checkbox" />
                This feed contains journalist requests
              </label>
              <p className="field-hint">
                Request feeds use explicit deadline, expiry, expiration, or due
                date fields. Publication dates are never treated as deadlines.
              </p>
              <button
                className="button-secondary"
                type="submit"
                disabled={working}
              >
                Add RSS source
              </button>
            </form>
          ) : null}
          <button
            className="source-ingest"
            type="button"
            onClick={ingest}
            aria-busy={ingesting}
          >
            {ingesting ? "Ingesting media…" : "Ingest media"}
          </button>
          <p className="field-hint">
            Each run imports up to 25 items per source and 100 items total.
            Deleted items found again are restored with their existing history.
          </p>
          {pendingDelete ? (
            <AccessibleDialog
              title={`Delete ${pendingDelete.name}?`}
              description="PressRadar will stop ingesting new media from this source. You can add the source again later."
              onClose={() => setPendingDelete(null)}
            >
              <div className="actions">
                <button
                  className="button-danger"
                  type="button"
                  onClick={remove}
                  disabled={working}
                >
                  Delete source
                </button>
                <button
                  className="button-secondary"
                  type="button"
                  onClick={() => setPendingDelete(null)}
                  disabled={working}
                >
                  Cancel
                </button>
              </div>
            </AccessibleDialog>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function PaginationControls({
  label,
  page,
  pageCount,
  setPage,
}: Readonly<{
  label: string;
  page: number;
  pageCount: number;
  setPage: (page: number) => void;
}>) {
  return (
    <>
      <p className="pagination-note">
        Pagination appears when there are more than 5 items.
      </p>
      {pageCount > 1 ? (
        <nav className="pagination" aria-label={`${label} pagination`}>
          <button
            className="button-secondary"
            type="button"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <span>
            Page {page} of {pageCount}
          </span>
          <button
            className="button-secondary"
            type="button"
            disabled={page === pageCount}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
    </>
  );
}
