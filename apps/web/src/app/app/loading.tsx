export default function ApplicationLoading() {
  return (
    <main className="page-shell" aria-busy="true" aria-live="polite">
      <section className="wide-card loading-state">
        <p className="eyebrow">PressRadar</p>
        <h1>Loading your workspace…</h1>
        <p>Prioritizing the latest media opportunities.</p>
      </section>
    </main>
  );
}
