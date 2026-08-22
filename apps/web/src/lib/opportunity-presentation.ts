import type { OpportunityStatus } from "./opportunity-types";

export type UrgencyLevel = "overdue" | "critical" | "upcoming" | "none";

export const statusLabels: Record<OpportunityStatus, string> = {
  new: "New match",
  analyzing: "Analyzing",
  ready: "Ready for review",
  approved: "Approved",
  sending: "Sending",
  sent: "Sent",
  dismissed: "Dismissed",
  failed: "Needs attention",
};

export function urgencyLevel(
  deadline: string | null,
  now: Date = new Date(),
): UrgencyLevel {
  if (!deadline) return "none";
  const remaining = new Date(deadline).getTime() - now.getTime();
  if (remaining <= 0) return "overdue";
  if (remaining <= 60 * 60 * 1000) return "critical";
  if (remaining <= 24 * 60 * 60 * 1000) return "upcoming";
  return "none";
}

export const urgencyLabels: Record<Exclude<UrgencyLevel, "none">, string> = {
  overdue: "Deadline passed",
  critical: "Due within 1 hour",
  upcoming: "Due within 24 hours",
};
