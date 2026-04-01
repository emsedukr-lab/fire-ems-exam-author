"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function UploadForm() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);

  async function submitForm(formData: FormData) {
    setError(null);
    const response = await fetch("/api/workspaces", {
      method: "POST",
      body: formData
    });

    const payload = (await response.json()) as { error?: string; workspaceId?: string };
    if (!response.ok || !payload.workspaceId) {
      setError(payload.error ?? "워크스페이스를 생성하지 못했습니다.");
      return;
    }
    router.push(`/workspaces/${payload.workspaceId}`);
    router.refresh();
  }

  return (
    <form
      className="upload-panel"
      onSubmit={(event) => {
        event.preventDefault();
        const formData = new FormData(event.currentTarget);
        startTransition(() => {
          void submitForm(formData);
        });
      }}
    >
      <div className="upload-headline">
        <p className="eyebrow">Launch Pad</p>
        <h2>기출 파일을 올리면 곧바로 분석 워크스페이스를 만듭니다.</h2>
        <p className="supporting-text">
          PDF, 이미지, DOCX, XLSX, MD/TXT, HWP/HWPX를 한 번에 넣고 Python 파이프라인을 그대로 실행합니다.
          기출문항이 없더라도 참고자료와 지시문에서 문항 초안을 자동 생성하도록 fallback이 동작합니다.
        </p>
      </div>

      <label className="field">
        <span>워크스페이스 이름</span>
        <input
          name="name"
          type="text"
          placeholder="예: 2024 응급처치학개론 1회"
          className="text-input"
        />
      </label>

      <label className="upload-dropzone">
        <span className="upload-title">원본 자료 선택</span>
        <span className="upload-copy">여러 파일을 한 번에 선택할 수 있습니다.</span>
        <input
          name="files"
          type="file"
          multiple
          required
          accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.md,.txt,.hwp,.hwpx"
          className="visually-hidden"
          onChange={(event) => {
            const names = Array.from(event.target.files ?? []).map((file) => file.name);
            setSelectedFiles(names);
          }}
        />
        <span className="upload-chip">파일 추가</span>
      </label>

      <div className="file-preview" aria-live="polite">
        {selectedFiles.length === 0 ? (
          <p className="file-empty">아직 선택된 파일이 없습니다.</p>
        ) : (
          selectedFiles.map((name) => (
            <span key={name} className="file-tag">
              {name}
            </span>
          ))
        )}
      </div>

      <div className="actions-row">
        <button type="submit" className="primary-button" disabled={isPending}>
          {isPending ? "워크스페이스 생성 중..." : "업로드 후 전체 분석"}
        </button>
        <p className="meta-note">처리 시간은 OCR 유무와 파일 수에 따라 달라집니다.</p>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}
    </form>
  );
}
