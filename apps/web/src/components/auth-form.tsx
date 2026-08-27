"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, startTransition, useState } from "react";

import { publicApiUrl } from "@/lib/api";
import { PublicAIControls } from "@/components/public-ai-controls";

type AuthMode = "signin" | "signup";

export function AuthForm({ mode }: Readonly<{ mode: AuthMode }>) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [signupChallenge, setSignupChallenge] = useState<{
    user_id: string;
    challenge_id: string;
  } | null>(null);
  const isSignup = mode === "signup";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const body = Object.fromEntries(
      new FormData(event.currentTarget).entries(),
    );
    if (
      isSignup &&
      String(body.name ?? "")
        .trim()
        .split(/\s+/, 1)[0].length > 25
    ) {
      setError("First name must be 25 characters or fewer.");
      setSubmitting(false);
      return;
    }
    try {
      const response = await fetch(`${publicApiUrl}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        if (response.status === 428) setTotpRequired(true);
        setError(
          typeof payload.detail === "string"
            ? payload.detail
            : "Unable to continue",
        );
        return;
      }
      const payload = (await response.json()) as {
        onboarding_completed?: boolean;
        verification_required?: boolean;
        user_id?: string;
        challenge_id?: string;
      };
      if (
        response.status === 202 &&
        payload.verification_required &&
        payload.user_id &&
        payload.challenge_id
      ) {
        setSignupChallenge({
          user_id: payload.user_id,
          challenge_id: payload.challenge_id,
        });
        return;
      }
      router.push(
        payload.onboarding_completed === false ? "/onboarding" : "/app",
      );
      startTransition(() => router.refresh());
    } catch {
      setError("PressRadar is temporarily unavailable");
    } finally {
      setSubmitting(false);
    }
  }

  async function verifySignup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!signupChallenge) return;
    setSubmitting(true);
    setError("");
    try {
      const code = String(new FormData(event.currentTarget).get("code") ?? "");
      const response = await fetch(`${publicApiUrl}/auth/signup/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ ...signupChallenge, code }),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        setError(payload.detail ?? "Unable to verify this code");
        return;
      }
      router.push("/onboarding");
      startTransition(() => router.refresh());
    } catch {
      setError("PressRadar is temporarily unavailable");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main id="main-content" className="centered-shell auth-shell" tabIndex={-1}>
      <PublicAIControls />
      <section className="card" aria-labelledby="auth-title">
        <p className="eyebrow">PressRadar</p>
        <h1 id="auth-title">
          {isSignup ? "Create your workspace" : "Welcome back"}
        </h1>
        {signupChallenge ? (
          <form onSubmit={verifySignup}>
            <p>Enter the six-digit code sent to your email address.</p>
            <label>
              Email verification code
              <input
                name="code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                autoFocus
              />
            </label>
            {error ? <p role="alert">{error}</p> : null}
            <button type="submit" disabled={submitting} aria-busy={submitting}>
              Verify email
            </button>
          </form>
        ) : (
          <form onSubmit={submit}>
            {isSignup ? (
              <label>
                Name
                <input
                  name="name"
                  autoComplete="name"
                  required
                  maxLength={100}
                />
              </label>
            ) : null}
            <label>
              Email
              <input name="email" type="email" autoComplete="email" required />
            </label>
            {totpRequired ? (
              <label>
                Authenticator code
                <input
                  name="totp_code"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                />
              </label>
            ) : null}
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={isSignup ? "new-password" : "current-password"}
                minLength={isSignup ? 12 : 1}
                maxLength={128}
                required
              />
            </label>
            {isSignup ? <small>Use at least 12 characters.</small> : null}
            {error ? <p role="alert">{error}</p> : null}
            <button type="submit" disabled={submitting} aria-busy={submitting}>
              {isSignup ? "Create account" : "Sign in"}
            </button>
          </form>
        )}
        <p>
          {isSignup ? "Already have an account?" : "New to PressRadar?"}{" "}
          <Link href={isSignup ? "/signin" : "/signup"}>
            {isSignup ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </section>
    </main>
  );
}
