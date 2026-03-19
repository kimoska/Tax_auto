"""
AutoTax — 암호화/복호화 단위 테스트
"""
import os
import tempfile
import pytest
from core.crypto import CryptoManager


@pytest.fixture
def crypto_manager():
    """임시 디렉토리에서 CryptoManager 생성 (테스트 격리)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CryptoManager(key_dir=tmpdir)
        yield cm


class TestCryptoManager:
    """Fernet 암호화/복호화 테스트"""

    def test_encrypt_decrypt_roundtrip(self, crypto_manager):
        """암호화 → 복호화 왕복 테스트"""
        plaintext = '800101-1234567'
        encrypted = crypto_manager.encrypt(plaintext)
        decrypted = crypto_manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypted_differs_from_plaintext(self, crypto_manager):
        """암호문은 평문과 다름"""
        plaintext = '800101-1234567'
        encrypted = crypto_manager.encrypt(plaintext)
        assert encrypted != plaintext

    def test_korean_text(self, crypto_manager):
        """한글 텍스트 암호화/복호화"""
        plaintext = '비밀번호123!'
        encrypted = crypto_manager.encrypt(plaintext)
        decrypted = crypto_manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_empty_string(self, crypto_manager):
        """빈 문자열"""
        assert crypto_manager.encrypt('') == ''
        assert crypto_manager.decrypt('') == ''

    def test_key_file_created(self):
        """키 파일 자동 생성 확인"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CryptoManager(key_dir=tmpdir)
            key_path = os.path.join(tmpdir, '.secret_key')
            assert os.path.exists(key_path)

    def test_key_persistence(self):
        """같은 키 파일 → 같은 복호화 결과"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm1 = CryptoManager(key_dir=tmpdir)
            encrypted = cm1.encrypt('테스트 데이터')

            # 새 인스턴스가 같은 키를 로드하여 복호화 가능
            cm2 = CryptoManager(key_dir=tmpdir)
            decrypted = cm2.decrypt(encrypted)
            assert decrypted == '테스트 데이터'

    def test_different_keys_cannot_decrypt(self):
        """다른 키로 복호화 불가"""
        with tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:
            cm1 = CryptoManager(key_dir=tmpdir1)
            cm2 = CryptoManager(key_dir=tmpdir2)

            encrypted = cm1.encrypt('비밀 데이터')
            with pytest.raises(Exception):
                cm2.decrypt(encrypted)
