import { TOTPOnboarding } from "@/components/totp-onboarding";

export default function OnboardingPage() {
  return (
    <main id="main-content" className="centered-shell" tabIndex={-1}>
      <TOTPOnboarding />
    </main>
  );
}
