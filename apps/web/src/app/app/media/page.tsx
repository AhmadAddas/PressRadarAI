import { cookies } from "next/headers";
import Link from "next/link";

import { IngestMediaButton } from "@/components/ingest-media-button";
import { MediaSourceManager } from "@/components/media-source-manager";
import { internalApiUrl } from "@/lib/api";
import type { MediaItem } from "@/lib/media-types";
import type {
  MediaSource,
  MediaSourceSuggestion,
} from "@/lib/media-source-types";

type Identity = { workspace_kind: "demo" | "prod" };

export default async function MediaPage() {
  const cookieHeader = (await cookies()).toString();
  const identityResponse = await fetch(`${internalApiUrl}/auth/me`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (!identityResponse.ok) {
    throw new Error("Unable to load workspace");
  }
  const identity = (await identityResponse.json()) as Identity;
  const response = await fetch(`${internalApiUrl}/media`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Unable to load media");
  }
  const media = (await response.json()) as MediaItem[];
  let sources: MediaSource[] = [];
  let suggestions: MediaSourceSuggestion[] = [];
  if (identity.workspace_kind === "prod") {
    const [sourcesResponse, suggestionsResponse] = await Promise.all([
      fetch(`${internalApiUrl}/media/sources`, {
        headers: { cookie: cookieHeader },
        cache: "no-store",
      }),
      fetch(`${internalApiUrl}/media/sources/suggestions`, {
        headers: { cookie: cookieHeader },
        cache: "no-store",
      }),
    ]);
    if (!sourcesResponse.ok || !suggestionsResponse.ok) {
      throw new Error("Unable to load media sources");
    }
    sources = (await sourcesResponse.json()) as MediaSource[];
    suggestions = (await suggestionsResponse.json()) as MediaSourceSuggestion[];
  }

  return (
    <main className="page-shell">
      <section className="wide-card">
        <header className="page-header">
          <div>
            <p className="eyebrow">Simulated source</p>
            <h1>Media feed</h1>
          </div>
          <div className="actions media-header-actions">
            <Link className="button button-secondary" href="/app">
              Dashboard
            </Link>
            {identity.workspace_kind === "demo" ? (
              <IngestMediaButton />
            ) : (
              <MediaSourceManager sources={sources} suggestions={suggestions} />
            )}
          </div>
        </header>
        {media.length ? (
          <ul className="media-list">
            {media.map((item) => (
              <li key={item.id}>
                <div className="media-meta">
                  <span>{item.source_type.replace("_", " ")}</span>
                  <span>{item.source}</span>
                  {item.deadline ? (
                    <strong>Deadline {formatTime(item.deadline)}</strong>
                  ) : null}
                </div>
                <h2>{item.headline}</h2>
                <p>{item.body}</p>
                <div className="topics">
                  {item.topics.map((topic) => (
                    <span key={topic}>{topic}</span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <h2>No media ingested</h2>
            <p>
              Run the simulated source to load deterministic demo stories and
              requests.
            </p>
          </div>
        )}
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
