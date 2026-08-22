import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { internalApiUrl } from "@/lib/api";

type Identity = {
  name: string;
  email: string;
  workspace_id: string;
};

export default async function ProfilePage() {
  const response = await fetch(`${internalApiUrl}/auth/me`, {
    headers: { cookie: (await cookies()).toString() },
    cache: "no-store",
  }).catch(() => null);
  if (!response?.ok) {
    redirect("/signin");
  }
  const identity = (await response.json()) as Identity;

  return (
    <main className="page-shell profile-page">
      <section className="wide-card profile-card">
        <header className="page-header">
          <div>
            <p className="eyebrow">Account</p>
            <h1>Your profile</h1>
          </div>
          <Link className="button button-secondary" href="/app">
            Back to dashboard
          </Link>
        </header>
        <dl className="profile-details">
          <div>
            <dt>Name</dt>
            <dd>{identity.name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{identity.email}</dd>
          </div>
          <div>
            <dt>Workspace ID</dt>
            <dd className="workspace-id">{identity.workspace_id}</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
