"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

export function DemoSetupButton({
  initiallyReady = false,
}: Readonly<{ initiallyReady?: boolean }>) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [ready, setReady] = useState(initiallyReady);
  const [working, setWorking] = useState(false);

  async function setup() {
    setWorking(true);
    setError("");
    try {
      const response = await fetch(`${publicApiUrl}/demo/setup`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        setError("Unable to prepare the demo workspace.");
        return;
      }
      setReady(true);
      router.refresh();
    } catch {
      setError("PressRadar is temporarily unavailable.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="demo-action">
      <button
        type="button"
        className="demo-toggle"
        onClick={setup}
        disabled={working || ready}
        aria-pressed={ready}
        aria-label={
          working
            ? "Preparing demo workspace"
            : ready
              ? "Demo workspace loaded"
              : "Load demo workspace"
        }
      >
        <span className="toggle-switch" aria-hidden="true">
          <span />
        </span>
        <span>Demo workspace</span>
      </button>
      {error ? <p role="alert">{error}</p> : null}
    </div>
  );
}
