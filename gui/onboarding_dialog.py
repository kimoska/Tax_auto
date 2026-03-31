from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QCheckBox, QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QSettings, QDate
from PySide6.QtGui import QFont, QPixmap
from gui.widgets import Colors, BTN_PRIMARY, BTN_SECONDARY, apply_card_shadow

class OnboardingDialog(QDialog):
    """사용 가이드를 제공하는 팝업 다이얼로그 (오늘 하루 보지 않기 기능 포함)"""
    
    def __init__(self, settings_key: str, title: str, content_html: str, parent=None):
        super().__init__(parent)
        self.settings_key = settings_key
        self.setWindowTitle("사용 가이드")
        self.setFixedSize(500, 500)
        self.setModal(False)
        
        # 오늘 하루 보지 않기 체크 여부 확인
        settings = QSettings("AutoTax", "Onboarding")
        last_hidden_date = settings.value(f"hide_{self.settings_key}")
        if last_hidden_date == QDate.currentDate().toString(Qt.ISODate):
            # 이미 오늘 숨기기로 함 -> 즉시 닫기 (실제 호출부에서 check_should_show를 먼저 부르는게 좋음)
            self.should_show = False
        else:
            self.should_show = True

        self._setup_ui(title, content_html)

    def _setup_ui(self, title_text, content_html):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 메인 카드 프레임
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: white; border-radius: 12px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 20)
        card_layout.setSpacing(20)

        # 타이틀
        lbl_title = QLabel(title_text)
        lbl_title.setFont(QFont("Pretendard", 18, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {Colors.PRIMARY};")
        lbl_title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_title)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Colors.BORDER}; max-height: 1px;")
        card_layout.addWidget(line)

        # 본문 내용 (HTML 지원)
        self.lbl_content = QLabel(content_html)
        self.lbl_content.setFont(QFont("Pretendard", 11))
        self.lbl_content.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; line-height: 1.6;")
        self.lbl_content.setWordWrap(True)
        self.lbl_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        card_layout.addWidget(self.lbl_content)

        card_layout.addStretch()

        # 하단 바 (체크박스 + 닫기 버튼)
        bottom_layout = QHBoxLayout()
        
        self.chk_hide_today = QCheckBox("오늘 하루 더 이상 열지 않기")
        self.chk_hide_today.setFont(QFont("Pretendard", 10))
        self.chk_hide_today.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        
        btn_close = QPushButton("닫기")
        btn_close.setFixedWidth(100)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(BTN_PRIMARY)
        btn_close.clicked.connect(self.on_close)

        bottom_layout.addWidget(self.chk_hide_today)
        bottom_layout.addStretch()
        bottom_layout.addWidget(btn_close)
        
        card_layout.addLayout(bottom_layout)
        layout.addWidget(card)

    def on_close(self):
        if self.chk_hide_today.isChecked():
            settings = QSettings("AutoTax", "Onboarding")
            settings.setValue(f"hide_{self.settings_key}", QDate.currentDate().toString(Qt.ISODate))
        self.accept()

    @staticmethod
    def check_should_show(settings_key: str) -> bool:
        settings = QSettings("AutoTax", "Onboarding")
        last_hidden_date = settings.value(f"hide_{settings_key}")
        return last_hidden_date != QDate.currentDate().toString(Qt.ISODate)
