"""
AutoTax - 초기 로그인 윈도우 (로컬 UI)
프로그램 মে인 화면 진입 전, 홈택스 작업에 사용할 인증서를 미리 선택하는 모듈입니다.
"""
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMessageBox, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from db.repository import Repository
from core.crypto import CryptoManager
from core.cert_reader import CertReader, CertificateInfo


class LoginWindow(QDialog):
    """
    초기 실행 시 나타나는 공동인증서 선택 모달 창.
    """
    def __init__(self, repo: Repository, crypto: CryptoManager, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.crypto = crypto
        
        # 인증서 리더
        self.cert_reader = CertReader()
        self.harddisk_certs: list[CertificateInfo] = []
        self.usb_certs: list[CertificateInfo] = []
        self.selected_cert: Optional[CertificateInfo] = None

        self.setWindowTitle("AutoTax - 공동인증서 로그인")
        self.setFixedSize(550, 480)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; }
            QTabWidget::pane { border: 1px solid #CCC; background: white; }
            QTabBar::tab { background: #E9ECEF; padding: 10px 20px; border: 1px solid #CCC; border-bottom: none; }
            QTabBar::tab:selected { background: white; font-weight: bold; border-top: 3px solid #0078D7; }
        """)
        
        self._load_certificates()
        self._setup_ui()
        self._load_saved_credentials()

    def _load_certificates(self):
        """PC의 인증서를 읽어옵니다."""
        all_certs = self.cert_reader.get_all_certificates(include_usb=True)
        
        self.harddisk_certs = []
        self.usb_certs = []
        
        for c in all_certs:
            if c.path.startswith("C:"):
                self.harddisk_certs.append(c)
            else:
                self.usb_certs.append(c)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 타이틀
        title = QLabel("AutoTax 공동인증서 로그인")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("홈택스 자동 업로드에 사용할 인증서를 선택해주세요.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # 탭 위젯 (하드디스크 / 이동식디스크)
        self.tabs = QTabWidget()
        
        self.tab_hdd = QWidget()
        self.tab_usb = QWidget()
        
        self._setup_tab(self.tab_hdd, self.harddisk_certs, "hdd")
        self._setup_tab(self.tab_usb, self.usb_certs, "usb")
        
        self.tabs.addTab(self.tab_hdd, "하드디스크")
        self.tabs.addTab(self.tab_usb, "이동식디스크")
        layout.addWidget(self.tabs)

        # 비밀번호 입력란 구성
        self.pw_layout = QHBoxLayout()
        self.pw_label = QLabel("인증서 비밀번호 :")
        self.pw_label.setFont(QFont("Pretendard", 10, QFont.Bold))
        
        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.Password)
        self.pw_input.setPlaceholderText('선택한 인증서의 비밀번호 입력')
        self.pw_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #0078D7;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:disabled { background: #EEE; border: 1px solid #CCC; }
        """)
        self.pw_input.returnPressed.connect(self._on_start_clicked)
        
        self.pw_layout.addWidget(self.pw_label)
        self.pw_layout.addWidget(self.pw_input, 1)
        layout.addLayout(self.pw_layout)

        # 저장 체크박스
        self.cb_save = QCheckBox("로그인 정보 기억하기 (자동 업로드 시 바로 사용)")
        self.cb_save.setChecked(True)
        layout.addWidget(self.cb_save)

        # 취소 / 시작 버튼
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("프로그램 종료")
        self.btn_cancel.setMinimumHeight(45)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_start = QPushButton("보안 로그인")
        self.btn_start.setMinimumHeight(45)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #005A9E; }
        """)
        self.btn_start.clicked.connect(self._on_start_clicked)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_start, 2)
        layout.addLayout(btn_layout)

    def _setup_tab(self, parent_widget: QWidget, certs: list[CertificateInfo], tab_type: str):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['구분(발급자)', '사용자', '만료일자'])
        
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
        table.setStyleSheet("""
            QTableWidget { border: none; font-size: 12px; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #E3F2FD; color: black; }
        """)
        
        table.setRowCount(len(certs))
        for row, cert in enumerate(certs):
            # 발급자
            item_issuer = QTableWidgetItem(cert.issuer)
            # 사용자명
            item_cn = QTableWidgetItem(cert.subject_cn)
            item_cn.setFont(QFont("Pretendard", 10, QFont.Bold))
            # 만료일
            item_expire = QTableWidgetItem(cert.expire_date)
            
            if cert.is_expired:
                item_expire.setForeground(QColor("red"))
                item_expire.setText(item_expire.text() + " (만료)")
            
            table.setItem(row, 0, item_issuer)
            table.setItem(row, 1, item_cn)
            table.setItem(row, 2, item_expire)
            
            # 행별로 데이터 보관
            table.item(row, 0).setData(Qt.UserRole, cert)
            
        table.itemSelectionChanged.connect(lambda t=table: self._on_cert_selected(t))
        
        # 속성 저장
        if tab_type == "hdd":
            self.table_hdd = table
        else:
            self.table_usb = table
            
        layout.addWidget(table)

    def _on_cert_selected(self, table: QTableWidget):
        """테이블에서 인증서를 클릭했을 때"""
        selected_rows = table.selectedItems()
        if not selected_rows:
            return
            
        # 클릭된 행의 UserRole(CertificateInfo 객체) 가져오기
        row = selected_rows[0].row()
        cert: CertificateInfo = table.item(row, 0).data(Qt.UserRole)
        self.selected_cert = cert
        
        # 반대쪽 탭테이블 선택 해제
        if table == self.table_hdd:
            self.table_usb.clearSelection()
        else:
            self.table_hdd.clearSelection()
            
        self.pw_input.setFocus()

    def _load_saved_credentials(self):
        """DB에서 이전에 저장된 인증서 키워드와 비밀번호를 불러옵니다."""
        keyword_setting = self.repo.get_setting('cert_keyword')
        saved_cn = keyword_setting['value'] if keyword_setting else None
        
        # 드라이브 정보도 함께 불러오기 (HDD/USB 구분용)
        drive_setting = self.repo.get_setting('cert_drive')
        saved_drive = drive_setting['value'] if drive_setting else 'C'
        
        if saved_cn:
            if saved_drive == 'C':
                # 하드디스크 탭에서 먼저 찾기
                found = self._select_cert_by_cn(self.table_hdd, saved_cn)
                if found:
                    self.tabs.setCurrentIndex(0)
                else:
                    found = self._select_cert_by_cn(self.table_usb, saved_cn)
                    if found:
                        self.tabs.setCurrentIndex(1)
            else:
                # 이동식디스크 탭에서 먼저 찾기
                found = self._select_cert_by_cn(self.table_usb, saved_cn)
                if found:
                    self.tabs.setCurrentIndex(1)
                else:
                    found = self._select_cert_by_cn(self.table_hdd, saved_cn)
                    if found:
                        self.tabs.setCurrentIndex(0)

        # 비밀번호 로드
        pw_setting = self.repo.get_setting('cert_password')
        if pw_setting and pw_setting.get('value'):
            try:
                dec_pw = self.crypto.decrypt(pw_setting['value'])
                self.pw_input.setText(dec_pw)
            except Exception:
                pass

    def _select_cert_by_cn(self, table: QTableWidget, target_cn: str) -> bool:
        """이름으로 행을 찾아 자동으로 선택합니다."""
        for row in range(table.rowCount()):
            cert: CertificateInfo = table.item(row, 0).data(Qt.UserRole)
            if cert.subject_cn == target_cn:
                table.selectRow(row)
                return True
        return False

    def _on_start_clicked(self):
        password = self.pw_input.text()
        
        if not self.selected_cert:
            QMessageBox.warning(self, "입력 오류", "사용할 공동인증서를 목록에서 선택하세요.")
            return
            
        if not password:
            QMessageBox.warning(self, "입력 오류", "인증서 비밀번호를 입력해주세요.")
            self.pw_input.setFocus()
            return
            
        if self.selected_cert.is_expired:
            reply = QMessageBox.question(
                self, "만료된 인증서", 
                "만료된 인증서입니다. 계속 진행하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # 인증 설정 DB 저장 (향후 RPARunner에서 활용)
        if self.cb_save.isChecked():
            # 인증 방식은 공동인증서로 고정
            self.repo.update_setting('auth_method', 'certificate')
            # 인증서 고유 식별자 저장 (CN 기준)
            self.repo.update_setting('cert_keyword', self.selected_cert.subject_cn)
            
            # 드라이브 문자 (C, D 등) 저장
            drive_letter = self.selected_cert.path[0].upper() if self.selected_cert.path else 'C'
            self.repo.update_setting('cert_drive', drive_letter)
            
            try:
                enc_pw = self.crypto.encrypt(password)
                self.repo.update_setting('cert_password', enc_pw, is_encrypted=1)
            except Exception:
                pass
        
        # 이제 더이상 여기서 홈택스 웹에 접속하지 않으므로, 쿨하게 완료하고 메인화면으로 진입!
        self.accept()
