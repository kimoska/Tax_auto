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
from gui.instructor_tab import InstructorTab
from gui.lecture_tab import LectureTab
from gui.settlement_tab import SettlementTab
from gui.annual_tab import AnnualTab
from gui.settings_tab import SettingsTab
from db.repository import Repository
from core.crypto import CryptoManager

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
        ('instructor', '강사 관리'),
        ('lecture', '강의 내역'),
        ('settlement', '월별 정산 (홈택스)'),
        ('annual', '연간 신고 데이터'),
    ]

    BOTTOM_CONFIG = [
        ('settings', '시스템 설정'),
    ]

    def __init__(self, repo: Repository, crypto: CryptoManager):
        super().__init__()
        self.repo = repo
        self.crypto = crypto

        # 현재 기간 (YYYY-MM)
        now = datetime.datetime.now()
        self.current_year = str(now.year)
        self.current_month = f'{now.month:02d}'

        self.setWindowTitle('AutoTax — 강사료 원천세 자동화')
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

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
        version = QLabel('Enterprise Edition v4.0')
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

        # 하단 구분선 + 설정
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #393939;")
        layout.addWidget(sep)

        for tab_id, tab_name in self.BOTTOM_CONFIG:
            btn = SidebarButton(tab_name)
            idx = len(self.nav_buttons)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        return sidebar

    def _create_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(32, 0, 32, 0)

        self.title_label = QLabel('강사 관리')
        self.title_label.setStyleSheet(
            f"font-size: 18px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; border: none;"
        )
        layout.addWidget(self.title_label)
        layout.addStretch()

        # 기간 선택 콤보
        combo_style = f"""
            QComboBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 13px;
                min-width: 80px;
            }}
        """
        period_label = QLabel('조회기간:')
        period_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; border: none;")
        layout.addWidget(period_label)

        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet(combo_style)
        for y in range(2024, 2031):
            self.year_combo.addItem(f'{y}년', str(y))
        idx_y = self.year_combo.findData(self.current_year)
        if idx_y >= 0:
            self.year_combo.setCurrentIndex(idx_y)
        self.year_combo.currentIndexChanged.connect(self._on_period_changed)
        layout.addWidget(self.year_combo)

        self.month_combo = QComboBox()
        self.month_combo.setStyleSheet(combo_style)
        for m in range(1, 13):
            self.month_combo.addItem(f'{m}월', f'{m:02d}')
        idx_m = self.month_combo.findData(self.current_month)
        if idx_m >= 0:
            self.month_combo.setCurrentIndex(idx_m)
        self.month_combo.currentIndexChanged.connect(self._on_period_changed)
        layout.addWidget(self.month_combo)

        return topbar

    def _on_period_changed(self):
        """기간 변경 시 현재 탭 새로고침"""
        self.current_year = self.year_combo.currentData() or self.current_year
        self.current_month = self.month_combo.currentData() or self.current_month
        period = f"{self.current_year}-{self.current_month}"

        # 기간 인식 탭 업데이트
        self.lecture_tab.set_period(period)
        self.settlement_tab.set_period(period)

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

        left = QLabel('AutoTax v4.0')
        left.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; border: none;")
        layout.addWidget(left)
        layout.addStretch()

        return bar

    def _create_tabs(self):
        """탭 위젯 생성 및 스택에 추가"""
        period = f"{self.current_year}-{self.current_month}"

        # [0] 강사 관리 탭
        self.instructor_tab = InstructorTab(self.repo, self.crypto)
        self.stack.addWidget(self.instructor_tab)

        # [1] 강의 내역 탭
        self.lecture_tab = LectureTab(self.repo)
        self.lecture_tab.set_period(period)
        self.stack.addWidget(self.lecture_tab)

        # [2] 월별 정산 탭
        self.settlement_tab = SettlementTab(self.repo)
        self.settlement_tab.set_period(period)
        self.stack.addWidget(self.settlement_tab)

        # [3] 연간 신고 데이터 탭
        self.annual_tab = AnnualTab(self.repo, self.crypto)
        self.stack.addWidget(self.annual_tab)

        # [4] 시스템 설정 탭
        self.settings_tab = SettingsTab(self.repo, self.crypto)
        self.stack.addWidget(self.settings_tab)

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

        # 타이틀 업데이트
        all_tabs = self.TAB_CONFIG + self.BOTTOM_CONFIG
        if 0 <= index < len(all_tabs):
            self.title_label.setText(all_tabs[index][1])

        # 탭별 데이터 새로고침
        period = f"{self.current_year}-{self.current_month}"
        if index == 0:
            self.instructor_tab.refresh_data()
        elif index == 1:
            self.lecture_tab.set_period(period)
        elif index == 2:
            self.settlement_tab.set_period(period)
