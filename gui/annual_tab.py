"""
AutoTax — [탭4] 연간 신고 데이터 탭
plan.md §10.4 — 월별 선택 합산 + 엑셀 다운로드
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QCheckBox, QHeaderView,
    QAbstractItemView, QMessageBox, QFrame, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from gui.widgets import (
    Panel, Colors, format_money,
    BTN_PRIMARY, BTN_SECONDARY, BTN_SUCCESS
)
from db.repository import Repository
from core.crypto import CryptoManager
from core.excel_generator import generate_annual_excel


class AnnualTab(QWidget):
    """연간 신고 데이터 탭 — 월별 선택 합산"""

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.setObjectName('annualTab')
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ── 연도 + 월 선택 영역 ──
        selector_frame = QFrame()
        selector_frame.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        sel_layout = QVBoxLayout(selector_frame)
        sel_layout.setSpacing(12)

        # 연도
        top_row = QHBoxLayout()
        lbl_year = QLabel('연도 선택:')
        lbl_year.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        top_row.addWidget(lbl_year)

        combo_style = f"""
            QComboBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 14px;
                min-width: 100px;
            }}
        """
        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet(combo_style)
        import datetime
        current_year = datetime.datetime.now().year
        for y in range(2024, 2031):
            self.year_combo.addItem(f'{y}년', str(y))
        idx = self.year_combo.findData(str(current_year))
        if idx >= 0:
            self.year_combo.setCurrentIndex(idx)
        top_row.addWidget(self.year_combo)
        top_row.addStretch()

        btn_query = QPushButton('조회 (선택 월 합산)')
        btn_query.setStyleSheet(BTN_PRIMARY)
        btn_query.setCursor(Qt.PointingHandCursor)
        btn_query.clicked.connect(self._query)
        top_row.addWidget(btn_query)

        btn_excel = QPushButton('연간 엑셀 다운로드')
        btn_excel.setStyleSheet(BTN_SUCCESS)
        btn_excel.setCursor(Qt.PointingHandCursor)
        btn_excel.clicked.connect(self._download_excel)
        top_row.addWidget(btn_excel)

        btn_upload_annual = QPushButton('홈택스 자동 업로드(연말정산용)')
        btn_upload_annual.setStyleSheet(BTN_PRIMARY)
        btn_upload_annual.setCursor(Qt.PointingHandCursor)
        btn_upload_annual.clicked.connect(self._auto_upload_annual)
        top_row.addWidget(btn_upload_annual)

        sel_layout.addLayout(top_row)

        # 월 체크박스 (plan.md §10.4)
        month_row = QHBoxLayout()
        month_row.setSpacing(8)
        lbl_months = QLabel('월 선택:')
        lbl_months.setStyleSheet(f"font-size: 13px; color: {Colors.TEXT_SECONDARY};")
        month_row.addWidget(lbl_months)

        self.month_checks = []
        for m in range(1, 13):
            cb = QCheckBox(f'{m}월')
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 13px;")
            self.month_checks.append(cb)
            month_row.addWidget(cb)

        btn_all = QPushButton('전체')
        btn_all.setStyleSheet(BTN_SECONDARY + "QPushButton { padding: 4px 10px; font-size: 11px; }")
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self.month_checks])
        month_row.addWidget(btn_all)

        btn_none = QPushButton('해제')
        btn_none.setStyleSheet(BTN_SECONDARY + "QPushButton { padding: 4px 10px; font-size: 11px; }")
        btn_none.setCursor(Qt.PointingHandCursor)
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self.month_checks])
        month_row.addWidget(btn_none)

        sel_layout.addLayout(month_row)
        layout.addWidget(selector_frame)

        # ── 결과 테이블 ──
        self.panel = Panel('연간 합산 데이터')

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            '주민번호', '강사명', '업종코드',
            '연간 총지급액', '연간 소득세', '연간 지방소득세', '연간 소득세 총액', '연간 총실지급액'
        ])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(60)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Fixed)            # 번호
        self.table.setColumnWidth(0, 160)
        
        # 비율 기반 초기 너비 (더 세밀하게 조정: 연간 지방소득세, 소득세 총액 너비 확대)
        self._col_ratios = [0, 0.11, 0.10, 0.14, 0.13, 0.16, 0.18, 0.18]
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                border: none; font-size: 13px; gridline-color: {Colors.BORDER};
            }}
            QTableWidget::item {{ padding: 8px 12px; }}
            QHeaderView::section {{
                background: #FAFAFA; color: {Colors.TEXT_SECONDARY};
                font-weight: 500; font-size: 13px; padding: 10px 12px;
                border: none; border-bottom: 2px solid {Colors.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: #E0E7FF;
                color: #1E293B;
                font-weight: bold;
            }}
            QTableWidget::item:alternate {{ background: #FAFCFE; }}
        """)

        self.panel.body_layout.addWidget(self.table)
        layout.addWidget(self.panel)
        self._apply_proportional_widths()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(10, self._apply_proportional_widths)

    def _apply_proportional_widths(self):
        """비율 기반 컬럼 너비 분배"""
        total = self.table.viewport().width()
        fixed = self.table.columnWidth(0)
        avail = total - fixed
        if avail <= 0:
            return
            
        used = 0
        last_interactive = 7
        
        for i, ratio in enumerate(self._col_ratios):
            if ratio > 0:
                w = int(avail * ratio)
                self.table.setColumnWidth(i, w)
                used += w
                
        if avail > used:
            self.table.setColumnWidth(last_interactive, self.table.columnWidth(last_interactive) + (avail - used))

    def _get_selected_months(self) -> list[str]:
        """선택된 월 리스트 반환"""
        months = []
        for i, cb in enumerate(self.month_checks):
            if cb.isChecked():
                months.append(f'{i+1:02d}')
        return months

    def refresh_data(self):
        """외부에서 호출 가능한 데이터 새로고침"""
        self._query()

    def _query(self):
        """선택 월 합산 조회"""
        year = self.year_combo.currentData()
        months = self._get_selected_months()

        if not months:
            QMessageBox.warning(self, '월 선택', '조회할 월을 1개 이상 선택하세요.')
            return

        data = self.repo.get_annual_summary(year, months)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(data) + 1 if data else 0)

        sum_total = 0
        sum_income = 0
        sum_local = 0
        sum_total_tax = 0
        sum_net = 0

        for row, d in enumerate(data):
            # 주민번호 마스킹 (평문 저장된 값에서 마스킹 처리)
            rid = d.get('resident_id', '')
            masked = rid[:6] + '-*******' if len(rid) >= 6 else '***'

            rid_item = QTableWidgetItem(masked)
            rid_item.setForeground(Qt.black)
            self.table.setItem(row, 0, rid_item)

            name_item = QTableWidgetItem(d.get('name', ''))
            name_item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
            name_item.setForeground(Qt.black)
            self.table.setItem(row, 1, name_item)

            ind_item = QTableWidgetItem(d.get('industry_code', ''))
            ind_item.setForeground(Qt.black)
            self.table.setItem(row, 2, ind_item)

            total = d.get('annual_total', 0) or 0
            income_tax = d.get('annual_income_tax', 0) or 0
            local_tax = d.get('annual_local_tax', 0) or 0
            total_tax = income_tax + local_tax
            net = d.get('annual_net_payment', 0) or 0

            sum_total += total
            sum_income += income_tax
            sum_local += local_tax
            sum_total_tax += total_tax
            sum_net += net

            vals = [total, income_tax, local_tax, total_tax, net]

            for i, val in enumerate(vals):
                col = i + 3
                item = QTableWidgetItem(format_money(val))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                if col == 3:
                    item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
                elif col == 6:  # 연간 소득세 총액
                    item.setForeground(QColor(Colors.ERROR))
                    item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
                elif col == 7:  # 연간 총실지급액
                    item.setForeground(QColor(Colors.ERROR))
                    item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
                
                self.table.setItem(row, col, item)

        if data:
            last_row = len(data)
            
            sum_label = QTableWidgetItem("합계")
            sum_label.setFont(QFont('Pretendard', 10, QFont.Bold))
            sum_label.setTextAlignment(Qt.AlignCenter)
            sum_label.setBackground(QColor('#F8FAFC'))
            self.table.setItem(last_row, 0, sum_label)
            
            for c in [1, 2]:
                empty_item = QTableWidgetItem("")
                empty_item.setBackground(QColor('#F8FAFC'))
                self.table.setItem(last_row, c, empty_item)

            sum_vals = [sum_total, sum_income, sum_local, sum_total_tax, sum_net]
            for i, val in enumerate(sum_vals):
                col = i + 3
                item = QTableWidgetItem(format_money(val))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item.setBackground(QColor('#F8FAFC'))
                item.setFont(QFont('Pretendard', 10, QFont.Bold))
                
                if col in [6, 7]:
                    item.setForeground(QColor(Colors.ERROR))
                else:
                    item.setForeground(Qt.black)
                    
                self.table.setItem(last_row, col, item)

        self.table.setSortingEnabled(True)

    def _download_excel(self):
        """연간 엑셀 다운로드"""
        year = self.year_combo.currentData()
        months = self._get_selected_months()

        if not months:
            QMessageBox.warning(self, '월 선택', '다운로드할 월을 선택하세요.')
            return

        # 저장 경로 선택
        default_name = f'연간거주자사업소득지급명세서_{year}.xlsx'
        filepath, _ = QFileDialog.getSaveFileName(
            self, '엑셀 저장', default_name,
            'Excel 파일 (*.xlsx);;모든 파일 (*.*)'
        )
        if not filepath:
            return

        try:
            generate_annual_excel(self.repo, year, months, filepath)
            QMessageBox.information(self, '다운로드 완료', f'파일이 저장되었습니다:\n{filepath}')
        except ValueError as e:
            QMessageBox.warning(self, '오류', str(e))
        except Exception as e:
            QMessageBox.critical(self, '오류', f'엑셀 생성 실패:\n{str(e)}')

    def _auto_upload_annual(self):
        """홈택스 자동 업로드 (연말정산용) - 추후 구현 예정"""
        QMessageBox.information(
            self, '안내',
            '홈택스 자동 업로드(연말정산용) 기능은 추후 업데이트에서 구현될 예정입니다.'
        )
