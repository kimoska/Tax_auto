import os
import glob
from dataclasses import dataclass
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend


@dataclass
class CertificateInfo:
    subject_cn: str  # 소유자 이름 (보통 사람 이름 또는 법인명)
    issuer: str      # 발급기관 (예: yessign, KICA 등)
    expire_date: str # 만료일자 (YYYY-MM-DD 형식)
    path: str        # 인증서 폴더 경로
    is_expired: bool # 만료 여부

    @property
    def display_name(self) -> str:
        """UI에 표시할 이름"""
        return f"{self.subject_cn} ({self.issuer})"


class CertReader:
    """PC에 설치된 공동인증서(NPKI)를 스캔하고 파싱하는 유틸리티"""

    def __init__(self):
        # 주로 인증서가 저장되는 기본 경로 (하드디스크)
        self.default_npki_path = os.path.expanduser(r'~\AppData\LocalLow\NPKI')
        self.program_files_npki = r'C:\Program Files\NPKI'
        self.program_files_x86_npki = r'C:\Program Files (x86)\NPKI'

    def get_all_certificates(self, include_usb=True) -> list[CertificateInfo]:
        """PC 내의 모든 공동인증서 목록을 반환합니다."""
        target_dirs = [self.default_npki_path, self.program_files_npki, self.program_files_x86_npki]
        
        # USB 드라이브 추가 탐색
        if include_usb:
            target_dirs.extend(self._get_usb_npki_dirs())

        certs = []
        for base_dir in target_dirs:
            if not os.path.exists(base_dir):
                continue
            
            # signCert.der 파일 찾기 (모든 하위 디렉토리)
            der_files = glob.glob(os.path.join(base_dir, '**', 'signCert.der'), recursive=True)
            for der_path in der_files:
                cert_info = self._parse_certificate(der_path)
                if cert_info:
                    certs.append(cert_info)

        # 만료되지 않은 것을 위로, 날짜순 정렬
        certs.sort(key=lambda x: (x.is_expired, x.expire_date), reverse=False)
        return certs

    def _get_usb_npki_dirs(self) -> list[str]:
        """윈도우 이동식 디스크(USB)의 NPKI 폴더 목록을 반환합니다."""
        usb_dirs = []
        try:
            # 윈도우 C~Z 드라이브 중 이동식 디스크 찾기 (여기서는 단순 드라이브 문자 순회)
            import string
            for letter in string.ascii_uppercase:
                if letter == 'C':
                    continue
                drive_path = f"{letter}:\\NPKI"
                if os.path.exists(drive_path):
                    usb_dirs.append(drive_path)
        except Exception:
            pass
        return usb_dirs

    def _parse_certificate(self, der_path: str) -> CertificateInfo | None:
        """DER 포맷의 퍼블릭 인증서를 파싱하여 정보를 추출합니다."""
        try:
            with open(der_path, 'rb') as f:
                der_data = f.read()

            cert = x509.load_der_x509_certificate(der_data, default_backend())
            
            # 주체(Subject) 파싱
            subject_attrs = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            subject_cn = subject_attrs[0].value if subject_attrs else "Unknown"
            
            # 만약 CN에 괄호()가 있다면 괄호 전까지만 보통 이름임 (예: 홍길동(123456) -> 홍길동)
            # 깔끔하게 보여주기 위해 그대로 두거나 필요시 파싱 가능
            
            # 발급자(Issuer) 파싱 (보통 Organization Name)
            issuer_attrs = cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)
            if not issuer_attrs:
                issuer_attrs = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            issuer = issuer_attrs[0].value if issuer_attrs else "Unknown"

            # 날짜 파싱 (UTC -> 로컬타임 변환 간소화)
            expire_dt = getattr(cert, 'not_valid_after_utc', cert.not_valid_after)
            expire_date_str = expire_dt.strftime('%Y-%m-%d')
            
            # 만료 여부 확인
            is_expired = datetime.utcnow().replace(tzinfo=expire_dt.tzinfo) > expire_dt

            return CertificateInfo(
                subject_cn=subject_cn,
                issuer=issuer,
                expire_date=expire_date_str,
                path=os.path.dirname(der_path),
                is_expired=is_expired
            )
        except Exception as e:
            # 파싱 오류 발생 시 무시 (유효하지 않은 파일 등)
            return None
