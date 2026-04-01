"use client";

export default function Error({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="shell">
      <section className="hero-card">
        <p className="eyebrow">Fatal State</p>
        <h1>프론트엔드에서 복구할 수 없는 오류가 발생했습니다.</h1>
        <p className="supporting-text">{error.message}</p>
        <div className="actions-row">
          <button type="button" className="primary-button" onClick={() => reset()}>
            다시 시도
          </button>
        </div>
      </section>
    </main>
  );
}
