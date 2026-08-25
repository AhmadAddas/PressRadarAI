"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
import QRCode from "qrcode";
import { FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";

type Setup = { secret: string; provisioning_uri: string };

export function TOTPOnboarding() {
  const router = useRouter();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [qr, setQr] = useState("");
  const [skipOpen, setSkipOpen] = useState(false);
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    void fetch(`${publicApiUrl}/auth/2fa/setup`, {
      method: "POST",
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setSetup((await response.json()) as Setup);
      })
      .catch(() => toast.error("Unable to prepare two-factor authentication."));
  }, []);

  useEffect(() => {
    if (!setup) return;
    void QRCode.toDataURL(setup.provisioning_uri, {
      width: 240,
      margin: 1,
    }).then(setQr);
  }, [setup]);

  useEffect(() => {
    if (!skipOpen || countdown <= 0) return;
    const timer = window.setTimeout(
      () => setCountdown((value) => value - 1),
      1000,
    );
    return () => window.clearTimeout(timer);
  }, [skipOpen, countdown]);

  async function enable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = String(new FormData(event.currentTarget).get("code") ?? "");
    const response = await fetch(`${publicApiUrl}/auth/2fa/enable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ code }),
    });
    if (!response.ok) {
      toast.error("The authenticator code is incorrect.");
      return;
    }
    toast.success("Two-factor authentication is active.");
    router.replace("/app");
    router.refresh();
  }

  async function skip() {
    const response = await fetch(`${publicApiUrl}/auth/2fa/skip`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) return toast.error("Unable to save your choice.");
    toast.warning("Two-factor authentication was skipped.");
    router.replace("/app");
    router.refresh();
  }

  return (
    <section className="card totp-card" aria-labelledby="totp-title">
      <p className="eyebrow">Protect your account</p>
      <h1 id="totp-title">Set up two-factor authentication</h1>
      <p>
        Scan the QR code or enter the manual setup key in your authenticator
        app.
      </p>
      {qr ? (
        <Image
          className="totp-qr"
          src={qr}
          alt="TOTP setup QR code"
          width={240}
          height={240}
          unoptimized
        />
      ) : (
        <p>Preparing QR code…</p>
      )}
      {setup ? (
        <div className="manual-key">
          <strong>Manual setup key</strong>
          <code>{setup.secret}</code>
        </div>
      ) : null}
      <form onSubmit={enable}>
        <label>
          Six-digit authenticator code
          <input
            name="code"
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            required
          />
        </label>
        <button type="submit" disabled={!setup}>
          Activate 2FA
        </button>
      </form>
      <button
        className="button-secondary"
        type="button"
        onClick={() => {
          setCountdown(5);
          setSkipOpen(true);
        }}
      >
        Skip for now
      </button>
      <p className="sms-unavailable">
        SMS setup is unavailable until Twilio API keys are configured.
      </p>
      {skipOpen ? (
        <div className="modal-backdrop">
          <section
            className="confirmation-modal"
            role="alertdialog"
            aria-modal="true"
          >
            <h2>Continue without 2FA?</h2>
            <p>
              Your account will have less protection against stolen passwords.
            </p>
            <div className="actions">
              <button
                className="button-secondary"
                type="button"
                onClick={() => setSkipOpen(false)}
              >
                Keep 2FA
              </button>
              <button type="button" disabled={countdown > 0} onClick={skip}>
                {countdown > 0 ? `Skip in ${countdown}s` : "Skip 2FA"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
