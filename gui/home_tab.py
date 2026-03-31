import urllib.parse
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QFont, QCursor, QDesktopServices

from gui.widgets import Colors

class ActionCard(QFrame):
    clicked = Signal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 1px solid {Colors.PRIMARY};
                background-color: #F8FAFC;
            }}
        """)
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont('Pretendard', 14, QFont.Bold))
        lbl_title.setStyleSheet("color: #1E293B; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setWordWrap(True)

        layout.addWidget(lbl_title)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

class HomeTab(QWidget):
    navigate_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(24)
        main_layout.setAlignment(Qt.AlignTop)

        # 1. Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        lbl_title = QLabel("강사관리 자동화 시스템")
        lbl_title.setFont(QFont('Pretendard', 28, QFont.Bold))
        lbl_title.setStyleSheet("color: #0F172A;")

        header_layout.addWidget(lbl_title)
        main_layout.addLayout(header_layout)

        main_layout.addSpacing(16)

        # 2. Quick Actions (Grid)
        grid = QGridLayout()
        grid.setSpacing(20)

        card_instructor = ActionCard("강사 관리")
        card_instructor.clicked.connect(lambda: self.navigate_requested.emit(1))
        
        card_lecture = ActionCard("강의 내역")
        card_lecture.clicked.connect(lambda: self.navigate_requested.emit(2))
        
        card_settlement = ActionCard("월별 정산")
        card_settlement.clicked.connect(lambda: self.navigate_requested.emit(3))
        
        card_help = ActionCard("사용자 매뉴얼")
        card_help.clicked.connect(lambda: self.navigate_requested.emit(5))

        grid.addWidget(card_instructor, 0, 0)
        grid.addWidget(card_lecture, 0, 1)
        grid.addWidget(card_settlement, 1, 0)
        grid.addWidget(card_help, 1, 1)

        main_layout.addLayout(grid)
        main_layout.addSpacing(16)

        # 3. Recent Updates Panel
        updates_frame = QFrame()
        updates_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        updates_layout = QVBoxLayout(updates_frame)
        updates_layout.setContentsMargins(24, 20, 24, 20)
        updates_layout.setSpacing(12)

        lbl_update_title = QLabel("최근 업데이트 가이드")
        lbl_update_title.setFont(QFont('Pretendard', 14, QFont.Bold))
        lbl_update_title.setStyleSheet("color: #1E293B; border: none;")
        updates_layout.addWidget(lbl_update_title)

        from PySide6.QtWidgets import QScrollArea
        
        self.lbl_updates_content = QLabel("인터넷에서 최신 공지사항을 불러오는 중입니다...")
        self.lbl_updates_content.setFont(QFont('Pretendard', 11))
        self.lbl_updates_content.setStyleSheet("color: #475569; border: none; line-height: 1.5;")
        self.lbl_updates_content.setWordWrap(True)
        self.lbl_updates_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { width: 10px; }")
        scroll_area.setWidget(self.lbl_updates_content)

        updates_layout.addWidget(scroll_area)

        main_layout.addWidget(updates_frame)
        main_layout.addStretch()

        # 4. Support Banner
        support_frame = QFrame()
        support_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """)
        support_layout = QHBoxLayout(support_frame)
        support_layout.setContentsMargins(20, 16, 20, 16)
        
        lbl_support = QLabel("시스템 이용 중 문의사항이나 기능 개선 제안이 필요하신가요?")
        lbl_support.setFont(QFont('Pretendard', 11))
        lbl_support.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; border: none; background: transparent;")

        btn_mail = QPushButton("건의사항 이메일 보내기")
        btn_mail.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563EB;
            }}
        """)
        btn_mail.setCursor(Qt.PointingHandCursor)
        btn_mail.clicked.connect(self._open_mail_client)

        support_layout.addWidget(lbl_support)
        support_layout.addStretch()
        support_layout.addWidget(btn_mail)

        main_layout.addWidget(support_frame)

    def update_release_notes(self, notes: str):
        self.lbl_updates_content.setText(notes)

    def _open_mail_client(self):
        subject = urllib.parse.quote("강사관리 자동화 시스템 건의사항 및 문의")
        body = urllib.parse.quote("어떠한 불편사항이 있으셨는지, 혹은 추가적으로 필요한 기능이 무엇인지 상세히 적어주세요.\n\n내용:\n")
        mailto_link = f"mailto:oska@dcsenior.or.kr?subject={subject}&body={body}"
        QDesktopServices.openUrl(QUrl(mailto_link))
