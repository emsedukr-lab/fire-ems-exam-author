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

## 지원 입력 형식

- PDF
- PNG / JPG / JPEG
- DOCX
- XLSX
- HWP
- HWPX

기본 처리 원칙:
- `HWPX`는 ZIP/XML 기반 추출을 우선 시도
- `HWP`는 전용 파서 우선, 실패 시 `PDF 재내보내기`를 기본 fallback으로 사용
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
- 저신뢰 문항, 출처 충돌 문항, OCR 품질 저하 문항, 정답표 부재 문항은 `review/`로 이동
- 검수 완료 전에는 출판 반영용 최종본 생성 금지

## 저장소 목적

이 저장소는 스킬 자체를 버전 관리하기 위한 저장소입니다.
실제 작업 결과물은 이 저장소가 아니라, 사용자가 실행하는 현재 작업 폴더에 생성됩니다.
