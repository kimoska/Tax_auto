"""
AutoTax — Firebase Authentication REST API 래퍼
클라이언트 사이드 이메일/비밀번호 인증 + 토큰 관리
"""
import time
import requests
from core.config import FIREBASE_CONFIG, FIREBASE_AUTH_URL, FIREBASE_TOKEN_URL


class AuthError(Exception):
    """Firebase 인증 관련 오류"""

    ERROR_MESSAGES = {
        'EMAIL_EXISTS': '이미 등록된 이메일 주소입니다.',
        'INVALID_EMAIL': '유효하지 않은 이메일 주소입니다.',
        'WEAK_PASSWORD': '비밀번호는 6자 이상이어야 합니다.',
        'EMAIL_NOT_FOUND': '등록되지 않은 이메일 주소입니다.',
        'INVALID_PASSWORD': '비밀번호가 올바르지 않습니다.',
        'INVALID_LOGIN_CREDENTIALS': '이메일 또는 비밀번호가 올바르지 않습니다.',
        'USER_DISABLED': '비활성화된 계정입니다. 관리자에게 문의하세요.',
        'TOO_MANY_ATTEMPTS_TRY_LATER': '로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요.',
    }

    def __init__(self, code: str, raw_message: str = ''):
        self.code = code
        user_msg = self.ERROR_MESSAGES.get(code, raw_message or f'인증 오류: {code}')
        super().__init__(user_msg)


class FirebaseAuth:
    """Firebase Auth REST API 클라이언트"""

    def __init__(self):
        self.api_key = FIREBASE_CONFIG['apiKey']

        # 인증 세션 정보
        self.id_token: str | None = None
        self.refresh_token_str: str | None = None
        self.uid: str | None = None
        self.email: str | None = None
        self.org_id: str | None = None
        self._token_expires_at: float = 0

    @property
    def is_authenticated(self) -> bool:
        return self.id_token is not None

    @property
    def token(self) -> str:
        """유효한 ID 토큰 반환 (필요 시 자동 갱신)"""
        if not self.id_token:
            raise AuthError('NOT_AUTHENTICATED', '로그인이 필요합니다.')
        if time.time() >= self._token_expires_at - 60:
            self._refresh_token()
        return self.id_token

    def sign_up(self, email: str, password: str) -> dict:
        """
        이메일/비밀번호 회원가입.
        반환: {'uid': ..., 'email': ..., 'id_token': ...}
        """
        url = f"{FIREBASE_AUTH_URL}/accounts:signUp?key={self.api_key}"
        payload = {
            'email': email,
            'password': password,
            'returnSecureToken': True
        }
        data = self._post(url, payload)

        self._store_session(data)
        return {
            'uid': self.uid,
            'email': self.email,
            'id_token': self.id_token
        }

    def sign_in(self, email: str, password: str) -> dict:
        """
        이메일/비밀번호 로그인.
        반환: {'uid': ..., 'email': ..., 'id_token': ...}
        """
        url = f"{FIREBASE_AUTH_URL}/accounts:signInWithPassword?key={self.api_key}"
        payload = {
            'email': email,
            'password': password,
            'returnSecureToken': True
        }
        data = self._post(url, payload)

        self._store_session(data)
        return {
            'uid': self.uid,
            'email': self.email,
            'id_token': self.id_token
        }

    def sign_out(self):
        """로그아웃 (로컬 세션 초기화)"""
        self.id_token = None
        self.refresh_token_str = None
        self.uid = None
        self.email = None
        self.org_id = None
        self._token_expires_at = 0

    def _refresh_token(self):
        """리프레시 토큰으로 ID 토큰 갱신"""
        if not self.refresh_token_str:
            raise AuthError('NO_REFRESH_TOKEN', '다시 로그인해주세요.')

        url = f"{FIREBASE_TOKEN_URL}/token?key={self.api_key}"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token_str
        }
        data = self._post(url, payload)

        self.id_token = data.get('id_token')
        self.refresh_token_str = data.get('refresh_token')
        expires_in = int(data.get('expires_in', 3600))
        self._token_expires_at = time.time() + expires_in

    def _store_session(self, data: dict):
        """API 응답에서 세션 정보 저장"""
        self.id_token = data.get('idToken')
        self.refresh_token_str = data.get('refreshToken')
        self.uid = data.get('localId')
        self.email = data.get('email')
        expires_in = int(data.get('expiresIn', 3600))
        self._token_expires_at = time.time() + expires_in

    def _post(self, url: str, payload: dict) -> dict:
        """HTTP POST 요청 (에러 핸들링 및 재시도 로직 포함)"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, json=payload, timeout=15)
                break  # 성공 시 루프 탈출
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < max_retries - 1:
                    time.sleep(1) # 1초 후 재시도
                    continue
                if isinstance(e, requests.ConnectionError):
                    raise AuthError('NETWORK_ERROR', '인터넷 연결을 확인해주세요.')
                else:
                    raise AuthError('TIMEOUT', '서버 응답 시간이 초과되었습니다.')

        data = resp.json()

        if resp.status_code != 200:
            error = data.get('error', {})
            code = error.get('message', 'UNKNOWN_ERROR')
            raise AuthError(code)

        return data
