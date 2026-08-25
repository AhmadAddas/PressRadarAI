"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  defaultLanguage,
  languageByCode,
  languages,
  type Language,
} from "@/lib/languages";
import { publicApiUrl } from "@/lib/api";
import type { PublicLocalAIStatus } from "@/lib/local-ai-types";

export const languageEvent = "pressradar:language";
export const languageStorageKey = "pressradar-language";

export function LanguageMenu({
  status,
}: Readonly<{ status?: PublicLocalAIStatus | null }>) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Language>(defaultLanguage);
  const [aiStatus, setAIStatus] = useState<PublicLocalAIStatus | null>(
    status ?? null,
  );
  const menuRef = useRef<HTMLDivElement>(null);
  const matches = languages.filter((language) =>
    `${language.name} ${language.code}`
      .toLocaleLowerCase()
      .includes(query.toLocaleLowerCase()),
  );

  useEffect(() => {
    if (status !== undefined) {
      setAIStatus(status);
      return;
    }
    let cancelled = false;
    void fetch(`${publicApiUrl}/local-ai/public-status`)
      .then(async (response) => {
        if (!response.ok) return;
        const result = (await response.json()) as PublicLocalAIStatus;
        if (!cancelled) setAIStatus(result);
      })
      .catch(() => {
        if (!cancelled) setAIStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, [status]);

  useEffect(() => {
    const timer = window.setTimeout(
      () =>
        setSelected(
          languageByCode(localStorage.getItem(languageStorageKey) ?? "en"),
        ),
      0,
    );
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent | KeyboardEvent) {
      if (
        event.type === "keydown" &&
        (event as KeyboardEvent).key === "Escape"
      ) {
        setOpen(false);
      } else if (
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

  function choose(language: Language) {
    if (language.code !== "en" && !aiStatus?.translation_available) return;
    localStorage.setItem(languageStorageKey, language.code);
    setSelected(language);
    setOpen(false);
    setQuery("");
    window.dispatchEvent(
      new CustomEvent(languageEvent, { detail: language.code }),
    );
    if (language.code !== "en") {
      toast.info(
        `Switching Local AI to ${aiStatus?.translation_model} for translation.`,
      );
    }
  }

  return (
    <div className="language-picker" ref={menuRef} data-no-translate>
      <button
        className="button-secondary language-trigger"
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="language-menu"
      >
        <span aria-hidden="true">{selected.flag}</span>
        <span>{selected.name}</span>
        <span aria-hidden="true">▾</span>
      </button>
      {open ? (
        <section className="language-menu" id="language-menu">
          <label>
            Search languages
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Arabic, French, Hindi…"
              autoFocus
            />
          </label>
          <div className="language-list">
            {matches.map((language) => (
              <button
                className={language.code === selected.code ? "is-selected" : ""}
                type="button"
                key={language.code}
                onClick={() => choose(language)}
                disabled={
                  language.code !== "en" && !aiStatus?.translation_available
                }
                title={
                  language.code !== "en" && !aiStatus?.translation_available
                    ? "Activate Local AI and install the translation model first."
                    : undefined
                }
              >
                <span aria-hidden="true">{language.flag}</span>
                <span>{language.name}</span>
              </button>
            ))}
          </div>
          {!matches.length ? <p>No matching language.</p> : null}
          <small>
            {aiStatus?.translation_available
              ? `Non-English pages use ${aiStatus.translation_model} privately.`
              : "Non-English languages require active Local AI and its translation model."}
          </small>
        </section>
      ) : null}
    </div>
  );
}
