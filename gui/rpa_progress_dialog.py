"""
AutoTax — RPA 진행 상태 다이얼로그
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from gui.widgets import Colors, BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER

from rpa.rpa_runner import RPARunner


class RPAWorker(QThread):
    """RPA 비동기 실행 워커 스레드"""
    progress = Signal(int, int, str)     # step, total, message
    finished = Signal(dict)              # result dict

    def __init__(self, runner: RPARunner):
        super().__init__()
        self.runner = runner
        self.runner.set_progress_callback(self._on_progress)

    def _on_progress(self, step, total, msg):
        self.progress.emit(step, total, msg)

    def run(self):
        import asyncio
        result = asyncio.run(self.runner.run())
        self.finished.emit(result)


class RPAProgressDialog(QDialog):
    """RPA 진행 상태 모달 다이얼로그"""

    def __init__(self, auth_method: str, cert_path: str, cert_password: str,
                 excel_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('홈택스 자동 업로드')
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)
        self.setStyleSheet("QDialog { background: white; }")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._result = None
        self._worker = None
        self._runner = RPARunner(
            auth_method=auth_method,
            cert_path=cert_path,
            cert_password=cert_password,
            excel_path=excel_path,
        )

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 상태 아이콘 + 제목
        self.title_label = QLabel('🤖 홈택스 자동 업로드')
        self.title_label.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};"
        )
        layout.addWidget(self.title_label)

        # 진행 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 8)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                background: #F3F4F6;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: {Colors.ACCENT};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # 현재 단계 레이블
        self.step_label = QLabel('시작 대기 중...')
        self.step_label.setStyleSheet(f"font-size: 14px; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(self.step_label)

        # 로그 영역
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background: #1E1E1E;
                color: #4EC9B0;
                font-family: 'Consolas', 'D2Coding', monospace;
                font-size: 12px;
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        self.log_area.setMaximumHeight(180)
        layout.addWidget(self.log_area)

        # 안내 문구
        warning_frame = QFrame()
        warning_frame.setStyleSheet(f"""
            QFrame {{
                background: #FFFBEB;
                border: 1px solid #FDE68A;
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setContentsMargins(12, 8, 12, 8)
        warn_text = QLabel(
            '⚠️ RPA 실행 중에는 브라우저를 조작하지 마세요.\n'
            '업로드 완료 후 [제출] 버튼은 직접 클릭해야 합니다.'
        )
        warn_text.setStyleSheet("font-size: 12px; color: #92400E; border: none;")
        warn_text.setWordWrap(True)
        warning_layout.addWidget(warn_text)
        layout.addWidget(warning_frame)

        # 하단 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_start = QPushButton('실행')
        self.btn_start.setStyleSheet(BTN_PRIMARY + "QPushButton { padding: 10px 28px; font-size: 14px; }")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start)
        btn_layout.addWidget(self.btn_start)

        self.btn_close = QPushButton('닫기')
        self.btn_close.setStyleSheet(BTN_SECONDARY)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _start(self):
        """RPA 실행 시작"""
        self.btn_start.setEnabled(False)
        self.btn_start.setText('실행 중...')
        self._log('RPA 실행 시작')

        self._worker = RPAWorker(self._runner)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, step: int, total: int, message: str):
        """진행 상태 업데이트"""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(step)
        self.step_label.setText(message)
        self._log(f'[{step}/{total}] {message}')

    def _on_finished(self, result: dict):
        """RPA 완료"""
        self._result = result
        self.btn_start.setEnabled(True)

        if result.get('success'):
            self.title_label.setText('✅ 업로드 완료')
            self.btn_start.setText('재실행')
            self._log('✅ ' + result.get('message', '완료'))
        else:
            self.title_label.setText('❌ 업로드 실패')
            self.btn_start.setText('재시도')
            self._log('❌ ' + result.get('message', '실패'))

    def _log(self, text: str):
        """로그 추가"""
        import datetime
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f'[{ts}] {text}')
