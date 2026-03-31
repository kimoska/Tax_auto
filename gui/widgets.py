"""
AutoTax — 공통 커스텀 위젯
plan.md §5 Design System 기반
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect, QHeaderView, QTableWidgetItem,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem, QStyle
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QColor, QFont, QPen, QPainter


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
        self._layout.addStretch(1)

        self._btn_layout = QHBoxLayout()
        self._btn_layout.setSpacing(4)
        self._btn_layout.setContentsMargins(0, 0, 0, 0)
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
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {hover};
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


class CheckBoxDelegate(QStyledItemDelegate):
    """
    체크박스 커스텀 렌더러 - 검정 테두리 + 빨간색 V 체크마크
    """
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        # 배경 그리기
        self.initStyleOption(option, index)
        painter.save()
        
        # 배경 색상
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor('#E0E7FF'))
        elif index.row() % 2 == 1:
            painter.fillRect(option.rect, QColor('#FAFCFE'))
        else:
            painter.fillRect(option.rect, QColor('white'))

        # 체크박스 사각형 (중앙 배치)
        box_size = 18
        x = option.rect.center().x() - box_size // 2
        y = option.rect.center().y() - box_size // 2
        box_rect = QRect(x, y, box_size, box_size)

        # 테두리 그리기 (검정색)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor('#334155'))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(QColor('white'))
        painter.drawRoundedRect(box_rect, 3, 3)

        # 체크 상태이면 빨간색 V 그리기
        check_state = index.data(Qt.CheckStateRole)
        # PySide6에서 enum이 넘어오거나 int(2)가 넘어올 수 있음
        if check_state in (Qt.Checked, 2, Qt.CheckState.Checked):
            pen = QPen(QColor('#EF4444'))
            pen.setWidth(3)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            # V 모양 그리기
            margin = 4
            p1 = QPoint(x + margin, y + box_size // 2)
            p2 = QPoint(x + box_size // 2 - 1, y + box_size - margin - 1)
            p3 = QPoint(x + box_size - margin, y + margin + 1)
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        """클릭 시 체크 상태 토글"""
        from PySide6.QtCore import QEvent
        if event.type() in (QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick):
            current = index.data(Qt.CheckStateRole)
            new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
            model.setData(index, new_state, Qt.CheckStateRole)
            return True
        return super().editorEvent(event, model, option, index)
