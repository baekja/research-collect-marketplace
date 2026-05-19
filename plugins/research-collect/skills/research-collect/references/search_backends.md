# 검색 백엔드 호출법과 raw.json 변환

본 plugin 은 검색 백엔드에 종속되지 않는다 (Constitution §0.2). SKILL.md 의 Step 1 에서 어떤 백엔드가 선택되든 결과는 `./data/raw.json` 표준 스키마로 통일된다. 이 문서는 백엔드별 호출 패턴과 raw.json 변환 예시.

## 표준 스키마

모든 백엔드 출력은 다음 스키마로 변환해야 한다:

```json
[
  {
    "title": "...",          // required
    "authors": ["..."],      // required, ≥1
    "year": 2025,            // required, integer
    "doi": "...",            // optional
    "abstract": "...",       // optional
    "pdf_url": "...",        // optional
    "source_url": "..."      // optional
  }
]
```

## 백엔드별 가이드

### 1. firecrawl-mcp (선호)

- 도구: `firecrawl_search`, `firecrawl_extract`, `firecrawl_scrape`
- 장점: structured extraction 으로 author·year·abstract 까지 직접 추출 가능. arXiv 페이지에 가장 정확.
- 단점: `FIRECRAWL_API_KEY` 필요.
- 호출:
  ```
  firecrawl_search(query="<키워드>", limit=N)
  → 결과의 url 들에 firecrawl_extract 로 schema 추출
  ```
- 변환: title/authors/year/abstract 가 거의 그대로 매핑됨. pdf_url 은 arXiv 의 `https://arxiv.org/pdf/<id>.pdf` 패턴 추정.

### 2. exa-mcp

- 도구: `exa_search` (이름은 도구마다 약간 다를 수 있음)
- 장점: 학술 검색에 최적화된 reranking. API key 가 있다면 firecrawl 다음 후보.
- 단점: structured output 이 firecrawl 보다 거칠다.
- 변환: snippet 에서 author·year 를 LLM-side 파싱.

### 3. brave-search-mcp + web_fetch

- 도구: `brave_web_search` + `web_fetch`
- 장점: API key 무료 layer 가 넉넉.
- 단점: 검색 결과의 url 마다 `web_fetch` 로 페이지를 받아 LLM 이 직접 파싱해야 함.
- 변환:
  1. `brave_web_search(query="...")` → 상위 N 개 url
  2. 각 url 에 `web_fetch` → HTML 또는 abstract 페이지
  3. LLM 이 title/authors/year/abstract 추출

### 4. 내장 web_search + web_fetch (최후 fallback)

- 도구: Claude Code 의 내장 `web_search`, `web_fetch`
- 장점: 추가 설정 없이 동작.
- 단점: 결과 품질이 위 셋보다 낮을 수 있음. 페이지 파싱은 동일하게 LLM 부담.
- 변환: brave 와 동일한 패턴.

## 변환 예시 (arXiv 페이지 1개)

입력 (firecrawl extracted):

```json
{
  "title": "Attention Is All You Need",
  "authors": "Vaswani, A.; Shazeer, N.; Parmar, N.",
  "year": "2017",
  "abstract": "...",
  "url": "https://arxiv.org/abs/1706.03762"
}
```

raw.json 출력:

```json
{
  "title": "Attention Is All You Need",
  "authors": ["Vaswani, A.", "Shazeer, N.", "Parmar, N."],
  "year": 2017,
  "abstract": "...",
  "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
  "source_url": "https://arxiv.org/abs/1706.03762"
}
```

주의:

- `authors` 는 list 여야 한다 (string 인 경우 `;` 또는 `,` 로 split)
- `year` 는 integer 여야 한다 (Python pipeline 에서 type-coerce 됨)
- `pdf_url` 은 검증되지 않는다 — 실제 PDF 인지는 `pdf_downloader.download_pdf` 의 magic-byte 체크가 책임

## 백엔드 선택 결정 트리

```
사용 가능한 MCP 도구 검사:
├── firecrawl_search 있음 → firecrawl 사용 (1)
├── 없음 + exa_search 있음 → exa 사용 (2)
├── 없음 + brave_web_search 있음 → brave + web_fetch (3)
└── 모두 없음 → 내장 web_search + web_fetch (4)
```

이 트리는 SKILL.md 의 Step 1 과 일치한다. 새로운 검색 백엔드를 추가하려면 (a) 이 문서에 항목 추가, (b) SKILL.md Step 1 fallback chain 갱신 두 곳을 동시에 손봐야 정합성이 유지된다.
