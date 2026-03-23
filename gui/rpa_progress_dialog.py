"""
AutoTax — RPA 진행 상태 다이얼로그
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QTextEdit,
    QMessageBox
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

    def __init__(self, excel_path: str, auth_method: str = 'certificate', cert_keyword: str = '', cert_drive: str = 'C', cert_password: str = '', settlements: list = None, parent=None):
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
            cert_keyword=cert_keyword,
            cert_drive=cert_drive,
            cert_password=cert_password,
            excel_path=excel_path,
            settlements=settlements or [],
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
        self.progress_bar.setRange(0, 10)
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
        """RPA 완료 — 상세 요약 알림 + 제출 안내"""
        self._result = result
        self.btn_start.setEnabled(True)

        if result.get('success'):
            self.title_label.setText('✅ 동기화 완료')
            self.btn_start.setText('재실행')
            self._log('✅ ' + result.get('message', '완료'))

            # ── 1단계: 상세 요약 알림 ──
            sync_details = result.get('sync_details', {})
            details_list = sync_details.get('details', [])
            updated = sync_details.get('updated', 0)
            deleted = sync_details.get('deleted', 0)
            added = sync_details.get('added', 0)

            summary_lines = [
                '📊 홈택스 동기화 결과\n',
                f'  ✏️ 수정: {updated}건',
                f'  🗑️ 삭제: {deleted}건',
                f'  ➕ 신규: {added}건',
                '\n────────────────────────────\n',
            ]
            if details_list:
                summary_lines.append('📋 상세 내역:\n')
                for detail in details_list:
                    summary_lines.append(f'  {detail}')
            else:
                summary_lines.append('(변경 사항 없음)')

            summary_text = '\n'.join(summary_lines)

            summary_box = QMessageBox(self)
            summary_box.setWindowTitle('📊 동기화 결과 보고')
            summary_box.setText(summary_text)
            summary_box.setIcon(QMessageBox.Information)
            summary_box.setStandardButtons(QMessageBox.Ok)
            summary_box.button(QMessageBox.Ok).setText('완료')
            summary_box.exec()

            # ── 2단계: 제출 안내 알림 ──
            guide_text = (
                '✅ 모든 데이터가 홈택스에 반영되었습니다.\n\n'
                '이제 홈택스 브라우저에서 다음을 확인해주세요:\n\n'
                '1️⃣  상세내역 목록 및 총 지급액이 올바른지 확인\n'
                '2️⃣  확인이 완료되면 [제출하러 가기] 버튼 클릭\n'
                '3️⃣  제출 후 접수증을 다운로드하여 보관\n\n'
                '⚠️  브라우저를 닫지 마세요!\n'
                '     제출이 완료될 때까지 열어두셔야 합니다.'
            )
            guide_box = QMessageBox(self)
            guide_box.setWindowTitle('📌 제출 안내')
            guide_box.setText(guide_text)
            guide_box.setIcon(QMessageBox.Warning)
            guide_box.setStandardButtons(QMessageBox.Ok)
            guide_box.button(QMessageBox.Ok).setText('확인')
            guide_box.exec()

        else:
            self.title_label.setText('❌ 업로드 실패')
            self.btn_start.setText('재시도')
            self._log('❌ ' + result.get('message', '실패'))

    def _log(self, text: str):
        """로그 추가"""
        import datetime
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f'[{ts}] {text}')
