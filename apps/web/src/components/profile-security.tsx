"use client";

import QRCode from "qrcode";
import Image from "next/image";
import { FormEvent, useRef, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";
import { OTPInput } from "@/components/otp-input";

export function ProfileSecurity({
  totpEnabled,
}: Readonly<{ totpEnabled: boolean }>) {
  const [challenge, setChallenge] = useState("");
  const [purpose, setPurpose] = useState<"setup_2fa" | "disable_2fa" | null>(
    null,
  );
  const [setup, setSetup] = useState<{ secret: string; qr: string } | null>(
    null,
  );
  const [passwordError, setPasswordError] = useState("");
  const [securityAction, setSecurityAction] = useState<
    "setup_2fa" | "disable_2fa" | null
  >(null);
  const [verifyingEmail, setVerifyingEmail] = useState(false);
  const [activating, setActivating] = useState(false);
  const securityRequestInFlight = useRef(false);
  const emailVerificationInFlight = useRef(false);
  const activationInFlight = useRef(false);

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const passwordForm = event.currentTarget;
    setPasswordError("");
    const form = new FormData(passwordForm);
    const currentPassword = String(form.get("current_password") ?? "");
    const newPassword = String(form.get("new_password") ?? "");
    const confirmation = String(form.get("confirm_new_password") ?? "");
    if (newPassword !== confirmation) {
      setPasswordError("The new passwords do not match.");
      return;
    }
    const response = await fetch(`${publicApiUrl}/auth/password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    if (!response.ok)
      return toast.error(
        (await response.json()).detail ?? "Unable to change password.",
      );
    passwordForm.reset();
    toast.success("Password changed.");
  }

  async function requestCode(nextPurpose: "setup_2fa" | "disable_2fa") {
    if (securityRequestInFlight.current) return;
    securityRequestInFlight.current = true;
    setSecurityAction(nextPurpose);
    setChallenge("");
    setPurpose(null);
    try {
      const response = await fetch(`${publicApiUrl}/auth/2fa/email-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ purpose: nextPurpose }),
      });
      if (!response.ok) return toast.error("Unable to send the email code.");
      setChallenge(
        ((await response.json()) as { challenge_id: string }).challenge_id,
      );
      setPurpose(nextPurpose);
      toast.info("A verification code was sent to your email.");
    } catch {
      toast.error("Unable to send the email code.");
    } finally {
      securityRequestInFlight.current = false;
      setSecurityAction(null);
    }
  }

  async function confirmEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!purpose || emailVerificationInFlight.current) return;
    emailVerificationInFlight.current = true;
    setVerifyingEmail(true);
    const code = String(new FormData(event.currentTarget).get("code") ?? "");
    const endpoint = purpose === "disable_2fa" ? "disable" : "setup";
    try {
      const response = await fetch(`${publicApiUrl}/auth/2fa/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ challenge_id: challenge, code }),
      });
      if (!response.ok)
        return toast.error(
          (await response.json()).detail ?? "Invalid email code.",
        );
      if (purpose === "disable_2fa") {
        toast.success("Two-factor authentication deactivated.");
        window.location.reload();
        return;
      }
      const result = (await response.json()) as {
        secret: string;
        provisioning_uri: string;
      };
      setChallenge("");
      setPurpose(null);
      setSetup({
        secret: result.secret,
        qr: await QRCode.toDataURL(result.provisioning_uri, {
          width: 220,
          margin: 1,
        }),
      });
    } catch {
      toast.error("Unable to verify the email code.");
    } finally {
      emailVerificationInFlight.current = false;
      setVerifyingEmail(false);
    }
  }

  async function activate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (activationInFlight.current) return;
    activationInFlight.current = true;
    setActivating(true);
    const code = String(new FormData(event.currentTarget).get("code") ?? "");
    try {
      const response = await fetch(`${publicApiUrl}/auth/2fa/enable`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ code }),
      });
      if (!response.ok)
        return toast.error("The authenticator code is incorrect.");
      toast.success("Two-factor authentication is active.");
      window.location.reload();
    } catch {
      toast.error("Unable to activate two-factor authentication.");
    } finally {
      activationInFlight.current = false;
      setActivating(false);
    }
  }

  return (
    <div className="profile-security">
      <section>
        <h2>Change password</h2>
        <form onSubmit={changePassword}>
          <label>
            Current password
            <input name="current_password" type="password" required />
          </label>
          <label>
            New password
            <input
              name="new_password"
              type="password"
              minLength={12}
              maxLength={128}
              required
            />
          </label>
          <label>
            Confirm new password
            <input
              name="confirm_new_password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              required
            />
          </label>
          {passwordError ? <p role="alert">{passwordError}</p> : null}
          <button type="submit">Change password</button>
        </form>
      </section>
      <section>
        <h2>Two-factor authentication</h2>
        <p>Status: {totpEnabled ? "Active" : "Inactive"}</p>
        <p className="sms-unavailable">
          SMS is unavailable until Twilio API keys are configured.
        </p>
        <p>
          Changing or deactivating two-factor authentication requires a code
          sent to your verified email address.
        </p>
        <div className="actions">
          <button
            className="button-secondary"
            type="button"
            disabled={securityAction !== null}
            aria-busy={securityAction === "setup_2fa"}
            onClick={() => requestCode("setup_2fa")}
          >
            {securityAction === "setup_2fa"
              ? "Sending email code…"
              : totpEnabled
                ? "Change 2FA"
                : "Set up 2FA"}
          </button>
          {totpEnabled ? (
            <button
              className="button-danger"
              type="button"
              disabled={securityAction !== null}
              aria-busy={securityAction === "disable_2fa"}
              onClick={() => requestCode("disable_2fa")}
            >
              {securityAction === "disable_2fa"
                ? "Sending email code…"
                : "Deactivate 2FA"}
            </button>
          ) : null}
        </div>
        {purpose && challenge ? (
          <form className="profile-email-verification" onSubmit={confirmEmail}>
            <p>
              Email reference:{" "}
              <strong>{challenge.slice(-6).toUpperCase()}</strong>
            </p>
            <OTPInput label="Email verification code" name="code" />
            <button
              type="submit"
              disabled={verifyingEmail}
              aria-busy={verifyingEmail}
            >
              {verifyingEmail ? "Verifying…" : "Verify email"}
            </button>
          </form>
        ) : null}
        {setup ? (
          <div className="totp-profile-setup">
            <Image
              className="totp-qr"
              src={setup.qr}
              alt="TOTP setup QR code"
              width={220}
              height={220}
              unoptimized
            />
            <div className="manual-key">
              <strong>Manual setup key</strong>
              <code>{setup.secret}</code>
            </div>
            <form className="totp-activation-form" onSubmit={activate}>
              <OTPInput label="Authenticator code" name="code" />
              <button
                type="submit"
                disabled={activating}
                aria-busy={activating}
              >
                {activating ? "Activating…" : "Activate 2FA"}
              </button>
            </form>
          </div>
        ) : null}
      </section>
    </div>
  );
}
