"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { publicApiUrl } from "@/lib/api";

export function DemoSetupButton() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);

  async function setup() {
    setWorking(true);
    setMessage("");
    try {
      const response = await fetch(`${publicApiUrl}/demo/setup`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        setMessage("Unable to prepare the demo workspace.");
        return;
      }
      const result = (await response.json()) as {
        opportunities_created: number;
      };
      setMessage(
        result.opportunities_created
          ? `Demo ready with ${result.opportunities_created} opportunities.`
          : "Demo workspace is already ready.",
      );
      router.refresh();
    } catch {
      setMessage("PressRadar is temporarily unavailable.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="demo-action">
      <button type="button" onClick={setup} disabled={working}>
        {working ? "Preparing demo…" : "Load demo workspace"}
      </button>
      {message ? <p role="status">{message}</p> : null}
    </div>
  );
}
