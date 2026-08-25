"use client";

export default function ApplicationError({ reset }: { reset: () => void }) {
  return (
    <main id="main-content" className="page-shell" tabIndex={-1}>
      <section className="wide-card error-state" role="alert">
        <p className="eyebrow">Workspace unavailable</p>
        <h1>We couldn&apos;t load PressRadar.</h1>
        <p>Your data is unchanged. Try loading the workspace again.</p>
        <button type="button" onClick={reset}>
          Try again
        </button>
      </section>
    </main>
  );
}
