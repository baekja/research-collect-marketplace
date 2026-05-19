---
name: research-collect
description: Use this skill when the user wants to collect academic papers from the web (arXiv, journal sites, search results) and register them in their Zotero library. Searches papers via the best available backend (firecrawl-mcp preferred, then exa-mcp, brave-search-mcp, or built-in web_search), normalizes metadata into Markdown with YAML frontmatter, and writes to Zotero in local or cloud mode (cloud mode auto-attaches PDFs via Unpaywall OA fallback). Triggers on Korean phrases like "논문 수집", "Zotero에 등록", "논문 정리", "참고문헌 모으기", and English phrases like "paper collection", "gather papers about X", "academic literature review", "import to Zotero". Also triggers when user mentions any of firecrawl, exa, brave-search, or Zotero in the context of academic research.
---

# research-collect

논문을 웹에서 수집해 Zotero 에 자동 등록하는 파이프라인 스킬. 검색 백엔드는 환경에 따라 자동 선택되며, Zotero 는 로컬/클라우드 모드로 자동 분기한다.

## When to use this skill

다음과 같은 자연어 요청이 들어오면 이 스킬이 발동한다:

- "arXiv 에서 transformer 논문 5편 모아서 Zotero 에 넣어줘"
- "graph neural network 키워드로 최근 논문 10편 정리해줘"
- "<도메인> 참고문헌 자동으로 가져와줘"
- "gather papers about diffusion models and import them to my Zotero"

본 스킬이 다루는 워크플로우는 3단계:

1. **검색** — 사용 가능한 MCP/내장 도구 중 가장 적합한 백엔드로 메타데이터 추출
2. **정규화·등록** — 결정론적 Python 파이프라인(`research_collect`) 으로 Markdown 변환 + Zotero 등록
3. **(선택) 검증** — `zotero-mcp` 가 있으면 등록된 컬렉션 조회로 확인

## Prerequisites check

발동 시 다음을 자동 확인하고, 누락 시 사용자에게 명시적 안내한다 (자동 설치 금지):

| 자원 | 확인 방법 | 누락 시 안내 |
|------|----------|-------------|
| 검색 백엔드 (MCP) | 사용 가능한 도구 목록에 `firecrawl_search` · `exa_search` · `brave_web_search` 중 하나라도 있는지 | 없으면 내장 `web_search` 로 fallback (정상) |
| `zotero-mcp` (검증 단계 전용) | 사용 가능한 도구 목록 | 없으면 Step 3 skip |
| Python 패키지 | `python3 -c "from research_collect import ingest"` 성공 여부 | 실패 시 `pip install -e .` 안내 |
| `.env` | `cwd/.env` 또는 환경변수 | 없어도 local 모드로 동작 |

## Step 1: Search (pluggable backend)

검색은 백엔드 추상화 위에서 동작한다. 발동 시 사용 가능한 MCP 도구를 우선순위대로 시도한다:

```
1. firecrawl_search 가 등록되어 있으면 → firecrawl (structured extraction 선호)
2. 없으면 exa_search → exa
3. 없으면 brave_web_search → brave + web_fetch
4. 모두 없으면 내장 web_search + web_fetch
```

각 백엔드의 raw output 은 호출 직후 다음 표준 스키마로 변환해 `./data/raw.json` 에 저장한다. 이후 단계의 Python 파이프라인은 이 스키마만 본다 — 백엔드 차이는 여기서 흡수된다.

```json
[
  {
    "title": "string (required)",
    "authors": ["string"],
    "year": 2025,
    "doi": "string (optional)",
    "abstract": "string (optional)",
    "pdf_url": "string (optional)",
    "source_url": "string (optional)"
  }
]
```

`data/` 가 없으면 사용자에게 명시적으로 안내한 뒤 `mkdir -p ./data` 를 실행한다.

## Step 2: Normalize and register (deterministic)

기본 입력 위치는 사용자 프로젝트 cwd 의 `./data/raw.json`. 출력 디렉토리도 cwd 기준 `./data/papers` · `./data/pdfs`. 다른 위치를 원하면 `--raw <path>` 등으로 명시.

실행 명령 (반드시 이 형태):

```bash
python3 -m research_collect \
    --raw data/raw.json \
    --out data/papers \
    --pdf-dir data/pdfs \
    --collection "<컬렉션 이름>"
```

스크립트는:

1. `.env` 를 자동 로드 → `connect()` 가 env 기반 모드 결정 (`[mode: local|cloud]` 출력)
2. 각 record 를 `normalize_record` 로 정리 → `bib_key` 생성
3. Markdown 작성 → `data/papers/<bibkey>.md`
4. Zotero 등록 (mode 별 분기)
5. cloud 모드 + `pdf_url` 비고 `doi` 있으면 Unpaywall OA fallback → `httpx` 다운로드 → `attachment_simple`
6. 모드, 등록 카운트, PDF 카운트, `oa_resolved_via_unpaywall` 카운트 출력

## Step 3: Verify (optional)

`zotero-mcp` 가 등록되어 있으면 컬렉션 조회로 검증한다:

```
"<컬렉션 이름> 컬렉션 최근 5건과 각 child PDF 보여줘"
```

없으면 Step 2 의 stdout 출력 (`[mode: local|cloud]` 라인 + 카운트들) 만으로 사용자에게 보고한다.

## Mode selection logic

`zotero_writer.connect()` 가 환경변수를 보고 자동 선택. 한 호출 안에서는 단일 모드.

| 항목 | local | cloud |
|------|-------|-------|
| 환경변수 | (없음) | `ZOTERO_USER_ID` + `ZOTERO_API_KEY` |
| 신규 item | connector `/saveItems` | `pyzotero create_items` |
| item key 응답 | ❌ 빈 body | ✅ |
| PDF 첨부 | ❌ | ✅ (`httpx` 다운로드 → `attachment_simple`) |
| OA 자동 검색 | ❌ | ✅ `UNPAYWALL_EMAIL` 있으면 paywall DOI 도 Unpaywall fallback |
| item 삭제 | ❌ 데스크탑 수동 | ✅ `delete_item` |
| 보안 | 키 노출 0 | 키 관리 필요 |

env 가 비면 자동으로 local 모드로 회귀하고 PDF 단계는 skip 된다.

## Known limitations

Zotero 로컬 API 의 write 한계 — 왜 두 모드가 필요한지:

| 동작 | HTTP | 결과 | 우리가 쓰는 채널 |
|------|------|------|------------------|
| `GET /api/users/0/collections` | 200 | OK | `pyzotero zot.collections()` |
| `POST /api/users/0/collections` | 200 | 컬렉션 생성 OK | `pyzotero zot.create_collections()` |
| `GET /api/items/new?itemType=journalArticle` | **404** | "No endpoint found" | 폴백 dict 로 우회 |
| `GET /api/items/new?itemType=attachment` | **404** | 동일 | `attachment_simple` 도 깨짐 |
| `POST /api/users/0/items` | **400** | "Endpoint does not support method" | local→connector 우회, cloud→OK |
| `DELETE /api/users/0/items/<key>` | **501** | "Method not implemented" | local→데스크탑 수동, cloud→OK |
| `POST /connector/saveItems` | 201 | 신규 item 등록 OK, body 빈 응답 | local 의 메인 쓰기 채널 |
| `POST /connector/saveItems` + `attachments[].url` | 201 | item 만 생기고 **PDF 다운로드는 트리거 안 됨** | — |
| `POST /connector/savePage` | **404** | "No endpoint found" | — |

→ **로컬 모드만으로는 PDF 자동 첨부 불가능.** PDF 가 필요하면 cloud 모드 활성화 (`ZOTERO_USER_ID` + `ZOTERO_API_KEY`).

## Troubleshooting

학생 시연 중 자주 막히는 6가지:

1. **`npx` 가 느리거나 실패** — npm registry 차단. `claude mcp add ...` 재실행 또는 `uvx` 변형 시도.
2. **Zotero MCP `connection refused`** — Zotero 앱이 닫혀 있거나 *Allow other applications* 옵션 꺼짐. 데스크탑 앱 확인.
3. **`claude mcp add` 후 tool 안 보임** — Claude Code 세션 재시작 필요.
4. **`UnsupportedParamsError 400` / `Method not implemented 501`** — 로컬 Zotero API write 한계. cloud 모드로 전환.
5. **`[mode: local]` 인데 PDF 가 안 들어감** — `ZOTERO_USER_ID`·`ZOTERO_API_KEY` 누락. `.env` 채우고 재실행.
6. **`oa_resolved_via_unpaywall: 0`** — `UNPAYWALL_EMAIL` 누락이거나 진짜 OA 없음. paywall 저널 대다수는 OA 사본 없는 게 정상.

## See also

`./references/` 의 추가 문서:

- `zotero_local_limits.md` — 로컬 API write 한계의 자세한 HTTP 표
- `unpaywall_setup.md` — `UNPAYWALL_EMAIL` 설정법, ToS, 동작 검증
- `search_backends.md` — firecrawl / exa / brave / web_search 백엔드별 호출법과 raw.json 변환 예시
