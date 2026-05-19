# research-collect Plugin 개발 작업 명세서

> Claude Code에 이 문서를 통째로 전달하여 단계별로 진행. SDD(Spec-Driven Development) 절차를 따른다.

---

## 0. Constitution (절대 원칙)

이 작업 전체에서 깨면 안 되는 규칙:

1. **기존 Python 패키지(`src/research_collect/`)의 코드 로직은 수정하지 않는다.** 위치만 옮기고 import path만 조정한다. 동작이 깨졌는지는 기존 테스트로 확인한다.
2. **Plugin은 검색 백엔드에 종속되지 않는다.** firecrawl-mcp가 없어도 exa, brave-search, 또는 내장 web_search로 동작 가능해야 한다. 추상화 경계는 `data/raw.json` 스키마.
3. **의존성 자동 설치는 시도하지 않는다.** 누락 시 사용자에게 정확한 설치 명령어를 안내한다.
4. **모드 자동 분기(`local` vs `cloud`)는 환경변수 기반으로 유지한다.** SKILL.md가 이 로직을 사용자에게 명확히 설명해야 한다.
5. **`.env` 와 API 키는 절대 커밋하지 않는다.** `.env.example`만 placeholder로 커밋.
6. **모든 응답·문서는 한국어.** 코드 주석·식별자는 영어 유지.
7. **최종 산출물은 Plugin Marketplace 형식.** `.claude-plugin/marketplace.json` + `plugins/<name>/.claude-plugin/plugin.json` + `plugins/<name>/skills/<name>/SKILL.md` 3종이 반드시 존재.
8. **기존 작업 디렉토리(`firecrawl-pyzotero-zotero workflow/`)는 손대지 않는다.** 강의용 README·CLAUDE.md·시연용 `.env`·`data/` 모두 보존. 새 sibling 디렉토리(`/Users/baekjw/Downloads/research-collect-marketplace/`)에는 코드·테스트·필수 메타데이터만 **복사**(이동 아님)한다. 기존 `.git` 충돌 없음을 새 레포 init 후 확인.

---

## 1. Specification (무엇을 만드는가)

### 1.1 목표

기존 `src/research_collect/` Python 패키지를 Claude Code Plugin Marketplace 형식으로 재구성하여 GitHub에 배포한다. 사용자가 한 줄 명령(`/plugin marketplace add` + `/plugin install`)으로 설치 가능해야 하며, 자연어 요청("arXiv에서 transformer 논문 5편 모아서 Zotero에 넣어줘")만으로 워크플로우가 발동해야 한다.

### 1.2 사용자 시나리오

**Primary**: Claude Code 사용자가 본인 연구 도메인의 논문을 모아 Zotero에 등록하고 싶다.
- "X 키워드로 논문 N편 모아서 정리해줘" → Skill 자동 발동 → 검색 백엔드 자동 선택 → Python 파이프라인 실행 → Zotero 등록 → 결과 보고

**Secondary**: 강의 시연. 교수가 학생들 앞에서 위 명령어로 작동을 보여주고, 학생들이 동일 plugin을 설치해 본인 도메인에 응용한다.

### 1.3 검색 백엔드 추상화

Skill은 다음 우선순위로 자동 선택:

1. `firecrawl-mcp` (registered) → 선호 (structured extraction)
2. `exa-mcp` (registered) → 대체
3. `brave-search-mcp` (registered) + `web_fetch` → 대체
4. 내장 `web_search` + `web_fetch` → 최후 fallback

모든 백엔드의 출력은 `data/raw.json` 표준 스키마를 따라야 한다:

```json
[
  {
    "title": "string (required)",
    "authors": ["string"] (required, ≥1),
    "year": "integer (required)",
    "doi": "string (optional)",
    "abstract": "string (optional)",
    "pdf_url": "string (optional)",
    "source_url": "string (optional)"
  }
]
```

### 1.4 Zotero 모드 분기

기존 로직 그대로 유지:
- `ZOTERO_USER_ID` + `ZOTERO_API_KEY` 둘 다 있으면 → cloud 모드 (PDF 자동 첨부 포함)
- 둘 중 하나라도 없으면 → local 모드 (connector 경유, PDF 없음)
- `UNPAYWALL_EMAIL` 추가 시 → cloud 모드에서 OA fallback 활성화

### 1.5 Out of scope (이번 작업에서 제외)

- Python 코드의 새 기능 추가
- DOI 기반 dedupe
- 새로운 출력 포맷
- Anthropic 공식 마켓플레이스 제출 (나중에)

---

## 2. Plan (어떻게 만드는가)

### 2.1 최종 디렉토리 구조

```
research-collect-marketplace/                       # GitHub 레포 루트
├── .claude-plugin/
│   └── marketplace.json                            # 마켓플레이스 카탈로그
├── plugins/
│   └── research-collect/
│       ├── .claude-plugin/
│       │   └── plugin.json                         # 플러그인 매니페스트
│       ├── skills/
│       │   └── research-collect/
│       │       ├── SKILL.md                        # 핵심 자연어 명세 (yaml frontmatter 포함)
│       │       ├── scripts/
│       │       │   └── research_collect/           # 기존 src/research_collect/ 이동
│       │       │       ├── __init__.py
│       │       │       ├── __main__.py
│       │       │       ├── ingest.py
│       │       │       ├── normalize.py
│       │       │       ├── md_writer.py
│       │       │       ├── zotero_writer.py
│       │       │       └── pdf_downloader.py
│       │       ├── references/                     # 보조 문서 (필요 시 Claude가 로드)
│       │       │   ├── zotero_local_limits.md
│       │       │   ├── unpaywall_setup.md
│       │       │   └── search_backends.md
│       │       └── examples/
│       │           └── firecrawl_arxiv_sample.json
│       ├── commands/
│       │   └── research-collect.md                 # NEW: 슬래시 커맨드
│       ├── hooks/
│       │   ├── hooks.json                          # NEW: PreToolUse 매처
│       │   └── check_env.sh                        # NEW: .env stage 차단
│       ├── scripts/
│       │   └── install.sh                          # 의존성 설치 도우미
│       └── README.md
├── tests/                                          # 기존 tests/ 그대로
│   ├── conftest.py
│   ├── fixtures/
│   ├── test_normalize.py
│   ├── test_md_writer.py
│   ├── test_zotero_writer.py
│   ├── test_pdf_downloader.py
│   ├── test_schema.py
│   ├── test_integration.py
│   └── test_plugin_structure.py                    # NEW: plugin 구조 검증
├── pyproject.toml                                  # 위치는 루트 유지 (개발 편의)
├── .env.example
├── .gitignore
├── LICENSE
└── README.md                                       # 마켓플레이스 전체 README
```

### 2.2 핵심 설계 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| Python 코드 위치 | `plugins/research-collect/skills/research-collect/scripts/research_collect/` | Plugin 설치 시 Skill 폴더 통째로 복사되므로 코드도 함께 가야 함 |
| `pyproject.toml` 위치 | 레포 루트 | `pip install -e .` 개발 편의. 설치 시 `package-dir` 로 scripts 경로 지정 |
| 검색 백엔드 선택 | SKILL.md 자연어 fallback chain | Claude가 환경 확인 후 자동 선택. 코드 분기 불필요 |
| 의존성 안내 | SKILL.md `Prerequisites check` 섹션 + `scripts/install.sh` | 자동 설치는 안 하되 명령어는 한 줄로 |
| Skill 분리 여부 | 단일 Skill | 현 시점 백엔드 차이가 raw.json 스키마로 흡수됨. 미래에 필요 시 분리 |

### 2.3 SKILL.md frontmatter

> `description` 최대 길이는 공식 스펙 기준 **1536자** (claude-code-guide 검증). 트리거 키워드는 한국어·영어·도구명 3계층으로 다층화.

```yaml
---
name: research-collect
description: Use this skill when the user wants to collect academic papers from the web (arXiv, journal sites, search results) and register them in their Zotero library. Searches papers via the best available backend (firecrawl-mcp preferred, then exa-mcp, brave-search-mcp, or built-in web_search), normalizes metadata into Markdown with YAML frontmatter, and writes to Zotero in local or cloud mode (cloud mode auto-attaches PDFs via Unpaywall OA fallback). Triggers on Korean phrases like "논문 수집", "Zotero에 등록", "논문 정리", "참고문헌 모으기", and English phrases like "paper collection", "gather papers about X", "academic literature review", "import to Zotero". Also triggers when user mentions any of firecrawl, exa, brave-search, or Zotero in the context of academic research.
---
```

---

## 3. Tasks (실행 순서, 의존성 있는 분할)

각 Task는 **이전 Task가 통과해야 다음으로 진행**. 각각 끝에 검증 step 포함.

### Task 1 — 디렉토리 골격 생성 (의존성 없음)

1. `/Users/baekjw/Downloads/research-collect-marketplace/` 루트 생성 (기존 작업 디렉토리의 sibling — §0.8 참조)
2. 위 2.1의 모든 디렉토리 `mkdir -p` (`commands/`, `hooks/` 포함)
3. 다음 파일들을 **명시된 내용대로** 생성:

   **`.gitignore`** (기존 디렉토리의 .gitignore 와 동일):
   ```
   __pycache__/
   *.py[cod]
   *$py.class
   .pytest_cache/
   *.egg-info/
   dist/
   build/
   .venv/
   venv/

   .env
   data/

   .DS_Store
   .vscode/
   .idea/
   ```

   **`.env.example`** (placeholder 만, 실제 값처럼 보이지 않도록):
   ```bash
   # Search backends (optional; pick what you have)
   FIRECRAWL_API_KEY=fc-your-key-here

   # Zotero — leave empty for local mode (no PDF)
   ZOTERO_USER_ID=
   ZOTERO_API_KEY=

   # Unpaywall OA fallback (optional; cloud mode only)
   UNPAYWALL_EMAIL=
   ```

   **`LICENSE`** (MIT, 저작권자 명시):
   ```
   MIT License

   Copyright (c) 2026 Jang-Woon Baek

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:

   The above copyright notice and this permission notice shall be included in all
   copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
   SOFTWARE.
   ```

   **`README.md`**: 빈 파일로 생성 (Task 10 에서 채움)

4. **검증**: `tree research-collect-marketplace -L 4` 가 2.1과 일치 (`commands/`, `hooks/` 포함)

### Task 2 — 기존 코드 복사 (Task 1 의존)

> §0.8 에 따라 **복사**(이동 아님). 기존 작업 디렉토리는 그대로 둔다.

1. 기존 `firecrawl-pyzotero-zotero workflow/src/research_collect/` 의 모든 `.py` 파일을 새 레포의 `plugins/research-collect/skills/research-collect/scripts/research_collect/` 로 **복사** (예: `cp -r`)
2. 기존 `firecrawl-pyzotero-zotero workflow/tests/` 전체를 새 레포 루트의 `tests/` 로 **복사**
3. 기존 `tests/fixtures/firecrawl_arxiv_sample.json` 을 `plugins/research-collect/skills/research-collect/examples/` 에도 복사
4. 기존 `pyproject.toml` 을 새 레포 루트에 복사하되 다음 한 곳만 수정:
   ```toml
   [tool.setuptools.packages.find]
   where = ["plugins/research-collect/skills/research-collect/scripts"]
   ```
   `[project.scripts] research-collect = "research_collect.__main__:main"` 은 그대로(패키지 이름 동일). 기타 dependencies·markers 그대로 유지.
5. **검증**: 새 레포 루트에서 `pip install -e .` 성공 + `python3 -c "from research_collect import ingest; print('ok')"` 성공

### Task 3 — 기존 테스트 회귀 확인 (Task 2 의존)

1. `python3 -m pytest tests/ -v` 실행
2. 모든 단위 테스트와 스키마 테스트 통과 확인
3. 실패 시 import path 만 조정. 로직은 절대 손대지 않음
4. **검증**: 기존 테스트 100% 통과 (mark가 integration인 것 제외)

### Task 4 — `.claude-plugin/marketplace.json` 작성 (Task 1 의존)

1. 마켓플레이스 매니페스트 작성:

```json
{
  "name": "baekja-research-tools",
  "description": "Research workflow plugins for academic paper collection and analysis.",
  "owner": {
    "name": "Jang-Woon Baek",
    "email": "baekjw@khu.ac.kr"
  },
  "plugins": [
    {
      "name": "research-collect",
      "source": "./plugins/research-collect",
      "description": "Pluggable-backend paper collection pipeline: search → normalize → Zotero register, with optional PDF auto-attachment via Unpaywall.",
      "version": "0.1.0"
    }
  ]
}
```

2. **검증**: `python3 -c "import json; json.load(open('research-collect-marketplace/.claude-plugin/marketplace.json'))"` 성공

### Task 5 — `plugins/research-collect/.claude-plugin/plugin.json` 작성 (Task 1 의존)

```json
{
  "name": "research-collect",
  "version": "0.1.0",
  "description": "Academic paper collection pipeline with pluggable search backend (firecrawl/exa/brave/web_search) and Zotero registration with optional PDF auto-attachment.",
  "author": {
    "name": "Jang-Woon Baek",
    "email": "baekjw@khu.ac.kr"
  },
  "homepage": "https://github.com/baekja/research-collect-marketplace"
}
```

**검증**: JSON 파싱 성공.

### Task 6 — SKILL.md 작성 (Task 1, 4, 5 의존)

`plugins/research-collect/skills/research-collect/SKILL.md` 작성. 필수 섹션:

1. **YAML frontmatter** (위 2.3과 동일, description ≤1536자)
2. **When to use this skill** — 트리거 시나리오
3. **Prerequisites check** — Claude가 발동 시 자동 확인할 사전조건 (MCP 등록 여부, Python deps, `.env`)
4. **Step 1: Search (pluggable backend)** — fallback chain 4단계 명시. **자연어 결정 가이드 포함**:
   ```
   Before searching, list available MCP tools and pick in order:
   1. If `firecrawl_search` is available → firecrawl with structured extraction.
   2. Else if `exa_search` (or similar exa tool) → exa.
   3. Else if `brave_web_search` → brave + web_fetch.
   4. Else → built-in web_search + web_fetch.

   For each backend, transform the raw output into the standard schema below
   (`./data/raw.json` relative to cwd) before invoking Step 2. The downstream
   Python pipeline only sees the schema, not the backend.
   ```
   이어서 raw.json 표준 스키마 표(§1.3) 인용.
5. **Step 2: Normalize and register (deterministic)** — 다음 정책 명시:
   - 기본 입력 위치: 사용자 프로젝트 cwd 의 `./data/raw.json`
   - 출력 디렉토리도 cwd 기준 `./data/papers`·`./data/pdfs`
   - 다른 위치를 원하면 `--raw <path>` 등 명시
   - `data/` 디렉토리가 없으면 Skill 이 명시적으로 안내 후 `mkdir -p ./data` 실행
   - 실행 명령: `python3 -m research_collect --raw data/raw.json --out data/papers --pdf-dir data/pdfs --collection "<이름>"`
6. **Step 3: Verify (optional)** — `zotero-mcp` 있으면 컬렉션 조회로 검증, 없으면 Step 2 출력(`[mode: ...]`, 등록·실패 카운트)으로 보고
7. **Mode selection logic** — local vs cloud 분기 표 (기존 CLAUDE.md 그대로 — 7행 비교표)
8. **Known limitations** — Zotero 로컬 API write 한계 표 (기존 CLAUDE.md L27-40 의 HTTP 표)
9. **Troubleshooting** — 자주 막히는 6가지 (기존 CLAUDE.md L159-166 그대로)
10. **See also** — `references/` 의 추가 문서 안내

**검증**: 
- 파일 첫 줄이 `---` 로 시작하고 frontmatter가 valid YAML
- `description` 필드가 **1536자 이내** (공식 스펙)
- 모든 섹션 헤더가 존재

### Task 6.5 — Slash command `/research-collect` 작성 (Task 6 의존)

> 강의 시연용 명시적 진입점. Skill 자동 트리거 외에 `/research-collect <키워드>` 한 줄로도 발동.

`plugins/research-collect/commands/research-collect.md` 작성:

```markdown
---
description: arXiv·Google Scholar 검색 → Zotero 등록 파이프라인을 한 줄로 실행
argument-hint: <검색 키워드> [컬렉션명] [N편]
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
```

**검증**:
- 파일 존재
- YAML frontmatter parsable (`description`, `argument-hint`)
- 본문에 `$ARGUMENTS` 토큰 존재

### Task 7 — references/ 보조 문서 작성 (Task 6 의존)

3개 파일:

- `references/zotero_local_limits.md` — 기존 CLAUDE.md의 "Zotero 로컬 API write 한계" 표 + 설명
- `references/unpaywall_setup.md` — UNPAYWALL_EMAIL 설정법, ToS 안내, 동작 검증법
- `references/search_backends.md` — 각 백엔드(firecrawl/exa/brave/web_search) 별 호출 방법, 장단점, raw.json 변환 예시

**검증**: 3개 파일 존재 + 각각 최소 1 KB 이상.

### Task 8 — `scripts/install.sh` 작성 (Task 1 의존)

```bash
#!/usr/bin/env bash
set -e
echo "[research-collect] Registering MCP servers..."

if ! command -v claude &> /dev/null; then
  echo "ERROR: claude CLI not found. Install Claude Code first."
  exit 1
fi

echo "  → firecrawl-mcp (optional, recommended)"
claude mcp add firecrawl npx -- -y firecrawl-mcp \
  -e FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-"set_me_in_env"} || true

echo "  → zotero-mcp (required)"
claude mcp add zotero uvx -- zotero-mcp -e ZOTERO_LOCAL=true || true

echo "[research-collect] Installing Python deps..."
pip install -e "$(dirname "$0")/../../.." || pip install -e "."

echo "[research-collect] Done. Please restart Claude Code."
echo ""
echo "Optional: edit .env to enable cloud mode and Unpaywall fallback."
```

**검증**: `bash -n scripts/install.sh` (syntax check) 성공.

### Task 8.5 — Hooks 작성 (`.env` 실수 commit 차단, Task 1 의존)

> Plugin 레벨에서 `.env` stage 를 사전 차단. git pre-commit 없이도 동작.

**파일 1**: `plugins/research-collect/hooks/hooks.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": { "tool_name": "Bash" },
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/check_env.sh"
      }
    ]
  }
}
```

**파일 2**: `plugins/research-collect/hooks/check_env.sh`

```bash
#!/usr/bin/env bash
# Block `git add .env` / `git commit` when .env is staged.
# Reads the about-to-run Bash command from stdin (Claude Code hook contract).

set -u
input="$(cat || true)"
cmd="$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("command",""))
except Exception:
    pass' 2>/dev/null || true)"

# Trigger only for git-related commands
if [[ "$cmd" == *"git add"* || "$cmd" == *"git commit"* ]]; then
  # Is .env staged?
  if git diff --cached --name-only 2>/dev/null | grep -qx '.env'; then
    echo "BLOCKED: .env is staged. Run 'git rm --cached .env' first." >&2
    exit 2   # exit 2 = block in Claude Code hook contract
  fi
fi
exit 0
```

후속 단계에서 `chmod +x plugins/research-collect/hooks/check_env.sh`.

**검증**:
- `python3 -m json.tool < plugins/research-collect/hooks/hooks.json` 성공
- `bash -n plugins/research-collect/hooks/check_env.sh` 성공
- 스크립트가 executable bit 가짐 (`test -x` 통과)

### Task 9 — Plugin 구조 검증 테스트 추가 (Task 4-8.5 의존)

`tests/test_plugin_structure.py` 신규 작성:

```python
"""Plugin과 Marketplace 구조 정합성 검증."""
import json
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_JSON = REPO_ROOT / "plugins" / "research-collect" / ".claude-plugin" / "plugin.json"
SKILL_MD = REPO_ROOT / "plugins" / "research-collect" / "skills" / "research-collect" / "SKILL.md"
SCRIPTS_DIR = REPO_ROOT / "plugins" / "research-collect" / "skills" / "research-collect" / "scripts" / "research_collect"
REFERENCES_DIR = REPO_ROOT / "plugins" / "research-collect" / "skills" / "research-collect" / "references"


class TestMarketplaceJson:
    def test_exists(self):
        assert MARKETPLACE_JSON.exists(), f"missing: {MARKETPLACE_JSON}"

    def test_valid_json(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        assert "name" in data
        assert "plugins" in data
        assert isinstance(data["plugins"], list)
        assert len(data["plugins"]) >= 1

    def test_name_kebab_case(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        # 소문자, 숫자, 하이픈만 허용
        import re
        assert re.fullmatch(r"[a-z0-9-]+", data["name"]), \
            f"marketplace name must be kebab-case: {data['name']}"

    def test_not_reserved_name(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        reserved = {
            "claude-code-marketplace", "claude-code-plugins",
            "claude-plugins-official", "anthropic-marketplace",
            "anthropic-plugins", "agent-skills",
            "knowledge-work-plugins", "life-sciences",
        }
        assert data["name"] not in reserved


class TestPluginJson:
    def test_exists(self):
        assert PLUGIN_JSON.exists(), f"missing: {PLUGIN_JSON}"

    def test_valid_json(self):
        data = json.loads(PLUGIN_JSON.read_text())
        for key in ("name", "version", "description"):
            assert key in data, f"plugin.json missing key: {key}"

    def test_name_kebab_case(self):
        import re
        data = json.loads(PLUGIN_JSON.read_text())
        assert re.fullmatch(r"[a-z0-9-]+", data["name"])

    def test_version_semver(self):
        import re
        data = json.loads(PLUGIN_JSON.read_text())
        assert re.fullmatch(r"\d+\.\d+\.\d+", data["version"])


class TestSkillMd:
    def test_exists(self):
        assert SKILL_MD.exists()

    def test_has_yaml_frontmatter(self):
        text = SKILL_MD.read_text()
        assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
        end = text.find("\n---\n", 4)
        assert end > 0, "SKILL.md frontmatter not closed"
        fm = yaml.safe_load(text[4:end])
        assert "name" in fm
        assert "description" in fm
        assert len(fm["description"]) <= 1536, "description too long (official spec: 1536)"
        assert len(fm["description"]) >= 50, "description too short — Claude won't trigger well"

    def test_required_sections(self):
        text = SKILL_MD.read_text()
        required = [
            "When to use",
            "Prerequisites",
            "Step 1",
            "Step 2",
            "Mode selection",
            "Troubleshooting",
        ]
        for section in required:
            assert section in text, f"SKILL.md missing section: {section}"

    def test_mentions_all_backends(self):
        text = SKILL_MD.read_text().lower()
        for backend in ("firecrawl", "exa", "brave", "web_search"):
            assert backend in text, f"SKILL.md must mention backend: {backend}"


class TestScriptsLayout:
    def test_python_package_present(self):
        assert (SCRIPTS_DIR / "__init__.py").exists()
        for mod in ("ingest", "normalize", "md_writer", "zotero_writer", "pdf_downloader"):
            assert (SCRIPTS_DIR / f"{mod}.py").exists(), f"missing: {mod}.py"

    def test_references_present(self):
        for doc in ("zotero_local_limits.md", "unpaywall_setup.md", "search_backends.md"):
            path = REFERENCES_DIR / doc
            assert path.exists(), f"missing: {doc}"
            assert path.stat().st_size > 500, f"too short: {doc}"


class TestInstallScript:
    def test_exists_and_executable(self):
        path = REPO_ROOT / "plugins" / "research-collect" / "scripts" / "install.sh"
        assert path.exists()
        # syntax check
        import subprocess
        r = subprocess.run(["bash", "-n", str(path)], capture_output=True)
        assert r.returncode == 0, f"syntax error: {r.stderr.decode()}"


class TestCommands:
    """Slash command `/research-collect` — Task 6.5."""

    CMD = REPO_ROOT / "plugins" / "research-collect" / "commands" / "research-collect.md"

    def test_exists(self):
        assert self.CMD.exists(), f"missing: {self.CMD}"

    def test_has_frontmatter(self):
        text = self.CMD.read_text()
        assert text.startswith("---\n"), "command must start with YAML frontmatter"
        end = text.find("\n---\n", 4)
        assert end > 0, "command frontmatter not closed"
        fm = yaml.safe_load(text[4:end])
        assert "description" in fm
        assert "argument-hint" in fm

    def test_uses_arguments_token(self):
        text = self.CMD.read_text()
        assert "$ARGUMENTS" in text, "command body must reference $ARGUMENTS"


class TestHooks:
    """Hooks — Task 8.5."""

    HOOKS_JSON = REPO_ROOT / "plugins" / "research-collect" / "hooks" / "hooks.json"
    CHECK_SH = REPO_ROOT / "plugins" / "research-collect" / "hooks" / "check_env.sh"

    def test_hooks_json_valid(self):
        data = json.loads(self.HOOKS_JSON.read_text())
        assert "hooks" in data
        assert "PreToolUse" in data["hooks"]

    def test_check_env_sh_syntax(self):
        import subprocess
        r = subprocess.run(["bash", "-n", str(self.CHECK_SH)], capture_output=True)
        assert r.returncode == 0, f"syntax error: {r.stderr.decode()}"

    def test_check_env_sh_executable(self):
        assert os.access(self.CHECK_SH, os.X_OK), \
            f"not executable: {self.CHECK_SH}"
```

`import os` 를 파일 상단에 추가해야 함 (위 `TestHooks.test_check_env_sh_executable` 가 사용).

**검증**: `python3 -m pytest tests/test_plugin_structure.py -v` 전부 통과.

### Task 10 — 루트 README.md 작성 (Task 4-9 의존)

마켓플레이스 진입점. 포함 내용:

1. 한 줄 소개
2. 설치 명령어 (사용자 관점)
   ```bash
   /plugin marketplace add baekja/research-collect-marketplace
   /plugin install research-collect@baekja-research-tools
   ```
3. 최초 설정 (`bash scripts/install.sh` + `.env` 작성)
4. 사용 예시 (자연어 명령어 3-4개)
5. 모드 차이 (local vs cloud) 짧은 표
6. 디렉토리 구조 다이어그램
7. 라이선스 (MIT)
8. 학생용 안내 1줄 (`강의 시연용 — 자세한 워크플로우는 SKILL.md 참조`)

**검증**: 파일 존재 + 위 7개 섹션 모두 포함.

### Task 11 — 로컬 마켓플레이스 테스트 (Task 1-10 모두 통과 후)

GitHub 푸시 전 로컬에서 plugin 작동 확인:

1. `claude` CLI에서:
   ```
   /plugin marketplace add /절대경로/research-collect-marketplace
   /plugin install research-collect@baekja-research-tools
   ```
2. 새 Claude 세션 시작
3. 테스트 프롬프트 입력: "research-collect skill로 arXiv에서 'graph neural network' 논문 3편 모아서 'TestGNN' 컬렉션에 넣어줘"
4. Claude가 다음을 자동 수행하는지 확인:
   - Prerequisites check (MCP 등록 여부, .env)
   - 사용 가능한 검색 백엔드 자동 선택
   - `data/raw.json` 생성
   - `python3 -m research_collect ...` 실행
   - 결과 보고

**검증**: 위 4단계가 사용자 추가 입력 없이 진행됨. 막히는 지점이 있으면 SKILL.md 보강 후 재시도.

### Task 12 — GitHub 푸시 (Task 11 통과 후)

공통 사전 단계:

```bash
cd /Users/baekjw/Downloads/research-collect-marketplace
git init
git add .
git status                                       # .env 가 staged 에서 빠졌는지 확인
# 만약 .env 가 보이면: git rm --cached .env && echo .env >> .gitignore && git add .gitignore
git commit -m "Initial: research-collect plugin v0.1.0"
```

이후 두 갈래:

**A. `gh` CLI 가 인증된 경우** (권장):
```bash
gh repo create baekja/research-collect-marketplace --public --source=. --push
```

**B. `gh` 가 없거나 인증되지 않은 경우** (fallback):
1. 브라우저로 <https://github.com/new> 접속
2. Repository name = `research-collect-marketplace`, Owner = `baekja`, **Public**, "Add a README" / `.gitignore` / license 체크 **해제** (이미 있음)
3. *Create repository* 클릭
4. 터미널로 돌아와:
   ```bash
   git branch -M main
   git remote add origin https://github.com/baekja/research-collect-marketplace.git
   git push -u origin main
   ```

**검증**: 
- `git log --oneline` 최소 1개 커밋 (§4.2.4: `.env` 미포함)
- GitHub 레포 URL 출력
- 다른 환경(또는 새 Claude 세션)에서 `/plugin marketplace add baekja/research-collect-marketplace` 작동

---

## 4. Test Plan (실패 없이 진행되었는지 어떻게 아는가)

### 4.1 게이트 (각 Task 후 통과 확인)

| Gate | 명령 | 통과 조건 |
|------|------|-----------|
| G1: 골격 | `tree research-collect-marketplace -L 4` | 2.1과 일치 |
| G2: 코드 이동 | `python3 -c "from research_collect import ingest"` | exit 0 |
| G3: 회귀 | `python3 -m pytest tests/ -v -m "not integration"` | 모두 통과 |
| G4: JSON 매니페스트 | `python3 -m json.tool < .claude-plugin/marketplace.json` | 파싱 성공 |
| G5: Plugin JSON | `python3 -m json.tool < plugins/research-collect/.claude-plugin/plugin.json` | 파싱 성공 |
| G6: SKILL.md | (Task 9의 `TestSkillMd` 클래스) | 모두 통과 |
| G6.5: slash command | `python3 -c "import yaml,re; t=open('plugins/research-collect/commands/research-collect.md').read(); print(yaml.safe_load(t.split('---')[1]))"` | YAML 파싱 OK + `$ARGUMENTS` 본문 포함 |
| G7: install.sh | `bash -n plugins/research-collect/scripts/install.sh` | exit 0 |
| G8: Plugin 구조 | `python3 -m pytest tests/test_plugin_structure.py -v` | 모두 통과 |
| G8.5: hooks | `python3 -m json.tool < plugins/research-collect/hooks/hooks.json && bash -n plugins/research-collect/hooks/check_env.sh` | 둘 다 exit 0 |
| G9: 로컬 plugin 작동 | Task 11의 4단계 자연어 시연 | 사용자 추가 입력 없이 진행 |
| G10: 푸시 | `git log --oneline` | 최소 1개 커밋, `.env` 미포함 |

### 4.2 회귀 방지 핵심 포인트

다음이 깨지면 **즉시 중단하고 사용자에게 보고**:

1. 기존 단위 테스트 1개라도 실패 → Task 2의 import path 조정만 다시 확인
2. SKILL.md description이 50자 미만이거나 1536자 초과 → frontmatter 손봄 (공식 스펙)
3. plugin.json 또는 marketplace.json의 `name` 필드가 kebab-case 아님 → 즉시 수정
4. `.env` 가 `git status` 에 나타남 → `.gitignore` 확인 후 `git rm --cached .env`
5. Task 11에서 Claude가 SKILL을 발동하지 않음 → `description` 의 트리거 키워드 보강

### 4.3 통합 시연 시나리오 (Task 11에서 반드시 작동해야 하는 4가지)

1. **firecrawl 있음 + cloud 모드**: PDF까지 자동 첨부 — Unpaywall fallback 카운트 표시
2. **firecrawl 있음 + local 모드** (`.env` 비움): 메타만 등록, PDF skip 명시
3. **firecrawl 없음 + 내장 web_search fallback**: raw.json 만들고 Step 2 통과
4. **zotero-mcp 미등록**: Step 3 skip하고 Step 2 출력만으로 보고

각 시나리오에서 Claude가 사용자에게 **명확한 상태 보고**를 해야 함 (어떤 모드로 동작 중인지, 무엇이 skip되었는지).

---

## 5. Claude Code에 넘길 단일 프롬프트

(이 문서 끝에 별도로 정리)
