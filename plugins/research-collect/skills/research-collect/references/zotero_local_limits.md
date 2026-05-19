# Zotero 로컬 API write 한계

`zotero-mcp` 가 노출하는 Zotero Local API 는 read 는 정상이지만 write/delete 가 부분적으로 막혀 있다. 이 표가 두 모드 분기(local vs cloud)의 근거다.

## HTTP 응답 표

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

## 결론

**로컬 모드만으로는 PDF 자동 첨부 불가능.** Zotero 데스크탑이 응답하는 connector 엔드포인트는 metadata 만 받는다. PDF 가 필요하면 `ZOTERO_USER_ID` + `ZOTERO_API_KEY` 로 클라우드 모드를 활성화해야 한다.

또한 `DELETE` 가 501 을 반환하므로, 잘못 등록된 아이템 청소는 Zotero 데스크탑에서 수동으로 해야 한다 (cloud 모드는 `delete_item` 정상 동작).

## 회귀 방지 포인트

- `_resolve_pdf_url` · `attach_pdfs` 는 `mode == "cloud"` 가드 안에서만 호출되어야 한다.
- `connector_save_items` 의 응답 body 가 비어 있다는 점 — local item key 를 사용한 후속 호출은 불가능.
- `cloud_create_items` 가 keys list 를 보존해야 attachment 가 올바른 부모에 붙는다.
- 로컬 API 의 endpoint 가능 여부는 Zotero 버전·플랫폼별로 다를 수 있다. 위 표는 macOS Zotero 7.x 기준.
