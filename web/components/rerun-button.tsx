"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function RerunButton({ workspaceId }: { workspaceId: string }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  async function rerun() {
    setError(null);
    const response = await fetch(`/api/workspaces/${workspaceId}/rerun`, {
      method: "POST"
    });
    const payload = (await response.json()) as { error?: string };
    if (!response.ok) {
      setError(payload.error ?? "재실행에 실패했습니다.");
      return;
    }
    router.refresh();
  }

  return (
    <div className="rerun-box">
      <button
        type="button"
        className="secondary-button"
        disabled={isPending}
        onClick={() => {
          startTransition(() => {
            void rerun();
          });
        }}
      >
        {isPending ? "재실행 중..." : "현재 워크스페이스 재실행"}
      </button>
      {error ? <p className="inline-error">{error}</p> : null}
    </div>
  );
}
