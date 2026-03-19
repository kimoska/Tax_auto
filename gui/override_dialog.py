"""
AutoTax — Manual Override 다이얼로그
plan.md §4.2 수동 수정 유즈케이스 구현
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt

from gui.widgets import Colors, format_money, BTN_PRIMARY, BTN_SECONDARY
from db.repository import Repository


class OverrideDialog(QDialog):
    """세액 수동 수정 모달"""

    def __init__(self, repo: Repository, settlement_id: int, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.settlement_id = settlement_id

        self.setWindowTitle('세액 수동 수정')
        self.setMinimumWidth(480)
        self.setStyleSheet("QDialog { background: white; }")

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 0)
        layout.setSpacing(16)

        input_style = f"""
            QLineEdit {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
        """
        label_style = f"font-size: 13px; font-weight: 500; color: {Colors.TEXT_PRIMARY};"
        sub_style = f"font-size: 12px; color: {Colors.TEXT_SECONDARY};"

        # 원래 계산 값 표시
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-radius: 8px;
                padding: 12px 16px;
            }}
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        self.info_label = QLabel('자동 계산 값')
        self.info_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #0369A1; border: none;")
        info_layout.addWidget(self.info_label)

        self.calc_info = QLabel('')
        self.calc_info.setStyleSheet("font-size: 13px; color: #0369A1; border: none;")
        info_layout.addWidget(self.calc_info)

        layout.addWidget(info_frame)

        # 수동 소득세
        lbl1 = QLabel('수동 소득세')
        lbl1.setStyleSheet(label_style)
        layout.addWidget(lbl1)
        self.income_tax_input = QLineEdit()
        self.income_tax_input.setStyleSheet(input_style)
        self.income_tax_input.setPlaceholderText('변경할 소득세')
        self.income_tax_input.textChanged.connect(self._recalc_net)
        layout.addWidget(self.income_tax_input)

        # 수동 지방소득세
        lbl2 = QLabel('수동 지방소득세')
        lbl2.setStyleSheet(label_style)
        layout.addWidget(lbl2)
        self.local_tax_input = QLineEdit()
        self.local_tax_input.setStyleSheet(input_style)
        self.local_tax_input.setPlaceholderText('변경할 지방소득세')
        self.local_tax_input.textChanged.connect(self._recalc_net)
        layout.addWidget(self.local_tax_input)

        # 예상 실지급액
        self.net_label = QLabel('예상 실지급액: -')
        self.net_label.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {Colors.ACCENT};")
        layout.addWidget(self.net_label)

        # 수정 사유
        lbl3 = QLabel('수정 사유 *')
        lbl3.setStyleSheet(label_style)
        layout.addWidget(lbl3)
        self.reason_input = QLineEdit()
        self.reason_input.setStyleSheet(input_style)
        self.reason_input.setPlaceholderText('수정 사유를 입력하세요')
        layout.addWidget(self.reason_input)

        # 하단 버튼
        footer = QFrame()
        footer.setStyleSheet(f"QFrame {{ background: #FAFAFA; border-top: 1px solid {Colors.BORDER}; }}")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)
        footer_layout.addStretch()

        btn_cancel = QPushButton('취소')
        btn_cancel.setStyleSheet(BTN_SECONDARY)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton('수동 수정 적용')
        btn_save.setStyleSheet(BTN_PRIMARY)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save)

        footer_layout.addWidget(btn_cancel)
        footer_layout.addWidget(btn_save)
        layout.addWidget(footer)

    def _load_data(self):
        self.settlement = self.repo.get_settlement(self.settlement_id)
        if not self.settlement:
            return

        s = self.settlement
        self.calc_info.setText(
            f"총지급액: {format_money(s['total_payment'])}원  |  "
            f"자동 소득세: {format_money(s['calc_income_tax'])}원  |  "
            f"자동 지방소득세: {format_money(s['calc_local_tax'])}원"
        )

        # 현재 final 값으로 초기화
        self.income_tax_input.setText(str(s['final_income_tax']))
        self.local_tax_input.setText(str(s['final_local_tax']))
        self._recalc_net()

    def _recalc_net(self):
        if not hasattr(self, 'settlement') or not self.settlement:
            return
        try:
            income = int(self.income_tax_input.text().strip() or '0')
            local = int(self.local_tax_input.text().strip() or '0')
            net = self.settlement['total_payment'] - income - local
            self.net_label.setText(f'예상 실지급액: {format_money(net)}원')
        except ValueError:
            self.net_label.setText('예상 실지급액: -')

    def _save(self):
        reason = self.reason_input.text().strip()
        if not reason:
            QMessageBox.warning(self, '입력 오류', '수정 사유를 입력하세요.')
            return

        try:
            income = int(self.income_tax_input.text().strip())
            local = int(self.local_tax_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, '입력 오류', '세액을 숫자로 입력하세요.')
            return

        self.repo.apply_override(
            self.settlement_id, income, local, reason
        )
        self.accept()
