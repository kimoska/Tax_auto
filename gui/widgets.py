"""
AutoTax — 공통 커스텀 위젯
plan.md §5 Design System 기반
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect, QHeaderView, QTableWidgetItem,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont


# ─────────────────────────────────────────────
# 색상 팔레트 (plan.md §5.1)
# ─────────────────────────────────────────────
class Colors:
    PRIMARY = '#0F1B2D'
    PRIMARY_LIGHT = '#1B3A5C'
    SURFACE = '#F8F9FB'
    CARD = '#FFFFFF'
    ACCENT = '#2563EB'
    ACCENT_HOVER = '#1D4ED8'
    SUCCESS = '#10B981'
    WARNING = '#F59E0B'
    ERROR = '#EF4444'
    TEXT_PRIMARY = '#111827'
    TEXT_SECONDARY = '#6B7280'
    BORDER = '#E5E7EB'


# ─────────────────────────────────────────────
# KPI 카드 위젯
# ─────────────────────────────────────────────
class KPICard(QFrame):
    """대시보드용 KPI 지표 카드"""

    def __init__(self, label: str, value: str = '0', color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName('kpiCard')
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background: white;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                border-left: 4px solid {Colors.PRIMARY};
                padding: 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        self.label_widget = QLabel(label)
        self.label_widget.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")

        self.value_widget = QLabel(value)
        value_color = color or Colors.TEXT_PRIMARY
        self.value_widget.setStyleSheet(
            f"color: {value_color}; font-size: 24px; font-weight: 700;"
        )

        layout.addWidget(self.label_widget)
        layout.addWidget(self.value_widget)

        # 그림자 효과
        apply_card_shadow(self)

    def set_value(self, value: str):
        self.value_widget.setText(value)


# ─────────────────────────────────────────────
# 패널 (CardWidget 대용)
# ─────────────────────────────────────────────
class Panel(QFrame):
    """테이블 등을 감싸는 카드 패널"""

    def __init__(self, title: str = '', parent=None):
        super().__init__(parent)
        self.setObjectName('panel')
        self.setStyleSheet(f"""
            QFrame#panel {{
                background: white;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        if title:
            self._header = PanelHeader(title)
            self._layout.addWidget(self._header)
        else:
            self._header = None

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._body)

        apply_card_shadow(self)

    @property
    def header(self):
        return self._header

    @property
    def body_layout(self):
        return self._body_layout

    def add_header_widget(self, widget):
        """헤더 우측에 위젯(버튼 등) 추가"""
        if self._header:
            self._header.add_widget(widget)


class PanelHeader(QFrame):
    """패널 상단 헤더"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                border-bottom: 1px solid {Colors.BORDER};
                padding: 12px 20px;
            }}
        """)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(20, 12, 20, 12)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; border: none;"
        )
        self._layout.addWidget(self.title_label)
        self._layout.addStretch()

        self._btn_layout = QHBoxLayout()
        self._btn_layout.setSpacing(8)
        self._layout.addLayout(self._btn_layout)

    def add_widget(self, widget):
        self._btn_layout.addWidget(widget)


# ─────────────────────────────────────────────
# 상태 뱃지
# ─────────────────────────────────────────────
class StatusBadge(QLabel):
    """색상 상태 뱃지 (plan.md §5.3.4)"""

    STYLES = {
        '입력완료': ('background: #DBEAFE; color: #1E40AF;', ),
        '정산완료': ('background: #D1FAE5; color: #065F46;', ),
        '제출완료': ('background: #E0E7FF; color: #3730A3;', ),
        '수동수정': ('background: #FEF3C7; color: #92400E;', ),
        '등록됨': ('background: #D1FAE5; color: #065F46;', ),
    }

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        style = self.STYLES.get(text, ('background: #E5E7EB; color: #374151;',))[0]
        self.setStyleSheet(
            f"{style} border-radius: 4px; padding: 2px 10px; "
            f"font-size: 12px; font-weight: 600;"
        )
        self.setAlignment(Qt.AlignCenter)


# ─────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────
def apply_card_shadow(widget):
    """위젯에 부드러운 Drop Shadow 적용 (plan.md §5.3.1)"""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setXOffset(0)
    shadow.setYOffset(4)
    shadow.setColor(QColor(0, 0, 0, 25))
    widget.setGraphicsEffect(shadow)


def format_money(value: int) -> str:
    """숫자 → '1,234,567' 포맷"""
    if value is None:
        return '0'
    return f'{value:,}'


def make_button_style(bg: str, text: str = 'white', hover_bg: str = None) -> str:
    """QPushButton 스타일시트 생성"""
    hover = hover_bg or bg
    return f"""
        QPushButton {{
            background-color: {bg};
            color: {text};
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {hover};
            padding-top: 9px;
        }}
        QPushButton:disabled {{
            background-color: #94A3B8;
            color: #CBD5E1;
        }}
    """


# 버튼 스타일 프리셋
BTN_PRIMARY = make_button_style(Colors.ACCENT, hover_bg=Colors.ACCENT_HOVER)
BTN_SECONDARY = make_button_style(
    '#FFFFFF', Colors.TEXT_PRIMARY,
    '#F3F4F6'
) + f"QPushButton {{ border: 1px solid {Colors.BORDER}; }}"
BTN_DANGER = make_button_style(Colors.ERROR, hover_bg='#DC2626')
BTN_SUCCESS = make_button_style(Colors.SUCCESS, hover_bg='#059669')
BTN_GHOST_DANGER = f"""
    QPushButton {{
        background: transparent;
        color: {Colors.ERROR};
        border: none;
        padding: 4px 10px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background: #FEF2F2;
        border-radius: 4px;
    }}
"""
