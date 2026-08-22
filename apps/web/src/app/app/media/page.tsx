import { cookies } from "next/headers";
import Link from "next/link";

import { IngestMediaButton } from "@/components/ingest-media-button";
import { internalApiUrl } from "@/lib/api";
import type { MediaItem } from "@/lib/media-types";

export default async function MediaPage() {
  const response = await fetch(`${internalApiUrl}/media`, {
    headers: { cookie: (await cookies()).toString() },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Unable to load media");
  }
  const media = (await response.json()) as MediaItem[];

  return (
    <main className="page-shell">
      <section className="wide-card">
        <header className="page-header">
          <div>
            <p className="eyebrow">Simulated source</p>
            <h1>Media feed</h1>
          </div>
          <div className="actions">
            <Link href="/app">Clients</Link>
            <IngestMediaButton />
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
