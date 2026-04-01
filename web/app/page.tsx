import Link from "next/link";

import { StatusPill } from "../components/status-pill";
import { UploadForm } from "../components/upload-form";
import { listWorkspaces } from "../lib/workspaces";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export default async function HomePage() {
  const workspaces = await listWorkspaces();

  return (
    <main className="shell">
      <div className="shell-grid">
        <section className="hero-card">
          <div className="hero-copy">
            <p className="eyebrow">Next.js Console</p>
            <h1>응급처치학개론 문항 제작을 브라우저에서 바로 운영합니다.</h1>
            <p className="supporting-text">
              업로드, 분석 실행, 오답별 4지 선다 전용 만다라트 검토, Markdown 결과 확인까지 한 화면에서 다룹니다.
            </p>
          </div>
          <div className="hero-stats">
            <article className="stat-card accent-red">
              <span className="stat-number">{workspaces.length}</span>
              <span className="stat-label">워크스페이스</span>
            </article>
            <article className="stat-card accent-amber">
              <span className="stat-number">
                {workspaces.reduce((sum, workspace) => sum + workspace.counts.examItems, 0)}
              </span>
              <span className="stat-label">분석 문항</span>
            </article>
            <article className="stat-card accent-mint">
              <span className="stat-number">
                {workspaces.reduce((sum, workspace) => sum + workspace.counts.reviewEntries, 0)}
              </span>
              <span className="stat-label">검수 큐</span>
            </article>
          </div>
        </section>

        <UploadForm />

        <section className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Workspace Deck</p>
              <h2>최근 작업</h2>
            </div>
            <span className="panel-badge">{workspaces.length}개</span>
          </div>

          {workspaces.length === 0 ? (
            <div className="empty-state">
              <h3>아직 생성된 워크스페이스가 없습니다.</h3>
              <p>
                첫 번째 기출 세트를 올리면 `sources`, `bank`, `outputs`, `review`가 자동으로 구성됩니다.
              </p>
            </div>
          ) : (
            <div className="workspace-list">
              {workspaces.map((workspace) => (
                <Link
                  key={workspace.id}
                  href={`/workspaces/${workspace.id}`}
                  className="workspace-card"
                >
                  <div className="workspace-card-head">
                    <div>
                      <h3>{workspace.name}</h3>
                      <p>{formatDate(workspace.updatedAt)} 갱신</p>
                    </div>
                    <StatusPill status={workspace.status} />
                  </div>

                  <dl className="workspace-metrics">
                    <div>
                      <dt>문항</dt>
                      <dd>{workspace.counts.examItems}</dd>
                    </div>
                    <div>
                      <dt>변형</dt>
                      <dd>{workspace.counts.variantItems}</dd>
                    </div>
                    <div>
                      <dt>검수</dt>
                      <dd>{workspace.counts.reviewEntries}</dd>
                    </div>
                    <div>
                      <dt>오답 카드</dt>
                      <dd>{workspace.counts.distractorRecords}</dd>
                    </div>
                  </dl>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
