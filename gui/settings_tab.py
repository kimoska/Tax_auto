"""
AutoTax — [탭5] 시스템 설정 탭
plan.md §5.4 — 기관정보 + 인증서 설정
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QComboBox, QFileDialog
)
from PySide6.QtCore import Qt

from gui.widgets import (
    Panel, Colors, BTN_PRIMARY, BTN_SECONDARY
)
from db.repository import Repository
from core.crypto import CryptoManager


class SettingsTab(QWidget):
    """시스템 설정 탭 — 기관정보 + NTS 인증 설정"""

    def __init__(self, repo: Repository, crypto: CryptoManager, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.crypto = crypto
        self.setObjectName('settingsTab')
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        input_style = f"""
            QLineEdit, QComboBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {Colors.ACCENT};
            }}
        """
        label_style = f"font-size: 13px; font-weight: 500; color: {Colors.TEXT_PRIMARY};"

        # ── 기관 정보 패널 ──
        org_panel = Panel('기관(지급자) 정보')

        org_body = QWidget()
        org_layout = QVBoxLayout(org_body)
        org_layout.setContentsMargins(24, 20, 24, 20)
        org_layout.setSpacing(14)

        row1 = QHBoxLayout()
        col1 = QVBoxLayout()
        lbl = QLabel('기관명')
        lbl.setStyleSheet(label_style)
        col1.addWidget(lbl)
        self.org_name = QLineEdit()
        self.org_name.setStyleSheet(input_style)
        self.org_name.setPlaceholderText('예: 강원도대치노인복지관')
        col1.addWidget(self.org_name)

        col2 = QVBoxLayout()
        lbl2 = QLabel('사업자등록번호')
        lbl2.setStyleSheet(label_style)
        col2.addWidget(lbl2)
        self.org_biz = QLineEdit()
        self.org_biz.setStyleSheet(input_style)
        self.org_biz.setPlaceholderText('000-00-00000')
        col2.addWidget(self.org_biz)

        row1.addLayout(col1)
        row1.addLayout(col2)
        org_layout.addLayout(row1)

        row2 = QHBoxLayout()
        col3 = QVBoxLayout()
        lbl3 = QLabel('대표자')
        lbl3.setStyleSheet(label_style)
        col3.addWidget(lbl3)
        self.org_rep = QLineEdit()
        self.org_rep.setStyleSheet(input_style)
        col3.addWidget(self.org_rep)

        col4 = QVBoxLayout()
        lbl4 = QLabel('관할 세무서')
        lbl4.setStyleSheet(label_style)
        col4.addWidget(lbl4)
        self.org_tax_office = QLineEdit()
        self.org_tax_office.setStyleSheet(input_style)
        col4.addWidget(self.org_tax_office)

        row2.addLayout(col3)
        row2.addLayout(col4)
        org_layout.addLayout(row2)

        addr_col = QVBoxLayout()
        lbl5 = QLabel('주소')
        lbl5.setStyleSheet(label_style)
        addr_col.addWidget(lbl5)
        self.org_address = QLineEdit()
        self.org_address.setStyleSheet(input_style)
        addr_col.addWidget(self.org_address)
        org_layout.addLayout(addr_col)

        org_panel.body_layout.addWidget(org_body)
        layout.addWidget(org_panel)

        # ── 홈택스 인증 설정 ──
        auth_panel = Panel('홈택스 인증 설정')

        auth_body = QWidget()
        auth_layout = QVBoxLayout(auth_body)
        auth_layout.setContentsMargins(24, 20, 24, 20)
        auth_layout.setSpacing(14)

        lbl_method = QLabel('인증 방식')
        lbl_method.setStyleSheet(label_style)
        auth_layout.addWidget(lbl_method)
        self.auth_method = QComboBox()
        self.auth_method.setStyleSheet(input_style)
        self.auth_method.addItem('공동·금융인증서', 'certificate')
        self.auth_method.addItem('간편인증 (민간인증서)', 'simple')
        self.auth_method.addItem('모바일신분증', 'mobile_id')
        self.auth_method.addItem('생체(얼굴·지문) 인증', 'bio')
        self.auth_method.addItem('비회원 로그인', 'non_member')
        auth_layout.addWidget(self.auth_method)

        # ── 인증서 저장 위치 ──
        lbl_location = QLabel('인증서 저장 위치')
        lbl_location.setStyleSheet(label_style)
        auth_layout.addWidget(lbl_location)
        self.cert_location = QComboBox()
        self.cert_location.setStyleSheet(input_style)
        self.cert_location.addItem('하드디스크 이동식', 'harddisk')
        self.cert_location.addItem('브라우저', 'browser')
        self.cert_location.addItem('금융인증서', 'financial')
        self.cert_location.addItem('휴대전화', 'mobile')
        self.cert_location.addItem('스마트인증', 'smart')
        auth_layout.addWidget(self.cert_location)

        # ── 인증서 소유자 키워드 ──
        lbl_keyword = QLabel('인증서 소유자 키워드 (선택)')
        lbl_keyword.setStyleSheet(label_style)
        auth_layout.addWidget(lbl_keyword)
        self.cert_keyword = QLineEdit()
        self.cert_keyword.setStyleSheet(input_style)
        self.cert_keyword.setPlaceholderText('예: 김관영 (비워두면 첫 번째 인증서 사용)')
        auth_layout.addWidget(self.cert_keyword)

        cert_row = QHBoxLayout()
        cert_col = QVBoxLayout()
        lbl_cert = QLabel('인증서 경로')
        lbl_cert.setStyleSheet(label_style)
        cert_col.addWidget(lbl_cert)
        cert_input_row = QHBoxLayout()
        self.cert_path = QLineEdit()
        self.cert_path.setStyleSheet(input_style)
        self.cert_path.setPlaceholderText('C:\\Users\\...\\NPKI\\...')
        btn_browse = QPushButton('찾아보기')
        btn_browse.setStyleSheet(BTN_SECONDARY + "QPushButton { padding: 8px 14px; }")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self._browse_cert)
        cert_input_row.addWidget(self.cert_path)
        cert_input_row.addWidget(btn_browse)
        cert_col.addLayout(cert_input_row)
        cert_row.addLayout(cert_col)
        auth_layout.addLayout(cert_row)

        pw_col = QVBoxLayout()
        lbl_pw = QLabel('인증서 비밀번호 (암호화 저장)')
        lbl_pw.setStyleSheet(label_style)
        pw_col.addWidget(lbl_pw)
        self.cert_password = QLineEdit()
        self.cert_password.setEchoMode(QLineEdit.Password)
        self.cert_password.setStyleSheet(input_style)
        self.cert_password.setPlaceholderText('••••••••')
        pw_col.addWidget(self.cert_password)
        auth_layout.addLayout(pw_col)

        auth_panel.body_layout.addWidget(auth_body)
        layout.addWidget(auth_panel)

        # ── 저장 버튼 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton('설정 저장')
        btn_save.setStyleSheet(BTN_PRIMARY + "QPushButton { padding: 12px 32px; font-size: 14px; }")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save_settings)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)
        layout.addStretch()

    def _browse_cert(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '인증서 파일 선택', '',
            '인증서 파일 (*.pfx *.p12 *.der);;모든 파일 (*.*)'
        )
        if path:
            self.cert_path.setText(path)

    def _load_settings(self):
        """DB에서 설정값 로드"""
        def _get(key):
            s = self.repo.get_setting(key)
            return s['value'] if s else ''

        self.org_name.setText(_get('org_name'))
        self.org_biz.setText(_get('org_biz_number'))
        self.org_rep.setText(_get('org_representative'))
        self.org_tax_office.setText(_get('org_tax_office'))
        self.org_address.setText(_get('org_address'))

        method = _get('auth_method')
        idx = self.auth_method.findData(method)
        if idx >= 0:
            self.auth_method.setCurrentIndex(idx)

        self.cert_path.setText(_get('cert_path'))

        location = _get('cert_location')
        loc_idx = self.cert_location.findData(location)
        if loc_idx >= 0:
            self.cert_location.setCurrentIndex(loc_idx)

        self.cert_keyword.setText(_get('cert_keyword'))

        # 비밀번호 복호화
        pw_setting = self.repo.get_setting('cert_password')
        if pw_setting and pw_setting['value']:
            try:
                decrypted = self.crypto.decrypt(pw_setting['value'])
                self.cert_password.setText(decrypted)
            except Exception:
                pass

    def _save_settings(self):
        """설정값 DB에 저장"""
        self.repo.update_setting('org_name', self.org_name.text().strip())
        self.repo.update_setting('org_biz_number', self.org_biz.text().strip())
        self.repo.update_setting('org_representative', self.org_rep.text().strip())
        self.repo.update_setting('org_tax_office', self.org_tax_office.text().strip())
        self.repo.update_setting('org_address', self.org_address.text().strip())
        self.repo.update_setting('auth_method', self.auth_method.currentData())
        self.repo.update_setting('cert_location', self.cert_location.currentData())
        self.repo.update_setting('cert_keyword', self.cert_keyword.text().strip())
        self.repo.update_setting('cert_path', self.cert_path.text().strip())

        # 비밀번호 암호화 저장
        pw = self.cert_password.text().strip()
        if pw:
            encrypted = self.crypto.encrypt(pw)
            self.repo.update_setting('cert_password', encrypted, is_encrypted=1)

        QMessageBox.information(self, '설정 저장', '설정이 저장되었습니다.')
