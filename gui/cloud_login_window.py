"""
AutoTax — 클라우드 로그인 윈도우
기관 등록 + 직원 로그인/가입 2모드 UI
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QWidget, QLineEdit,
    QStackedWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


from core.firebase_auth import FirebaseAuth, AuthError
from core.firestore_client import FirestoreClient, FirestoreError


# ─────────────────────────────────────────
# 백그라운드 작업 스레드
# ─────────────────────────────────────────

class OrgRegisterWorker(QThread):
    """기관 등록 백그라운드 작업"""
    success = Signal(str)  # org_id
    error = Signal(str)

    def __init__(self, auth, org_name, org_code):
        super().__init__()
        self.auth = auth
        self.org_name = org_name
        self.org_code = org_code

    def run(self):
        try:
            import datetime
            client = FirestoreClient(self.auth)

            # 코드 중복 확인
            existing = client.get_document(f'org_codes/{self.org_code}')
            if existing:
                self.error.emit('이미 사용 중인 기관코드입니다. 다른 코드를 입력해주세요.')
                return

            # org_id 생성 (코드를 기반으로)
            org_id = self.org_code.lower().replace('-', '_')

            # org_codes 문서 생성
            client.set_document(f'org_codes/{self.org_code}', {
                'org_id': org_id,
                'org_name': self.org_name,
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            # organizations 문서 생성
            client.set_document(f'organizations/{org_id}', {
                'name': self.org_name,
                'biz_number': '',
                'representative': '',
                'address': '',
                'tax_office': '',
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            self.success.emit(org_id)

        except (FirestoreError, AuthError) as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f'기관 등록 중 오류가 발생했습니다: {e}')


class LoginWorker(QThread):
    """로그인/가입 백그라운드 작업"""
    success = Signal(str, str)  # uid, org_id
    error = Signal(str)

    def __init__(self, auth, email, password, org_code, is_signup=False):
        super().__init__()
        self.auth = auth
        self.email = email
        self.password = password
        self.org_code = org_code
        self.is_signup = is_signup

    def run(self):
        try:
            import datetime
            client = FirestoreClient(self.auth)

            # 1) 기관 코드 확인
            org_doc = client.get_document(f'org_codes/{self.org_code}')
            if not org_doc:
                self.error.emit('존재하지 않는 기관코드입니다.\n기관 관리자에게 정확한 코드를 확인해주세요.')
                return

            org_id = org_doc['org_id']

            if self.is_signup:
                # 2) 회원가입
                result = self.auth.sign_up(self.email, self.password)

                # 3) users 프로필 문서 생성
                client.set_document(f'users/{self.auth.uid}', {
                    'email': self.email,
                    'org_id': org_id,
                    'display_name': self.email.split('@')[0],
                    'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                # 2) 로그인
                result = self.auth.sign_in(self.email, self.password)

                # 3) users 프로필에서 org_id 조회
                user_doc = client.get_document(f'users/{self.auth.uid}')
                if not user_doc or user_doc.get('org_id') != org_id:
                    self.auth.sign_out()
                    self.error.emit('이 계정은 해당 기관에 등록되어 있지 않습니다.')
                    return

            self.auth.org_id = org_id
            self.success.emit(self.auth.uid, org_id)

        except AuthError as e:
            self.error.emit(str(e))
        except FirestoreError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f'처리 중 오류가 발생했습니다: {e}')


# ─────────────────────────────────────────
# 메인 로그인 윈도우
# ─────────────────────────────────────────

class CloudLoginWindow(QDialog):
    """클라우드 로그인 윈도우 — 기관 등록 / 직원 로그인 2모드"""

    def __init__(self, auth: FirebaseAuth, parent=None):
        super().__init__(parent)
        self.auth = auth
        self._worker = None

        self.setWindowTitle("AutoTax — 로그인")
        self.setFixedSize(480, 680)
        self.setModal(True)

        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; }
        """)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 28, 40, 20)
        layout.setSpacing(0)

        # ── 상단 로고 영역 ──
        logo = QLabel('AutoTax Cloud')
        logo.setStyleSheet('color: #1E293B; font-size: 24px; font-weight: 700;')
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        subtitle = QLabel('강사료 원천세 자동화 시스템')
        subtitle.setStyleSheet('color: #64748B; font-size: 12px;')
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        # ── 모드 전환 탭 ──
        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)

        self.btn_login_mode = QPushButton('직원 로그인')
        self.btn_login_mode.setCursor(Qt.PointingHandCursor)
        self.btn_login_mode.setFixedHeight(42)
        self.btn_login_mode.clicked.connect(lambda: self._switch_mode(0))

        self.btn_register_mode = QPushButton('기관 등록')
        self.btn_register_mode.setCursor(Qt.PointingHandCursor)
        self.btn_register_mode.setFixedHeight(42)
        self.btn_register_mode.clicked.connect(lambda: self._switch_mode(1))

        tab_row.addWidget(self.btn_login_mode)
        tab_row.addWidget(self.btn_register_mode)
        layout.addLayout(tab_row)

        # ── 콘텐츠 스택 ──
        self.stack = QStackedWidget()

        self.login_page = self._create_login_page()
        self.register_page = self._create_register_page()

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.register_page)

        layout.addWidget(self.stack)
        layout.addStretch()

        # ── 하단 상태 메시지 ──
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #64748B; font-size: 11px;')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # 초기 모드
        self._switch_mode(0)

    def _switch_mode(self, mode: int):
        """모드 전환 (0: 로그인, 1: 기관등록)"""
        self.stack.setCurrentIndex(mode)
        self.status_label.setText('')

        active_style = """
            QPushButton {
                background: #FFFFFF; color: #1E293B;
                border: 1px solid #E2E8F0; border-bottom: 3px solid #3B82F6;
                font-size: 14px; font-weight: 600;
            }
        """
        inactive_style = """
            QPushButton {
                background: #F8FAFC; color: #94A3B8;
                border: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0;
                font-size: 14px; font-weight: 500;
            }
            QPushButton:hover { color: #64748B; background: #F1F5F9; }
        """

        self.btn_login_mode.setStyleSheet(active_style if mode == 0 else inactive_style)
        self.btn_register_mode.setStyleSheet(active_style if mode == 1 else inactive_style)

    # ─────────────────────────────────────────
    # 직원 로그인/가입 페이지
    # ─────────────────────────────────────────

    def _create_login_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(6)

        input_style = """
            QLineEdit {
                background: #F8FAFC; color: #1E293B;
                border: 2px solid #CBD5E1; border-radius: 8px;
                padding: 10px 14px; font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus { border-color: #3B82F6; background: #FFFFFF; }
            QLineEdit::placeholder { color: #94A3B8; }
        """
        label_style = 'color: #334155; font-size: 13px; font-weight: 600; margin-top: 6px;'

        # 이메일
        lbl_email = QLabel('이메일')
        lbl_email.setStyleSheet(label_style)
        layout.addWidget(lbl_email)

        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText('example@email.com')
        self.login_email.setStyleSheet(input_style)
        layout.addWidget(self.login_email)

        # 비밀번호
        lbl_pw = QLabel('비밀번호')
        lbl_pw.setStyleSheet(label_style)
        layout.addWidget(lbl_pw)

        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setPlaceholderText('6자 이상 입력')
        self.login_password.setStyleSheet(input_style)
        layout.addWidget(self.login_password)

        # 기관코드
        lbl_code = QLabel('기관코드')
        lbl_code.setStyleSheet(label_style)
        layout.addWidget(lbl_code)

        self.login_org_code = QLineEdit()
        self.login_org_code.setPlaceholderText('관리자에게 받은 기관코드 입력')
        self.login_org_code.setStyleSheet(input_style)
        self.login_org_code.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self.login_org_code)

        layout.addSpacing(12)

        # 버튼 행
        btn_row = QHBoxLayout()

        self.btn_signup = QPushButton('회원가입')
        self.btn_signup.setCursor(Qt.PointingHandCursor)
        self.btn_signup.setFixedHeight(46)
        self.btn_signup.setStyleSheet("""
            QPushButton {
                background: #FFFFFF; color: #3B82F6;
                border: 2px solid #3B82F6; border-radius: 8px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #EFF6FF; }
            QPushButton:disabled { color: #CBD5E1; border-color: #CBD5E1; }
        """)
        self.btn_signup.clicked.connect(self._on_signup_clicked)

        self.btn_login = QPushButton('로그인')
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setFixedHeight(46)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background: #3B82F6; color: white;
                border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #2563EB; }
            QPushButton:disabled { background: #CBD5E1; }
        """)
        self.btn_login.clicked.connect(self._on_login_clicked)

        btn_row.addWidget(self.btn_signup)
        btn_row.addWidget(self.btn_login, 2)
        layout.addLayout(btn_row)

        return page

    # ─────────────────────────────────────────
    # 기관 등록 페이지
    # ─────────────────────────────────────────

    def _create_register_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(6)

        input_style = """
            QLineEdit {
                background: #F8FAFC; color: #1E293B;
                border: 2px solid #CBD5E1; border-radius: 8px;
                padding: 10px 14px; font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus { border-color: #3B82F6; background: #FFFFFF; }
            QLineEdit::placeholder { color: #94A3B8; }
        """
        label_style = 'color: #334155; font-size: 13px; font-weight: 600; margin-top: 4px;'

        # 안내 문구
        guide = QLabel('ℹ️  기관 등록은 최초 1회만 수행합니다. 등록 후 기관코드를 직원들에게 공유하세요.')
        guide.setStyleSheet(
            'color: #1D4ED8; font-size: 11px; padding: 10px 12px;'
            'background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px;'
        )
        guide.setWordWrap(True)
        layout.addWidget(guide)

        # 관리자 이메일
        lbl_admin_email = QLabel('관리자 이메일')
        lbl_admin_email.setStyleSheet(label_style)
        layout.addWidget(lbl_admin_email)

        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText('관리자 계정 이메일')
        self.reg_email.setStyleSheet(input_style)
        layout.addWidget(self.reg_email)

        # 관리자 비밀번호
        lbl_admin_pw = QLabel('관리자 비밀번호')
        lbl_admin_pw.setStyleSheet(label_style)
        layout.addWidget(lbl_admin_pw)

        self.reg_password = QLineEdit()
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_password.setPlaceholderText('6자 이상 입력')
        self.reg_password.setStyleSheet(input_style)
        layout.addWidget(self.reg_password)

        # 기관명
        lbl_org = QLabel('기관명')
        lbl_org.setStyleSheet(label_style)
        layout.addWidget(lbl_org)

        self.reg_org_name = QLineEdit()
        self.reg_org_name.setPlaceholderText('예: 대치노인복지관')
        self.reg_org_name.setStyleSheet(input_style)
        layout.addWidget(self.reg_org_name)

        # 기관코드
        lbl_code = QLabel('기관코드 (직접 설정)')
        lbl_code.setStyleSheet(label_style)
        layout.addWidget(lbl_code)

        self.reg_org_code = QLineEdit()
        self.reg_org_code.setPlaceholderText('예: myorg2026 (영문/숫자)')
        self.reg_org_code.setStyleSheet(input_style)
        self.reg_org_code.returnPressed.connect(self._on_register_clicked)
        layout.addWidget(self.reg_org_code)

        layout.addSpacing(10)

        # 등록 버튼
        self.btn_register = QPushButton('기관 등록하기')
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.setFixedHeight(46)
        self.btn_register.setStyleSheet("""
            QPushButton {
                background: #10B981; color: white;
                border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:disabled { background: #CBD5E1; }
        """)
        self.btn_register.clicked.connect(self._on_register_clicked)
        layout.addWidget(self.btn_register)

        return page

    # ─────────────────────────────────────────
    # 이벤트 핸들러
    # ─────────────────────────────────────────

    def _on_login_clicked(self):
        email = self.login_email.text().strip()
        pw = self.login_password.text()
        code = self.login_org_code.text().strip()

        if not email or not pw or not code:
            QMessageBox.warning(self, '입력 오류', '이메일, 비밀번호, 기관코드를 모두 입력하세요.')
            return

        self._set_loading(True)
        self.status_label.setText('🔐 로그인 중...')
        self.status_label.setStyleSheet('color: #3B82F6; font-size: 11px;')

        self._worker = LoginWorker(self.auth, email, pw, code, is_signup=False)
        self._worker.success.connect(self._on_auth_success)
        self._worker.error.connect(self._on_auth_error)
        self._worker.start()

    def _on_signup_clicked(self):
        email = self.login_email.text().strip()
        pw = self.login_password.text()
        code = self.login_org_code.text().strip()

        if not email or not pw or not code:
            QMessageBox.warning(self, '입력 오류', '이메일, 비밀번호, 기관코드를 모두 입력하세요.')
            return

        if len(pw) < 6:
            QMessageBox.warning(self, '입력 오류', '비밀번호는 6자 이상이어야 합니다.')
            return

        self._set_loading(True)
        self.status_label.setText('📝 회원가입 중...')
        self.status_label.setStyleSheet('color: #3B82F6; font-size: 11px;')

        self._worker = LoginWorker(self.auth, email, pw, code, is_signup=True)
        self._worker.success.connect(self._on_auth_success)
        self._worker.error.connect(self._on_auth_error)
        self._worker.start()

    def _on_register_clicked(self):
        email = self.reg_email.text().strip()
        pw = self.reg_password.text()
        org_name = self.reg_org_name.text().strip()
        org_code = self.reg_org_code.text().strip()

        if not email or not pw or not org_name or not org_code:
            QMessageBox.warning(self, '입력 오류', '모든 항목을 입력하세요.')
            return

        if len(pw) < 6:
            QMessageBox.warning(self, '입력 오류', '비밀번호는 6자 이상이어야 합니다.')
            return

        if not org_code.replace('-', '').replace('_', '').isalnum():
            QMessageBox.warning(self, '입력 오류', '기관코드는 영문, 숫자, 하이픈(-)만 사용할 수 있습니다.')
            return

        self._set_loading(True)
        self.status_label.setText('🏢 기관 등록 중...')
        self.status_label.setStyleSheet('color: #10B981; font-size: 11px;')

        # 먼저 관리자 계정 생성
        try:
            self.auth.sign_up(email, pw)
        except AuthError as e:
            # 이미 가입된 계정이면 로그인 시도
            if e.code == 'EMAIL_EXISTS':
                try:
                    self.auth.sign_in(email, pw)
                except AuthError as e2:
                    if e2.code == 'INVALID_LOGIN_CREDENTIALS':
                        self._on_auth_error('이미 가입된 이메일입니다. 기존 비밀번호를 입력해주세요.')
                    else:
                        self._on_auth_error(str(e2))
                    return
            else:
                self._on_auth_error(str(e))
                return

        self._worker = OrgRegisterWorker(self.auth, org_name, org_code)
        self._worker.success.connect(lambda org_id: self._on_org_registered(org_id, org_code))
        self._worker.error.connect(self._on_auth_error)
        self._worker.start()

    def _on_org_registered(self, org_id: str, org_code: str):
        """기관 등록 성공"""
        import datetime
        self._set_loading(False)

        # 사용자 프로필 생성
        try:
            client = FirestoreClient(self.auth)
            client.set_document(f'users/{self.auth.uid}', {
                'email': self.auth.email,
                'org_id': org_id,
                'display_name': self.auth.email.split('@')[0],
                'role': 'admin',
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception:
            pass

        self.auth.org_id = org_id

        QMessageBox.information(
            self, '기관 등록 완료',
            f'기관 등록이 완료되었습니다!\n\n'
            f'기관명: {self.reg_org_name.text().strip()}\n'
            f'기관코드: {org_code}\n\n'
            f'이 코드를 직원들에게 알려주세요.\n'
            f'직원들은 "직원 로그인" 탭에서 이 코드를 입력하여\n'
            f'회원가입 후 프로그램을 사용할 수 있습니다.'
        )

        self.accept()

    def _on_auth_success(self, uid: str, org_id: str):
        """로그인/가입 성공"""
        self._set_loading(False)
        self.status_label.setText('✅ 인증 성공!')
        self.status_label.setStyleSheet('color: #10B981; font-size: 11px;')
        self.accept()

    def _on_auth_error(self, message: str):
        """인증 실패"""
        self._set_loading(False)
        self.status_label.setText(f'❌ {message}')
        self.status_label.setStyleSheet('color: #EF4444; font-size: 11px;')

    def _set_loading(self, loading: bool):
        """UI 로딩 상태 전환"""
        self.btn_login.setEnabled(not loading)
        self.btn_signup.setEnabled(not loading)
        self.btn_register.setEnabled(not loading)
        self.btn_login_mode.setEnabled(not loading)
        self.btn_register_mode.setEnabled(not loading)

        if loading:
            self.btn_login.setText('처리 중...')
            self.btn_register.setText('처리 중...')
        else:
            self.btn_login.setText('로그인')
            self.btn_register.setText('기관 등록하기')
