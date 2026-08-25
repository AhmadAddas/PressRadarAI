import { ClientForm } from "@/components/client-form";

export default function NewClientPage() {
  return (
    <main id="main-content" className="page-shell" tabIndex={-1}>
      <section className="wide-card">
        <p className="eyebrow">Client management</p>
        <h1>Add a client</h1>
        <ClientForm />
      </section>
    </main>
  );
}
