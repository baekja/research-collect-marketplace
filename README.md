# research-collect-marketplace

논문 수집 → Zotero 등록 워크플로우를 Claude Code 한 줄 명령으로 실행하는 plugin marketplace.

## 설치

Claude Code 세션에서:

```
/plugin marketplace add baekja/research-collect-marketplace
/plugin install research-collect@baekja-research-tools
```

(로컬 절대경로로도 등록 가능: `/plugin marketplace add /path/to/research-collect-marketplace`)

## 최초 설정

### macOS / Linux

```bash
git clone https://github.com/baekja/research-collect-marketplace.git
cd research-collect-marketplace
bash plugins/research-collect/scripts/install.sh
cp .env.example .env
# .env 편집 — cloud 모드 사용 시 ZOTERO_USER_ID·ZOTERO_API_KEY 채우기
```

### Windows (PowerShell)

```powershell
git clone https://github.com/baekja/research-collect-marketplace.git
cd research-collect-marketplace
powershell -ExecutionPolicy Bypass -File plugins\research-collect\scripts\install.ps1
Copy-Item .env.example .env
# .env 편집 — cloud 모드 사용 시 ZOTERO_USER_ID·ZOTERO_API_KEY 채우기
```

> Windows 사전 요구사항: `python --version`, `pip --version`, `claude --version` 이 모두 정상 출력되어야 한다 (PATH 등록 확인). PowerShell 실행 정책이 막혀 있으면 위의 `-ExecutionPolicy Bypass` 가 그 호출에 한해 우회한다.

`install.sh` / `install.ps1` 가 자동으로 `firecrawl-mcp` · `zotero-mcp` 를 등록하고 Python 패키지를 editable 로 설치한다. 자동 설치 실패 시 명령어를 stdout 에 출력 — 수동 실행 가이드를 따른다.

## 사용 예시

Claude Code 세션 안에서 자연어 또는 슬래시 커맨드:

```
"arXiv 에서 transformer 논문 5편 모아서 'Transformer-2025' 컬렉션에 넣어줘"
"diffusion model 키워드로 최근 10편 정리해줘"
"gather papers about graph neural networks and import to Zotero"
/research-collect "neural radiance fields" --collection NeRF --limit 8
```

위 한 줄로 검색 → 메타정규화 → Zotero 등록 → (cloud 모드면) PDF 자동 첨부 까지 진행된다.

### 이미 있는 item 에 PDF 만 첨부 (cloud 모드 전용)

메타데이터는 이미 Zotero 에 등록되어 있고 PDF 만 일괄 첨부하고 싶을 때:

```bash
python -m research_collect.attach_only --items data/attach_list.json
```

각 record 는 `item_key` 또는 `doi` (식별자) + `pdf_path` 또는 `pdf_url` (소스) 조합. 자세한 스키마와 샘플은 `plugins/research-collect/skills/research-collect/examples/attach_list_sample.json` 참조. local 모드에서는 거부 (Zotero local API attachment 업로드 불가).

## 모드 차이 (요약)

| 항목 | local | cloud |
|------|-------|-------|
| 환경변수 | (없음) | `ZOTERO_USER_ID` + `ZOTERO_API_KEY` |
| PDF 자동 첨부 | ❌ | ✅ |
| Unpaywall OA fallback | ❌ | ✅ (`UNPAYWALL_EMAIL` 추가 시) |
| item 삭제 | 데스크탑 수동 | API |

자세한 HTTP 응답·근거: `plugins/research-collect/skills/research-collect/references/zotero_local_limits.md`.

## 디렉토리 구조

```
research-collect-marketplace/
├── .claude-plugin/marketplace.json     # 마켓플레이스 카탈로그
├── plugins/research-collect/
│   ├── .claude-plugin/plugin.json
│   ├── skills/research-collect/
│   │   ├── SKILL.md                    # 자연어 명세 (자동 발동)
│   │   ├── scripts/research_collect/   # Python 패키지
│   │   ├── references/                 # 보조 문서 3 종
│   │   └── examples/                   # 샘플 raw.json
│   ├── commands/research-collect.md    # /research-collect 슬래시 커맨드
│   ├── hooks/                          # .env 실수 commit 차단
│   └── scripts/install.sh
├── tests/                              # 단위·스키마·구조 검증
├── pyproject.toml
└── .env.example
```

## 라이선스

MIT — `LICENSE` 참조.

---

강의 시연용 — 자세한 워크플로우는 `plugins/research-collect/skills/research-collect/SKILL.md` 참조.
