"""
AutoTax — Firestore REST API 클라이언트
인증된 사용자의 ID 토큰을 사용하여 Firestore CRUD 수행
"""
import requests
from datetime import datetime, timezone
from core.config import FIRESTORE_BASE_URL


class FirestoreError(Exception):
    """Firestore 통신 오류"""
    pass


class FirestoreClient:
    """Firestore REST API 래퍼"""

    def __init__(self, auth):
        """
        Args:
            auth: FirebaseAuth 인스턴스 (토큰 제공)
        """
        self.auth = auth

    def _headers(self) -> dict:
        headers = {'Content-Type': 'application/json'}
        try:
            # 토큰이 있으면 Authorization 추가, 없으면 공개 접근 시도
            if self.auth.is_authenticated:
                headers['Authorization'] = f'Bearer {self.auth.token}'
        except Exception:
            pass
        return headers

    # ─────────────────────────────────────────
    # 문서 CRUD
    # ─────────────────────────────────────────

    def get_document(self, doc_path: str) -> dict | None:
        """
        단일 문서 읽기.
        doc_path 예: "organizations/daechi_welfare"
        반환: dict (필드 값) 또는 None (문서 없을 때)
        """
        url = f"{FIRESTORE_BASE_URL}/{doc_path}"
        resp = self._request('GET', url)

        if resp.status_code == 404:
            return None
        self._check_error(resp)

        raw = resp.json()
        result = self._decode_document(raw)
        return result

    def list_documents(self, collection_path: str,
                       order_by: str = None,
                       filters: list[tuple] = None) -> list[dict]:
        """
        컬렉션의 모든 문서 조회 (구조화된 쿼리 사용).
        collection_path 예: "organizations/daechi_welfare/instructors"
        filters: [('field', 'op', value), ...] — op: EQUAL, LESS_THAN 등
        order_by: 정렬 기준 필드명
        반환: list[dict] (각 dict에 'id' 포함)
        """
        if filters:
            return self._run_query(collection_path, filters, order_by)

        url = f"{FIRESTORE_BASE_URL}/{collection_path}"
        params = {'pageSize': 1000}
        if order_by:
            params['orderBy'] = f'fields.{order_by}'

        all_docs = []
        while True:
            resp = self._request('GET', url, params=params)
            self._check_error(resp)
            data = resp.json()

            documents = data.get('documents', [])
            for doc in documents:
                decoded = self._decode_document(doc)
                all_docs.append(decoded)

            next_token = data.get('nextPageToken')
            if not next_token:
                break
            params['pageToken'] = next_token

        return all_docs

    def create_document(self, collection_path: str, data: dict,
                        document_id: str = None) -> dict:
        """
        문서 생성.
        document_id 지정 시 해당 ID로 생성, 미지정 시 자동 ID.
        반환: 생성된 문서 dict ('id' 포함)
        """
        url = f"{FIRESTORE_BASE_URL}/{collection_path}"
        params = {}
        if document_id:
            params['documentId'] = document_id

        body = {'fields': self._encode_fields(data)}
        resp = self._request('POST', url, json=body, params=params)
        self._check_error(resp)

        return self._decode_document(resp.json())

    def update_document(self, doc_path: str, data: dict) -> dict:
        """
        문서 업데이트 (지정된 필드만 갱신).
        doc_path 예: "organizations/daechi_welfare/instructors/abc123"
        """
        url = f"{FIRESTORE_BASE_URL}/{doc_path}"

        # updateMask로 변경할 필드만 지정
        params = [('updateMask.fieldPaths', k) for k in data.keys()]
        body = {'fields': self._encode_fields(data)}

        resp = self._request('PATCH', url, json=body, params=params)
        self._check_error(resp)

        return self._decode_document(resp.json())

    def set_document(self, doc_path: str, data: dict) -> dict:
        """
        문서 전체 덮어쓰기 (없으면 생성).
        """
        url = f"{FIRESTORE_BASE_URL}/{doc_path}"
        body = {'fields': self._encode_fields(data)}

        resp = self._request('PATCH', url, json=body)
        self._check_error(resp)

        return self._decode_document(resp.json())

    def delete_document(self, doc_path: str):
        """문서 삭제."""
        url = f"{FIRESTORE_BASE_URL}/{doc_path}"
        resp = self._request('DELETE', url)
        self._check_error(resp)

    # ─────────────────────────────────────────
    # 구조화된 쿼리 (필터링용)
    # ─────────────────────────────────────────

    def _run_query(self, collection_path: str,
                   filters: list[tuple],
                   order_by: str = None) -> list[dict]:
        """structuredQuery를 사용한 필터링 조회"""
        # collection_path에서 parent와 collection_id 분리
        parts = collection_path.rsplit('/', 1)
        if len(parts) == 2:
            parent_path, collection_id = parts
            url = f"{FIRESTORE_BASE_URL}/{parent_path}:runQuery"
        else:
            collection_id = parts[0]
            url = f"{FIRESTORE_BASE_URL}:runQuery"

        # 필터 구성
        where_filters = []
        for field, op, value in filters:
            where_filters.append({
                'fieldFilter': {
                    'field': {'fieldPath': field},
                    'op': op,
                    'value': self._encode_value(value)
                }
            })

        structured_query = {
            'from': [{'collectionId': collection_id}],
        }

        if len(where_filters) == 1:
            structured_query['where'] = where_filters[0]
        elif len(where_filters) > 1:
            structured_query['where'] = {
                'compositeFilter': {
                    'op': 'AND',
                    'filters': where_filters
                }
            }

        if order_by:
            structured_query['orderBy'] = [
                {'field': {'fieldPath': order_by}, 'direction': 'ASCENDING'}
            ]

        body = {'structuredQuery': structured_query}
        resp = self._request('POST', url, json=body)
        self._check_error(resp)

        results = []
        for item in resp.json():
            doc = item.get('document')
            if doc:
                results.append(self._decode_document(doc))

        return results

    # ─────────────────────────────────────────
    # 값 인코딩 (Python → Firestore)
    # ─────────────────────────────────────────

    def _encode_fields(self, data: dict) -> dict:
        """Python dict → Firestore fields 형식 변환"""
        fields = {}
        for key, value in data.items():
            fields[key] = self._encode_value(value)
        return fields

    def _encode_value(self, value) -> dict:
        """Python 값 → Firestore value 타입 변환"""
        if value is None:
            return {'nullValue': None}
        elif isinstance(value, bool):
            return {'booleanValue': value}
        elif isinstance(value, int):
            return {'integerValue': str(value)}
        elif isinstance(value, float):
            return {'doubleValue': value}
        elif isinstance(value, str):
            return {'stringValue': value}
        elif isinstance(value, datetime):
            return {'timestampValue': value.isoformat()}
        elif isinstance(value, list):
            return {'arrayValue': {'values': [self._encode_value(v) for v in value]}}
        elif isinstance(value, dict):
            return {'mapValue': {'fields': self._encode_fields(value)}}
        else:
            return {'stringValue': str(value)}

    # ─────────────────────────────────────────
    # 값 디코딩 (Firestore → Python)
    # ─────────────────────────────────────────

    def _decode_document(self, raw: dict) -> dict:
        """Firestore 문서 → Python dict 변환 (id 필드 자동 추가)"""
        result = {}

        # 문서 이름에서 ID 추출
        name = raw.get('name', '')
        if name:
            result['id'] = name.rsplit('/', 1)[-1]
            result['_path'] = '/'.join(name.split('/documents/', 1)[-1:]) if '/documents/' in name else name

        # 필드 디코딩
        fields = raw.get('fields', {})
        for key, val in fields.items():
            result[key] = self._decode_value(val)

        return result

    def _decode_value(self, val: dict):
        """Firestore value → Python 값 변환"""
        if 'nullValue' in val:
            return None
        elif 'booleanValue' in val:
            return val['booleanValue']
        elif 'integerValue' in val:
            return int(val['integerValue'])
        elif 'doubleValue' in val:
            return val['doubleValue']
        elif 'stringValue' in val:
            return val['stringValue']
        elif 'timestampValue' in val:
            return val['timestampValue']
        elif 'arrayValue' in val:
            values = val['arrayValue'].get('values', [])
            return [self._decode_value(v) for v in values]
        elif 'mapValue' in val:
            fields = val['mapValue'].get('fields', {})
            return {k: self._decode_value(v) for k, v in fields.items()}
        else:
            return None

    # ─────────────────────────────────────────
    # HTTP 유틸리티
    # ─────────────────────────────────────────

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """인증 헤더 포함 HTTP 요청"""
        kwargs.setdefault('headers', {}).update(self._headers())
        kwargs.setdefault('timeout', 15)
        try:
            return requests.request(method, url, **kwargs)
        except requests.ConnectionError:
            raise FirestoreError('인터넷 연결을 확인해주세요.')
        except requests.Timeout:
            raise FirestoreError('서버 응답 시간이 초과되었습니다.')

    def _check_error(self, resp: requests.Response):
        """HTTP 응답 에러 체크"""
        if resp.status_code >= 400:
            try:
                error = resp.json().get('error', {})
                msg = error.get('message', f'HTTP {resp.status_code}')
            except Exception:
                msg = f'HTTP {resp.status_code}'
            raise FirestoreError(f'Firestore 오류: {msg}')
