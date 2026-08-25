import Link from "next/link";
import { PublicAIControls } from "@/components/public-ai-controls";

export default function Home() {
  return (
    <main className="centered-shell landing-shell">
      <PublicAIControls />
      <section className="card">
        <p className="eyebrow">PressRadar</p>
        <h1>Turn media opportunities into timely pitches.</h1>
        <p>Sign in to your workspace or create one to get started.</p>
        <nav aria-label="Account">
          <Link className="button" href="/signup">
            Create account
          </Link>
          <Link className="button button-secondary" href="/signin">
            Sign in
          </Link>
        </nav>
      </section>
    </main>
  );
}
