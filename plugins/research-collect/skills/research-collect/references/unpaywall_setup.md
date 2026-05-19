# Unpaywall OA fallback 설정

`UNPAYWALL_EMAIL` 이 설정되어 있으면 cloud 모드의 `ingest.run()` 은 record 의 `pdf_url` 이 비어 있고 `doi` 가 있을 때 Unpaywall API 를 호출해 OA 사본 URL 을 찾는다.

## 설정 절차

1. 본인 이메일 주소 준비 (학교 메일 권장)
2. `.env` 에 한 줄 추가:
   ```
   UNPAYWALL_EMAIL=you@your-uni.edu
   ```
3. (선행 요건) cloud 모드 활성화 — `ZOTERO_USER_ID` + `ZOTERO_API_KEY` 도 있어야 함. local 모드는 PDF 첨부 자체가 불가능하므로 Unpaywall fallback 도 효과 없음.
4. `python3 -m research_collect ...` 실행 — stdout 에 `oa_resolved_via_unpaywall: N` 카운트가 표시되면 fallback 이 동작 중

## Unpaywall ToS

- email 필드는 *식별용* 이며 필수다 (Unpaywall 측이 abuse 차단·연락용으로 요구)
- 익명 호출은 차단됨
- rate limit: 일일 100k req — 강의 시연 규모에서는 신경 안 써도 됨
- 상업적 봇 트래픽 금지
- 결과 캐싱은 사용자측 자유

## 동작 검증

paywall journal 중 publisher OA 또는 preprint 가 있는 DOI 로 테스트:

```bash
python3 -c "
from research_collect.pdf_downloader import resolve_oa_url
print(resolve_oa_url('10.1038/nature12373', 'you@your-uni.edu'))
"
```

OA 사본이 있으면 `https://...pdf` URL, 없으면 빈 문자열을 출력한다.

## 알려진 한계

- 모든 paywall DOI 가 OA 사본을 갖지는 않는다 — 일부는 진짜로 OA 가 없으며 `oa_resolved_via_unpaywall: 0` 이 정상이다
- 출판사가 제공하는 OA URL 이 HTML 페이지인 경우 `download_pdf` 의 magic-byte 검증에서 거부 — 첨부 실패 카운트로 잡힌다
- `is_oa: True` 라도 `best_oa_location.url_for_pdf` 가 비어 있으면 skip
- preprint 만 OA 인 경우 출판본과 내용이 다를 수 있음 (사용자 인지 필요)

## 회귀 방지 테스트

`tests/test_pdf_downloader.py::test_resolve_oa_url_*` 가 다음 분기를 모두 mock 으로 검증:

- `is_oa: True` + `best_oa_location.url_for_pdf` 존재 → URL 반환
- `is_oa: False` → 빈 문자열
- `best_oa_location` 자체가 없거나 `url_for_pdf` 비어 있음 → 빈 문자열
- 404 / network error → 빈 문자열 (예외 삼키지 않음)
