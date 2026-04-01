# fire-ems-exam-author

`응급처치학개론` 기출 분석, 요약집 생성, 모의고사 생성, 오답 만다라트 확장을 위한 Codex 전역 스킬 저장소입니다.

## 포함 내용

- [SKILL.md](./SKILL.md)
  - 스킬 트리거 조건, 워크플로, 출력 규칙
- [agents/openai.yaml](./agents/openai.yaml)
  - UI 메타데이터
- [references/](./references/)
  - 데이터 계약, 입력 규칙, 검수 체크리스트
- [scripts/init_exam_workspace.py](./scripts/init_exam_workspace.py)
  - 현재 작업 폴더에 표준 작업 디렉터리 생성
- [scripts/extract_source_text.py](./scripts/extract_source_text.py)
  - 원본 파일 수집 및 텍스트 추출
- [scripts/synthesize_reference_items.py](./scripts/synthesize_reference_items.py)
  - 기출문항이 없는 참고자료/지시문 업로드에서 규칙 기반 초안 문항 생성
- [scripts/run_analysis_pipeline.py](./scripts/run_analysis_pipeline.py)
  - 문항 구조화, 정답 확정/추정, 해설, 만다라트, 검수 큐, Markdown 출력까지 일괄 실행
- [references/mandalart-authoring.md](./references/mandalart-authoring.md)
  - `기출 1문항 -> 만다라트 1장 -> 변형문항 5~7개`와 4지 선다 전용 3x3 제작 규격
- [web/](./web/)
  - Next.js 운영 콘솔. 업로드, 분석 실행, 결과/검수 큐 확인을 웹에서 처리

## 지원 입력 형식

- PDF
- PNG / JPG / JPEG
- DOCX
- XLSX
- MD / TXT
- HWP
- HWPX

기본 처리 원칙:
- `HWPX`는 ZIP/XML 기반 추출을 우선 시도
- `HWP`는 전용 파서 우선, 실패 시 `PDF 재내보내기`를 기본 fallback으로 사용
- 기출문항이 직접 들어 있지 않으면 참고자료/지시문에서 규칙 기반 초안 문항 생성을 시도
- 정답표가 없으면 추정 정답과 `confidence`, `review_status`를 함께 기록

## 기본 사용법

작업 폴더에서 워크스페이스를 초기화합니다.

```bash
python3 /Users/chungji/.codex/skills/fire-ems-exam-author/scripts/init_exam_workspace.py .
```

소스 파일을 수집하고 텍스트를 추출합니다.

```bash
python3 /Users/chungji/.codex/skills/fire-ems-exam-author/scripts/extract_source_text.py --workspace . <source-file>...
```

이후 분석 파이프라인을 실행합니다.

```bash
python3 /Users/chungji/.codex/skills/fire-ems-exam-author/scripts/run_analysis_pipeline.py --workspace .
```

단계별로 실행하려면 아래 순서를 사용합니다.

```bash
python3 scripts/parse_exam_items.py --workspace .
python3 scripts/synthesize_reference_items.py --workspace .
python3 scripts/resolve_answers.py --workspace .
python3 scripts/build_explanations.py --workspace .
python3 scripts/build_mandalart.py --workspace .
python3 scripts/build_review_queue.py --workspace .
python3 scripts/render_past_analysis.py --workspace .
```

웹 프론트엔드는 `web/`에서 실행합니다.

```bash
cd /Users/chungji/fire-ems-exam-author/web
pnpm install
pnpm dev
```

기본 웹 흐름:
- 파일 업로드로 새 워크스페이스 생성
- 업로드 직후 Python 추출/분석 파이프라인 실행
- 워크스페이스 상세 페이지에서 결과/검수 큐/Markdown 출력 확인
- 같은 상세 페이지에서 `intake-manifest.json`, `exam-bank.json`, `review-queue.json`도 raw preview 가능
- 필요 시 재실행 버튼으로 현 워크스페이스 다시 분석

주요 API 경로:
- `GET /api/workspaces`
- `POST /api/workspaces`
- `GET /api/workspaces/:workspaceId`
- `POST /api/workspaces/:workspaceId/rerun`

생성되는 기본 폴더:

```text
./sources/
./sources/extracted/
./bank/
./outputs/
./review/
```

## 핵심 출력 규칙

- 사람용 결과물은 `Markdown`
- 재활용용 결과물은 `JSON`
- 둘 다 동시에 생성
- 기본 분석 단위는 `기출 1문항 -> 만다라트 1장 -> 변형문항 5~7개`
- 4지 선다형은 `출제의도 / 정답 근거 / 오답① / 오답② / 중심문항 / 오답③ / 조건변형 / 형식변형 / 피드백` 구조를 사용
- 웹 업로드 워크스페이스는 저장소 루트의 `workspaces/` 아래에 생성되며 Git 추적에서 제외됨
- 저신뢰 문항, 출처 충돌 문항, OCR 품질 저하 문항, 정답표 부재 문항은 `review/`로 이동
- 검수 완료 전에는 출판 반영용 최종본 생성 금지

## 저장소 목적

이 저장소는 스킬 자체를 버전 관리하기 위한 저장소입니다.
실제 작업 결과물은 이 저장소가 아니라, 사용자가 실행하는 현재 작업 폴더에 생성됩니다.
