"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";
import type { LicenseDetails, LocalAIStatus } from "@/lib/local-ai-types";

export function LocalAIMenu() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<LocalAIStatus | null>(null);
  const [model, setModel] = useState("");
  const [license, setLicense] = useState<LicenseDetails | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [working, setWorking] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || status) return;

    async function loadStatus() {
      try {
        const response = await fetch(`${publicApiUrl}/local-ai`, {
          credentials: "include",
        });
        if (!response.ok) return;
        const result = (await response.json()) as LocalAIStatus;
        setStatus(result);
        setModel((current) => current || result.recommended_model);
      } catch {
        // The menu reports an unavailable runtime without interrupting the dashboard.
      }
    }

    void loadStatus();
  }, [open, status]);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent | KeyboardEvent) {
      if (
        event.type === "keydown" &&
        (event as KeyboardEvent).key === "Escape"
      ) {
        setOpen(false);
        return;
      }
      if (
        event.type === "pointerdown" &&
        !menuRef.current?.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", dismiss);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", dismiss);
    };
  }, [open]);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(
      () => setCountdown((value) => value - 1),
      1000,
    );
    return () => window.clearTimeout(timer);
  }, [countdown]);

  async function inspect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setLicense(null);
    try {
      const response = await fetch(`${publicApiUrl}/local-ai/license`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      if (!response.ok) {
        toast.error(
          await errorMessage(response, "Unable to inspect this model."),
        );
        return;
      }
      setLicense((await response.json()) as LicenseDetails);
      setCountdown(5);
    } catch {
      toast.error("PressRadar cannot reach the local AI service.");
    } finally {
      setWorking(false);
    }
  }

  async function clone() {
    if (!license || countdown > 0) return;
    setWorking(true);
    try {
      const response = await fetch(`${publicApiUrl}/local-ai/models`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, accepted_license: license.name }),
      });
      if (!response.ok) {
        toast.error(
          await errorMessage(response, "Unable to clone this model."),
        );
        return;
      }
      setStatus((await response.json()) as LocalAIStatus);
      setLicense(null);
      toast.success(`${model} is active.`);
    } catch {
      toast.error("PressRadar cannot reach the local AI service.");
    } finally {
      setWorking(false);
    }
  }

  async function setActive(active: boolean) {
    setWorking(true);
    try {
      const response = await fetch(`${publicApiUrl}/local-ai/active`, {
        method: active ? "POST" : "DELETE",
        credentials: "include",
      });
      if (!response.ok) {
        toast.error(
          `Unable to ${active ? "activate" : "deactivate"} Local AI.`,
        );
        return;
      }
      setStatus((await response.json()) as LocalAIStatus);
      toast.success(`Local AI ${active ? "activated" : "deactivated"}.`);
    } catch {
      toast.error("PressRadar cannot reach the local AI service.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="local-ai" ref={menuRef}>
      <button
        className="button-secondary local-ai-trigger"
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="local-ai-menu"
      >
        <OllamaIcon />
        Local AI
      </button>
      {open ? (
        <section className="local-ai-menu" id="local-ai-menu">
          <div className="local-ai-status">
            <span
              className={`status-dot ${status?.enabled && status.reachable ? "is-active" : ""}`}
              aria-hidden="true"
            />
            <div>
              <strong>
                {status?.enabled && status.reachable
                  ? "Active local AI"
                  : status?.enabled
                    ? "Local AI unavailable"
                    : "Local AI inactive"}
              </strong>
              <span>
                {status?.enabled && status.reachable
                  ? status.model
                  : status?.enabled
                    ? "Connect Ollama to use Local AI."
                    : status
                      ? "Clone an Ollama model to activate Local AI."
                      : "Checking Ollama…"}
              </span>
            </div>
          </div>
          {status?.enabled && status.reachable ? (
            <LicenseSummary
              license={status.license}
              title="Active model license"
            />
          ) : !status ? (
            <p role="status">Checking the Ollama service…</p>
          ) : null}
          {status ? (
            <div className="recommendation">
              <strong>Low-power VPS suggestion</strong>
              <p>{status.recommended_model}</p>
              <small>{status.recommendation}</small>
            </div>
          ) : null}
          <form className="local-ai-form" onSubmit={inspect}>
            <label>
              Ollama model name
              <input
                value={model}
                onChange={(event) => {
                  setModel(event.target.value);
                  setLicense(null);
                }}
                placeholder="qwen2.5:0.5b-instruct"
                required
                maxLength={200}
              />
            </label>
            <button
              className="button-secondary"
              type="submit"
              disabled={working}
            >
              Check license
            </button>
          </form>
          {license ? (
            <div className="license-confirmation">
              <LicenseSummary
                license={license}
                title="License found before cloning"
              />
              <small>
                Model downloads can consume significant disk, memory, CPU, and
                time on a VPS.
              </small>
              <button
                type="button"
                onClick={clone}
                disabled={working || countdown > 0}
              >
                {countdown > 0
                  ? `Clone in ${countdown}s`
                  : "Clone and activate"}
              </button>
            </div>
          ) : null}
          {status ? (
            <button
              className={status.enabled ? "button-danger" : "button-secondary"}
              type="button"
              onClick={() => setActive(!status.enabled)}
              disabled={working}
            >
              {status.enabled ? "Deactivate Local AI" : "Activate Local AI"}
            </button>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function LicenseSummary({
  license,
  title,
}: Readonly<{ license: LicenseDetails; title: string }>) {
  return (
    <div className="license-summary">
      <strong>{title}</strong>
      <span>{license.name}</span>
      <p>{license.summary}</p>
      {license.source_url ? (
        <a href={license.source_url} target="_blank" rel="noreferrer">
          View source on Hugging Face
        </a>
      ) : !license.known ? (
        <span>
          Search the internet for the publisher&apos;s full model license.
        </span>
      ) : null}
    </div>
  );
}

function OllamaIcon() {
  return (
    <svg className="ollama-icon" aria-hidden="true" viewBox="0 0 32 32">
      <path
        fill="currentColor"
        d="M9 5h3v6h8V5h3v7c2 1 4 4 4 8v7H5v-7c0-4 2-7 4-8V5Zm3 10c-2 0-3 2-3 5v3h14v-3c0-3-1-5-3-5h-8Zm0 2h2v3h-2v-3Zm6 0h2v3h-2v-3Z"
      />
    </svg>
  );
}

async function errorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || fallback;
  } catch {
    return fallback;
  }
}
