"use client";

import QRCode from "qrcode";
import Image from "next/image";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";

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

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = Object.fromEntries(
      new FormData(event.currentTarget).entries(),
    );
    const response = await fetch(`${publicApiUrl}/auth/password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    });
    if (!response.ok)
      return toast.error(
        (await response.json()).detail ?? "Unable to change password.",
      );
    event.currentTarget.reset();
    toast.success("Password changed.");
  }

  async function requestCode(nextPurpose: "setup_2fa" | "disable_2fa") {
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
  }

  async function confirmEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!purpose) return;
    const code = String(new FormData(event.currentTarget).get("code") ?? "");
    const endpoint = purpose === "disable_2fa" ? "disable" : "setup";
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
    setSetup({
      secret: result.secret,
      qr: await QRCode.toDataURL(result.provisioning_uri, {
        width: 220,
        margin: 1,
      }),
    });
  }

  async function activate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = String(new FormData(event.currentTarget).get("code") ?? "");
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
          <button type="submit">Change password</button>
        </form>
      </section>
      <section>
        <h2>Two-factor authentication</h2>
        <p>Status: {totpEnabled ? "Active" : "Inactive"}</p>
        <div className="actions">
          <button
            className="button-secondary"
            type="button"
            onClick={() => requestCode("setup_2fa")}
          >
            {totpEnabled ? "Change 2FA" : "Set up 2FA"}
          </button>
          {totpEnabled ? (
            <button
              className="button-danger"
              type="button"
              onClick={() => requestCode("disable_2fa")}
            >
              Deactivate 2FA
            </button>
          ) : null}
        </div>
        <p className="sms-unavailable">
          SMS is unavailable until Twilio API keys are configured.
        </p>
        {purpose && challenge ? (
          <form onSubmit={confirmEmail}>
            <label>
              Email verification code
              <input
                name="code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
              />
            </label>
            <button type="submit">Verify email</button>
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
            <form onSubmit={activate}>
              <label>
                Authenticator code
                <input
                  name="code"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                />
              </label>
              <button type="submit">Activate 2FA</button>
            </form>
          </div>
        ) : null}
      </section>
    </div>
  );
}
