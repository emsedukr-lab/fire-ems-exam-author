import type { WorkspaceStatus } from "../lib/workspaces";

const STATUS_LABELS: Record<WorkspaceStatus, string> = {
  approved: "검수 통과",
  empty: "문항 없음",
  needs_review: "검수 필요"
};

export function StatusPill({ status }: { status: WorkspaceStatus }) {
  return <span className={`status-pill status-${status}`}>{STATUS_LABELS[status]}</span>;
}
