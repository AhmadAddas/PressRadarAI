"use client";

import { startTransition, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { publicApiUrl } from "@/lib/api";

type SelectableItem = {
  id: string;
  label: string;
  content: ReactNode;
};

export function PaginatedSelectableList({
  items: initialItems,
  noun,
  endpoint,
  className,
  pageSize = 5,
}: Readonly<{
  items: SelectableItem[];
  noun: string;
  endpoint: string;
  className: string;
  pageSize?: number;
}>) {
  const router = useRouter();
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [pending, setPending] = useState<string[]>([]);
  const [countdown, setCountdown] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const items = initialItems.filter((item) => !deletedIds.has(item.id));
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const visible = items.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize,
  );
  const allSelected =
    items.length > 0 && items.every((item) => selected.has(item.id));

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(
      () => setCountdown((value) => value - 1),
      1000,
    );
    return () => window.clearTimeout(timer);
  }, [countdown]);

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((current) => {
      const next = new Set(current);
      for (const item of items) {
        if (allSelected) next.delete(item.id);
        else next.add(item.id);
      }
      return next;
    });
  }

  function warn(ids: string[]) {
    setPending([...new Set(ids)]);
    setCountdown(5);
  }

  async function confirmDelete() {
    if (!pending.length || countdown > 0) return;
    setDeleting(true);
    try {
      const results = await Promise.all(
        pending.map((id) =>
          fetch(`${publicApiUrl}/${endpoint}/${id}`, {
            method: "DELETE",
            credentials: "include",
          }),
        ),
      );
      if (results.some((response) => !response.ok)) {
        toast.error(`Unable to delete the selected ${noun} records.`);
        return;
      }
      const deleted = new Set(pending);
      setDeletedIds((current) => new Set([...current, ...deleted]));
      setSelected((current) => {
        const next = new Set(current);
        for (const id of deleted) next.delete(id);
        return next;
      });
      setPending([]);
      toast.success(
        `${deleted.size} ${noun}${deleted.size === 1 ? "" : " records"} deleted.`,
      );
      startTransition(() => router.refresh());
    } catch {
      toast.error("PressRadar is temporarily unavailable.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="selectable-list">
      <div className="selection-toolbar">
        <label>
          <input type="checkbox" checked={allSelected} onChange={toggleAll} />
          Select all
        </label>
        <button
          className="button-danger"
          type="button"
          disabled={!selected.size}
          onClick={() => warn([...selected])}
        >
          Delete selected ({selected.size})
        </button>
      </div>
      <ul className={className}>
        {visible.map((item) => (
          <li key={item.id} className="selectable-item">
            <div className="item-selection">
              <label>
                <input
                  type="checkbox"
                  checked={selected.has(item.id)}
                  onChange={() => toggle(item.id)}
                />
                Select {item.label}
              </label>
              <button
                className="button-danger button-compact"
                type="button"
                onClick={() => warn([item.id])}
              >
                Delete
              </button>
            </div>
            {item.content}
          </li>
        ))}
      </ul>
      {pageCount > 1 ? (
        <nav className="pagination" aria-label={`${noun} pagination`}>
          <button
            className="button-secondary"
            type="button"
            disabled={currentPage === 1}
            onClick={() => setPage((value) => value - 1)}
          >
            Previous
          </button>
          <span>
            Page {currentPage} of {pageCount}
          </span>
          <button
            className="button-secondary"
            type="button"
            disabled={currentPage === pageCount}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
      {pending.length ? (
        <div className="delete-warning" role="alert">
          <strong>
            Delete {pending.length} selected {noun}?
          </strong>
          <p>
            Only the selected {noun} will be deleted. Related records are kept
            for history and marked as orphaned when their original link is gone.
          </p>
          <div className="actions">
            <button
              className="button-danger"
              type="button"
              disabled={countdown > 0 || deleting}
              onClick={confirmDelete}
            >
              {countdown > 0 ? `Confirm in ${countdown}s` : "Confirm delete"}
            </button>
            <button
              className="button-secondary"
              type="button"
              disabled={deleting}
              onClick={() => setPending([])}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
