---
description: arXiv·Google Scholar 검색 → Zotero 등록 파이프라인을 한 줄로 실행
argument-hint: <검색 키워드> [--collection <이름>] [--limit <N>]
---

# research-collect 한 줄 실행

사용자 인자: `$ARGUMENTS`

다음을 순차 실행하라:

1. **research-collect skill 발동**: 이 커맨드는 `research-collect` skill 의 명시적 진입점이다. `SKILL.md` 의 Step 1-3 을 그대로 따른다.
2. **인자 파싱**:
   - 첫 토큰 → 검색 키워드
   - `--collection <이름>` 가 있으면 컬렉션명 (없으면 `AutoImport`)
   - `--limit <N>` 가 있으면 가져올 편수 (없으면 10)
3. **실행**:
   - Step 1 (Search): SKILL.md 의 백엔드 fallback chain 으로 `./data/raw.json` 생성
   - Step 2 (Register): `python3 -m research_collect --raw data/raw.json --out data/papers --pdf-dir data/pdfs --collection "<컬렉션명>"`
   - Step 3 (Verify): `zotero-mcp` 있으면 최근 5건 조회
4. **결과 보고**: `[mode: local|cloud]` · 등록 카운트 · PDF 첨부 카운트(cloud만) · OA 검색 카운트
