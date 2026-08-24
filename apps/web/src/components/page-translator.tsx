"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { languageEvent, languageStorageKey } from "@/components/language-menu";
import { publicApiUrl } from "@/lib/api";
import { languageByCode } from "@/lib/languages";

export function PageTranslator({
  children,
}: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const rootRef = useRef<HTMLDivElement>(null);
  const originals = useRef(new WeakMap<Text, string>());
  const startupTimer = useRef<number | null>(null);
  const [translating, setTranslating] = useState(false);

  const translate = useCallback(async (code: string) => {
    const language = languageByCode(code);
    document.documentElement.lang = language.code;
    document.documentElement.dir = language.rtl ? "rtl" : "ltr";
    const nodes = textNodes(rootRef.current);
    for (const node of nodes) {
      if (!originals.current.has(node)) originals.current.set(node, node.data);
    }
    if (language.code === "en") {
      for (const node of nodes)
        node.data = originals.current.get(node) ?? node.data;
      return;
    }

    const translatable = nodes.filter((node) =>
      (originals.current.get(node) ?? "").trim(),
    );
    if (!translatable.length) return;
    setTranslating(true);
    try {
      for (let offset = 0; offset < translatable.length; offset += 100) {
        const batch = translatable.slice(offset, offset + 100);
        const texts = batch.map((node) =>
          (originals.current.get(node) ?? node.data).trim(),
        );
        const response = await fetch(`${publicApiUrl}/local-ai/translate`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language_code: language.code, texts }),
        });
        if (!response.ok) throw new Error();
        const result = (await response.json()) as { translations: string[] };
        if (result.translations.length !== batch.length) throw new Error();
        batch.forEach((node, index) => {
          node.data = preserveWhitespace(
            originals.current.get(node) ?? node.data,
            result.translations[index] ?? "",
          );
        });
      }
    } catch {
      document.documentElement.lang = "en";
      document.documentElement.dir = "ltr";
      localStorage.setItem(languageStorageKey, "en");
      for (const node of nodes)
        node.data = originals.current.get(node) ?? node.data;
      toast.error(
        "Local AI could not translate this page. English was restored.",
      );
    } finally {
      setTranslating(false);
    }
  }, []);

  useEffect(() => {
    startupTimer.current = window.setTimeout(() => {
      void translate(localStorage.getItem(languageStorageKey) ?? "en");
    }, 0);
    return () => {
      if (startupTimer.current !== null)
        window.clearTimeout(startupTimer.current);
    };
  }, [pathname, translate]);

  useEffect(() => {
    const changeLanguage = (event: Event) => {
      const code = (event as CustomEvent<string>).detail;
      if (startupTimer.current !== null)
        window.clearTimeout(startupTimer.current);
      localStorage.setItem(languageStorageKey, code);
      void translate(code);
    };
    window.addEventListener(languageEvent, changeLanguage);
    return () => window.removeEventListener(languageEvent, changeLanguage);
  }, [translate]);

  return (
    <div ref={rootRef} className="translated-page" aria-busy={translating}>
      {translating ? (
        <div className="translation-progress" role="status" data-no-translate>
          Translating with Local AI…
        </div>
      ) : null}
      {children}
    </div>
  );
}

function textNodes(root: HTMLElement | null): Text[] {
  if (!root) return [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (
        !parent ||
        parent.closest("[data-no-translate]") ||
        parent.closest("script, style, textarea, input, select, option, svg")
      ) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const nodes: Text[] = [];
  while (walker.nextNode()) nodes.push(walker.currentNode as Text);
  return nodes;
}

function preserveWhitespace(original: string, translated: string): string {
  const leading = original.match(/^\s*/)?.[0] ?? "";
  const trailing = original.match(/\s*$/)?.[0] ?? "";
  return `${leading}${translated.trim()}${trailing}`;
}
