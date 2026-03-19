"""
AutoTax — Fernet 암호화/복호화 관리자
plan.md §8.4 기반
주민번호, 인증서 비밀번호 등 민감 정보를 AES-256(Fernet)으로 암호화
"""
import os
from cryptography.fernet import Fernet


class CryptoManager:
    """Fernet(AES-256) 기반 암호화/복호화 관리자"""

    KEY_FILE = '.secret_key'

    def __init__(self, key_dir: str = None):
        """
        key_dir: .secret_key 파일을 저장/로드할 디렉토리.
        None이면 프로젝트 루트(Tax_auto/) 사용.
        """
        if key_dir:
            self.key_path = os.path.join(key_dir, self.KEY_FILE)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.key_path = os.path.join(base_dir, self.KEY_FILE)

        self.fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        """키 파일이 있으면 로드, 없으면 자동 생성"""
        if os.path.exists(self.key_path):
            with open(self.key_path, 'rb') as f:
                return f.read()
        else:
            print(f"🔑 암호화 키 최초 생성: {self.key_path}")
            key = Fernet.generate_key()
            # 디렉토리가 없으면 생성
            key_dir = os.path.dirname(self.key_path)
            if key_dir:
                os.makedirs(key_dir, exist_ok=True)
            with open(self.key_path, 'wb') as f:
                f.write(key)
            return key

    def encrypt(self, plaintext: str) -> str:
        """평문 → 암호문 (문자열 → 문자열)"""
        if not plaintext:
            return ''
        return self.fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """암호문 → 평문 (문자열 → 문자열)"""
        if not ciphertext:
            return ''
        return self.fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
