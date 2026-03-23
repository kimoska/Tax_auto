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



    def _save_settings(self):
        """설정값 DB에 저장"""
        self.repo.update_setting('org_name', self.org_name.text().strip())
        self.repo.update_setting('org_biz_number', self.org_biz.text().strip())
        self.repo.update_setting('org_representative', self.org_rep.text().strip())
        self.repo.update_setting('org_tax_office', self.org_tax_office.text().strip())
        self.repo.update_setting('org_address', self.org_address.text().strip())


        QMessageBox.information(self, '설정 저장', '설정이 저장되었습니다.')
