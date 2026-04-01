"""
AutoTax — 메인 윈도우 (plan.md §5.4)
FluentWindow 스타일의 사이드바 네비게이션 + 탭 전환
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QPushButton, QFrame, QApplication, QSizePolicy,
    QComboBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from gui.widgets import Colors
from gui.home_tab import HomeTab
from gui.instructor_tab import InstructorTab
from gui.lecture_tab import LectureTab
from gui.settlement_tab import SettlementTab
from gui.annual_tab import AnnualTab
from gui.help_tab import HelpTab
from db.cloud_repository import CloudRepository
from core.crypto import CryptoManager
from core.updater import UpdateChecker

import datetime


class SidebarButton(QPushButton):
    """사이드바 네비게이션 버튼"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._update_style(False)

    def _update_style(self, active: bool):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background: #262626;
                    color: white;
                    border: none;
                    border-left: 4px solid #2563EB;
                    text-align: left;
                    padding: 0 20px;
                    font-size: 14px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #C6C6C6;
                    border: none;
                    border-left: 4px solid transparent;
                    text-align: left;
                    padding: 0 20px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #393939;
                    color: white;
                }
            """)

    def set_active(self, active: bool):
        self.setChecked(active)
        self._update_style(active)


class AutoTaxWindow(QMainWindow):
    """AutoTax 메인 윈도우"""

    TAB_CONFIG = [
        ('home', '홈 화면'),
        ('instructor', '강사 관리'),
        ('lecture', '강의 내역'),
        ('settlement', '월별 정산'),
        ('annual', '연간 신고데이터'),
        ('help', '도움말 매뉴얼'),
    ]

    BOTTOM_CONFIG = []

    def __init__(self, repo: CloudRepository, crypto: CryptoManager):
        super().__init__()
        self.repo = repo
        self.crypto = crypto

        # 현재 기간 (YYYY-MM)
        now = datetime.datetime.now()
        self.current_year = str(now.year)
        self.current_month = f'{now.month:02d}'

        self.setWindowTitle('AutoTax — 강사료 원천세 자동화')
        self.resize(1600, 950)
        self.setMinimumSize(1200, 800)

        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 사이드바 ──
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # ── 메인 콘텐츠 영역 ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 상단 바
        topbar = self._create_topbar()
        right_layout.addWidget(topbar)

        # 콘텐츠 스택
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {Colors.SURFACE};")
        right_layout.addWidget(self.stack)

        # 하단 상태바
        statusbar = self._create_statusbar()
        right_layout.addWidget(statusbar)

        main_layout.addWidget(right_panel)

        # ── 탭 생성 ──
        self._create_tabs()
        self._switch_tab(0)

        # ── 업데이트 확인 ──
        self._check_for_updates()
        
        # ── 전역 단축키 (F5 새로고침) ──
        from PySide6.QtGui import QShortcut, QKeySequence
        self.shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        self.shortcut_refresh.activated.connect(self._refresh_current_tab)

    def _refresh_current_tab(self):
        """현재 활성화된 탭에 맞춰 새로고침 명령 하달"""
        current_widget = self.stack.currentWidget()
        if hasattr(self, 'instructor_tab') and current_widget == self.instructor_tab:
            self.instructor_tab.refresh_data()
        elif hasattr(self, 'lecture_tab') and current_widget == self.lecture_tab:
            self.lecture_tab._on_period_changed()
        elif hasattr(self, 'settlement_tab') and current_widget == self.settlement_tab:
            self.settlement_tab._on_period_changed()
        elif hasattr(self, 'annual_tab') and current_widget == self.annual_tab:
            self.annual_tab._query()
            
        # ── 온보딩 가이드 ──
        from gui.onboarding_dialog import OnboardingDialog
        if OnboardingDialog.check_should_show("feature_guide"):
            content = """
            우선 강사 정보를 등록해보세요!<br><br>
            <b>1. 엑셀 일괄 등록</b><br>
            강사관리 탭에서 "엑셀 일괄 등록" 버튼을 누르고 
            압축을 해제한 폴더에서 "강사 등록 양식" 엑셀 파일을 찾아 업로드합니다.<br><br>
            <b>2. 강의 내역 등록</b><br>
            강의 내역 탭에서 "강의 추가"버튼을 눌러 강사별 강의를 등록하고 강의횟수를 작성하세요.<br><br>
            <b>3. 월별 정산 계산</b><br>
            강의를 등록한 "월"을 선택하고 "정산 재계산" 버튼을 눌러 실제 지급액을 확인해 보세요.<br><br>

            <small style='color: #64748B;'>* 샘플 엑셀파일에 등록된 정보는 가상의 정보입니다..</small>
            """
            self.guide = OnboardingDialog("feature_guide", "프로그램 테스트 방법", content, self)
            self.guide.show()

    def _check_for_updates(self):
        self.updater = UpdateChecker(current_version="v1.1.1")
        self.updater.update_available.connect(self._on_update_available)
        self.updater.error_occurred.connect(self._on_update_error)
        self.updater.start()

    def _on_update_available(self, version, desc, url):
        notes = f"<b>[{version}] 업데이트 안내</b><br><br>{desc}"
        notes = notes.replace('\n', '<br>')
        self.home_tab.update_release_notes(notes)
        
        if url:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, '업데이트 알림',
                f"새로운 버전({version})이 출시되었습니다.\n\n"
                f"지금 바로 업데이트하시겠습니까?\n(예를 누르시면 자동으로 다운로드 후 재시작됩니다)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._start_update(url)

    def _start_update(self, url):
        from PySide6.QtWidgets import QProgressDialog, QMessageBox
        from core.updater import UpdateDownloader, apply_update_and_restart
        
        self.dl_progress = QProgressDialog("업데이트 다운로드 중...", "취소", 0, 100, self)
        self.dl_progress.setWindowTitle("업데이트")
        self.dl_progress.setWindowModality(Qt.WindowModal)
        self.dl_progress.setAutoClose(True)
        self.dl_progress.show()

        self.downloader = UpdateDownloader(url)
        self.downloader.progress.connect(self.dl_progress.setValue)
        
        def on_finished(extracted_dir):
            self.dl_progress.close()
            apply_update_and_restart(extracted_dir)
            
        def on_error(err):
            self.dl_progress.close()
            QMessageBox.critical(self, "오류", f"업데이트 실패:\n{err}")

        self.downloader.finished.connect(on_finished)
        self.downloader.error.connect(on_error)
        
        # 다운로드 취소 시 쓰레드 중단 로직 (옵션)
        self.dl_progress.canceled.connect(self.downloader.terminate)
        
        self.downloader.start()

    def _on_update_error(self, err_msg):
        # 업데이트 실패 시에도 기존 문구가 남지 않도록 안내
        self.home_tab.update_release_notes(
            f"공지사항을 불러오는 중 오류가 발생했습니다.<br><br><small style='color: #94A3B8;'>{err_msg}</small>"
        )

    def _create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("QFrame { background: #161616; }")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 로고
        header = QWidget()
        header.setStyleSheet("background: transparent; border-bottom: 1px solid #393939;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 16)

        logo = QLabel('AutoTax')
        logo.setStyleSheet("color: white; font-size: 18px; font-weight: 700; border: none;")
        version = QLabel('Enterprise Edition v1.1.1')
        version.setStyleSheet("color: #8D8D8D; font-size: 11px; border: none;")

        header_layout.addWidget(logo)
        header_layout.addWidget(version)
        layout.addWidget(header)
        layout.addSpacing(12)

        # 상단 네비게이션 버튼
        self.nav_buttons = []
        for tab_id, tab_name in self.TAB_CONFIG:
            btn = SidebarButton(tab_name)
            idx = len(self.nav_buttons)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        return sidebar

    def _create_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setFixedHeight(80) # 조금 더 높게
        topbar.setStyleSheet(f"background: white; border-bottom: 1px solid {Colors.BORDER};")
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(24, 0, 24, 0)

        # 타이틀 레이블 (현재 탭 이름 표시용)
        self.title_label = QLabel('홈 화면')
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; border: none;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        return topbar

    def _on_period_changed(self):
        """기간 변경 시 (만약 전역적으로 필요하다면 사용)"""
        pass

    def _create_statusbar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(32)
        bar.setStyleSheet(f"""
            QFrame {{
                background: #FAFAFA;
                border-top: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        left = QLabel('AutoTax v1.1.0')
        left.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; border: none;")
        layout.addWidget(left)
        layout.addStretch()

        return bar

    def _create_tabs(self):
        """탭 위젯 생성 및 스택에 추가"""
        period = f"{self.current_year}-{self.current_month}"

        # [0] 홈 화면 탭
        self.home_tab = HomeTab()
        self.home_tab.navigate_requested.connect(self._switch_tab)
        self.stack.addWidget(self.home_tab)

        # [1] 강사 관리 탭
        self.instructor_tab = InstructorTab(self.repo, self.crypto)
        self.stack.addWidget(self.instructor_tab)

        # [2] 강의 내역 탭
        self.lecture_tab = LectureTab(self.repo)
        self.lecture_tab.set_period(period)
        self.stack.addWidget(self.lecture_tab)

        # [3] 월별 정산 탭
        self.settlement_tab = SettlementTab(self.repo)
        self.settlement_tab.set_period(period)
        self.stack.addWidget(self.settlement_tab)

        # [4] 연간 신고 데이터 탭
        self.annual_tab = AnnualTab(self.repo)
        self.stack.addWidget(self.annual_tab)

        # 강의 내역 변경 시 정산/연간 탭 자동 새로고침
        self.lecture_tab.data_changed.connect(self.settlement_tab.refresh_data)
        self.lecture_tab.data_changed.connect(self.annual_tab.refresh_data)

        # [5] 도움말 매뉴얼 탭
        self.help_tab = HelpTab()
        self.stack.addWidget(self.help_tab)

    def _create_placeholder(self, name: str) -> QWidget:
        """미구현 탭 플레이스홀더"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel(f'🚧  {name}\n\n이 탭은 다음 Phase에서 구현됩니다.')
        label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 16px; text-align: center;"
        )
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return w

    def _switch_tab(self, index: int):
        """탭 전환"""
        self.stack.setCurrentIndex(index)

        # 네비게이션 버튼 활성 상태 업데이트
        for i, btn in enumerate(self.nav_buttons):
            btn.set_active(i == index)

        all_tabs = self.TAB_CONFIG + self.BOTTOM_CONFIG
        if 0 <= index < len(all_tabs):
            tab_id, tab_name = all_tabs[index]
            self.title_label.setText(tab_name)

        # 탭별 데이터 새로고침 (기간은 사용자가 선택한 값 유지)
        if index == 1:
            self.instructor_tab.refresh_data()
        elif index == 2:
            self.lecture_tab.refresh_data()
        elif index == 3:
            self.settlement_tab.refresh_data()
