"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

export function DemoSetupButton({
  workspaceKind,
}: Readonly<{ workspaceKind: "demo" | "prod" }>) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  async function setup() {
    const target = workspaceKind === "demo" ? "prod" : "demo";
    setWorking(true);
    setError("");
    try {
      const response = await fetch(`${publicApiUrl}/auth/workspace`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_kind: target }),
      });
      if (!response.ok) {
        setError("Unable to switch workspaces.");
        return;
      }
      if (target === "demo") {
        const demoResponse = await fetch(`${publicApiUrl}/demo/setup`, {
          method: "POST",
          credentials: "include",
        });
        if (!demoResponse.ok) {
          setError("Demo selected, but its data could not be prepared.");
          return;
        }
      }
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
        disabled={working}
        aria-pressed={workspaceKind === "demo"}
        aria-label={
          working
            ? "Preparing demo workspace"
            : workspaceKind === "demo"
              ? "Switch to Prod workspace"
              : "Switch to Demo workspace"
        }
      >
        <span className="toggle-switch" aria-hidden="true">
          <span />
        </span>
        <span>{workspaceKind === "demo" ? "Demo" : "Prod"} workspace</span>
      </button>
      {error ? <p role="alert">{error}</p> : null}
    </div>
  );
}
