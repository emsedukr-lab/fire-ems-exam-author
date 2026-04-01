import Link from "next/link";

export default function NotFound() {
  return (
    <main className="shell">
      <section className="hero-card">
        <p className="eyebrow">Not Found</p>
        <h1>요청한 워크스페이스를 찾을 수 없습니다.</h1>
        <p className="supporting-text">
          주소가 잘못됐거나 아직 생성되지 않은 워크스페이스일 수 있습니다. 업로드 화면으로 돌아가 새 분석 세트를 시작하세요.
        </p>
        <div className="actions-row">
          <Link href="/" className="primary-button">
            홈으로 돌아가기
          </Link>
        </div>
      </section>
    </main>
  );
}
