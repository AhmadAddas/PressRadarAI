import { cookies } from "next/headers";
import Link from "next/link";

import { IngestMediaButton } from "@/components/ingest-media-button";
import { ExpandableText } from "@/components/expandable-text";
import { DeadlineEditor } from "@/components/deadline-editor";
import { MediaSourceManager } from "@/components/media-source-manager";
import { PaginatedSelectableList } from "@/components/paginated-selectable-list";
import { internalApiUrl } from "@/lib/api";
import { filterMedia, type MediaFilter } from "@/lib/media-filter";
import type { MediaItem } from "@/lib/media-types";
import { formatSourceType } from "@/lib/media-presentation";
import type {
  MediaSource,
  MediaSourceSuggestion,
} from "@/lib/media-source-types";

type Identity = { workspace_kind: "demo" | "prod" };
export default async function MediaPage({
  searchParams,
}: Readonly<{ searchParams: Promise<{ source?: string }> }>) {
  const source = (await searchParams).source;
  const mediaFilter: MediaFilter =
    source === "api" || source === "rss" ? source : "all";
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
  const media = filterMedia(
    (await response.json()) as MediaItem[],
    mediaFilter,
  );
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
    <main id="main-content" className="page-shell" tabIndex={-1}>
      <section className="wide-card">
        <header className="page-header">
          <div>
            <p className="eyebrow">Source</p>
            <h1>Media feed</h1>
          </div>
          <div className="actions media-header-actions">
            <Link className="button button-secondary" href="/app">
              Dashboard
            </Link>
            {identity.workspace_kind === "demo" ? (
              <IngestMediaButton />
            ) : (
              <MediaSourceManager
                sources={sources}
                suggestions={suggestions}
                initialFilter={mediaFilter}
              />
            )}
          </div>
        </header>
        {media.length ? (
          <PaginatedSelectableList
            key={media.map((item) => item.id).join(":")}
            noun="media item"
            endpoint="media"
            className="media-list"
            items={media.map((item) => ({
              id: item.id,
              label: item.headline,
              content: (
                <article>
                  <div className="media-meta">
                    <span>{formatSourceType(item.source_type)}</span>
                    <span>{item.source}</span>
                    <DeadlineEditor
                      mediaItemId={item.id}
                      deadline={item.deadline}
                    />
                  </div>
                  <h2>{item.headline}</h2>
                  <ExpandableText text={item.body} />
                  <div className="topics">
                    {item.topics.map((topic) => (
                      <span key={topic}>{topic}</span>
                    ))}
                  </div>
                </article>
              ),
            }))}
          />
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
