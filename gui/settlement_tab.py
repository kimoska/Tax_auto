"""
AutoTax — [탭3] 월별 정산 탭 (홈택스 제출용)
plan.md §5.4 + prototype.html 정산 로직 이식
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QDialog,
    QHeaderView, QAbstractItemView, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from gui.widgets import (
    KPICard, Panel, StatusBadge, Colors, format_money,
    BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER, BTN_SUCCESS, BTN_GHOST_DANGER
)
from gui.override_dialog import OverrideDialog
from db.repository import Repository
from core.aggregator import aggregate_lectures_to_settlements


class SettlementTab(QWidget):
    """월별 정산 탭 — 강사별 합산 + Override + 홈택스 액셀 생성"""

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.current_period = '2026-03'
        self.setObjectName('settlementTab')
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ── KPI 요약 ──
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)
        self.kpi_instructors = KPICard('정산 강사', '0')
        self.kpi_total = KPICard('총 지급액', '0원', Colors.ACCENT)
        self.kpi_tax = KPICard('총 세액', '0원', Colors.ERROR)
        self.kpi_net = KPICard('총 실지급액', '0원', Colors.SUCCESS)
        kpi_layout.addWidget(self.kpi_instructors)
        kpi_layout.addWidget(self.kpi_total)
        kpi_layout.addWidget(self.kpi_tax)
        kpi_layout.addWidget(self.kpi_net)
        layout.addLayout(kpi_layout)

        # ── 정산 테이블 패널 ──
        self.panel = Panel('간이지급명세서 미리보기')

        # 헤더 버튼
        btn_recalc = QPushButton('정산 재계산')
        btn_recalc.setStyleSheet(BTN_SECONDARY)
        btn_recalc.setCursor(Qt.PointingHandCursor)
        btn_recalc.clicked.connect(self.recalculate_settlements)
        self.panel.add_header_widget(btn_recalc)

        btn_excel = QPushButton('홈택스 엑셀 다운로드')
        btn_excel.setStyleSheet(BTN_SUCCESS)
        btn_excel.setCursor(Qt.PointingHandCursor)
        btn_excel.clicked.connect(self._download_hometax_excel)
        self.panel.add_header_widget(btn_excel)

        btn_upload = QPushButton('홈택스 자동 업로드')
        btn_upload.setStyleSheet(BTN_PRIMARY)
        btn_upload.setCursor(Qt.PointingHandCursor)
        btn_upload.clicked.connect(self._auto_upload)
        self.panel.add_header_widget(btn_upload)

        # 테이블 (홈택스 간이지급명세서 11컬럼 + 관리)
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            '번호', '귀속연도', '귀속월', '업종코드', '소득자성명',
            '주민등록번호', '내외국인', '지급액', '세율(%)',
            '소득세', '지방소득세', '상태', '관리'
        ])
        for i in range(self.table.columnCount()):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                border: none; font-size: 12px; gridline-color: {Colors.BORDER};
            }}
            QTableWidget::item {{ padding: 6px 10px; }}
            QHeaderView::section {{
                background: #FAFAFA; color: {Colors.TEXT_SECONDARY};
                font-weight: 500; font-size: 12px; padding: 8px 10px;
                border: none; border-bottom: 2px solid {Colors.BORDER};
            }}
            QTableWidget::item:alternate {{ background: #FAFCFE; }}
        """)

        self.panel.body_layout.addWidget(self.table)
        layout.addWidget(self.panel)

    def set_period(self, period: str):
        self.current_period = period
        self.refresh_data()

    def refresh_data(self):
        """DB의 settlements를 읽어 테이블 갱신"""
        settlements = self.repo.get_settlements_by_period(self.current_period)
        self.table.setRowCount(len(settlements))

        sum_total = sum_tax = sum_local = sum_net = 0
        year, month = self.current_period.split('-')

        for row, s in enumerate(settlements):
            sum_total += s['total_payment']
            sum_tax += s['final_income_tax']
            sum_local += s['final_local_tax']
            sum_net += s['final_net_payment']

            # 번호
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

            # 귀속연도
            self.table.setItem(row, 1, QTableWidgetItem(year))

            # 귀속월
            self.table.setItem(row, 2, QTableWidgetItem(month))

            # 업종코드
            self.table.setItem(row, 3, QTableWidgetItem(s['industry_code']))

            # 소득자성명
            name_item = QTableWidgetItem(s.get('name', ''))
            name_item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
            self.table.setItem(row, 4, name_item)

            # 주민등록번호 (마스킹)
            rid = s.get('resident_id', '')
            masked = rid[:6] + '-*******' if len(rid) >= 6 else '***'
            self.table.setItem(row, 5, QTableWidgetItem(masked))

            # 내외국인
            self.table.setItem(row, 6, QTableWidgetItem(s['is_foreigner']))

            # 지급액
            pay_item = QTableWidgetItem(format_money(s['total_payment']))
            pay_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 7, pay_item)

            # 세율
            self.table.setItem(row, 8, QTableWidgetItem(str(s['tax_rate'])))

            # 소득세
            tax_item = QTableWidgetItem(format_money(s['final_income_tax']))
            tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tax_item.setForeground(QColor(Colors.ERROR))
            self.table.setItem(row, 9, tax_item)

            # 지방소득세
            local_item = QTableWidgetItem(format_money(s['final_local_tax']))
            local_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            local_item.setForeground(QColor(Colors.ERROR))
            self.table.setItem(row, 10, local_item)

            # 상태 뱃지
            if s.get('ovr_income_tax') is not None:
                badge = StatusBadge('수동수정')
            elif s.get('is_submitted'):
                badge = StatusBadge('제출완료')
            else:
                badge = StatusBadge('정산완료')
            self.table.setCellWidget(row, 11, badge)

            # 관리 버튼
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            btn_ovr = QPushButton('수정')
            btn_ovr.setStyleSheet(BTN_SECONDARY + "QPushButton { padding: 3px 10px; font-size: 11px; }")
            btn_ovr.setCursor(Qt.PointingHandCursor)
            btn_ovr.clicked.connect(lambda _, sid=s['id']: self._open_override(sid))
            btn_layout.addWidget(btn_ovr)

            if s.get('ovr_income_tax') is not None:
                btn_revert = QPushButton('되돌리기')
                btn_revert.setStyleSheet(BTN_GHOST_DANGER + "QPushButton { font-size: 11px; }")
                btn_revert.setCursor(Qt.PointingHandCursor)
                btn_revert.clicked.connect(lambda _, sid=s['id']: self._revert_override(sid))
                btn_layout.addWidget(btn_revert)

            self.table.setCellWidget(row, 12, btn_widget)

        # KPI 갱신
        self.kpi_instructors.set_value(str(len(settlements)))
        self.kpi_total.set_value(f'{format_money(sum_total)}원')
        self.kpi_tax.set_value(f'{format_money(sum_tax + sum_local)}원')
        self.kpi_net.set_value(f'{format_money(sum_net)}원')

    def recalculate_settlements(self):
        """강의 내역 → 정산 재계산 (plan.md §4.1 파이프라인)"""
        lectures = self.repo.get_lectures_by_period(self.current_period)
        if not lectures:
            QMessageBox.information(self, '정산', f'{self.current_period} 기간의 강의 내역이 없습니다.')
            return

        aggregated = aggregate_lectures_to_settlements(lectures)

        for entry in aggregated:
            calc_data = {
                'total_payment': entry['total_payment'],
                'industry_code': entry['industry_code'],
                'is_foreigner': entry['is_foreigner'],
                'tax_rate': entry['tax_rate'],
                'income_tax': entry['income_tax'],
                'local_tax': entry['local_tax'],
                'net_payment': entry['net_payment'],
            }
            self.repo.upsert_settlement(
                entry['instructor_id'], self.current_period, calc_data
            )

        self.refresh_data()
        QMessageBox.information(
            self, '정산 완료',
            f'{len(aggregated)}명의 강사 정산이 완료되었습니다.'
        )

    def _open_override(self, settlement_id: int):
        dialog = OverrideDialog(self.repo, settlement_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_data()

    def _revert_override(self, settlement_id: int):
        reply = QMessageBox.question(
            self, '수동 수정 되돌리기',
            '자동 계산 값으로 되돌리시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.repo.revert_override(settlement_id)
            self.refresh_data()

    def _download_hometax_excel(self):
        """홈택스 11컬럼 엑셀 다운로드"""
        from PySide6.QtWidgets import QFileDialog
        from core.excel_generator import generate_hometax_excel
        from core.crypto import CryptoManager

        settlements = self.repo.get_settlements_by_period(self.current_period)
        if not settlements:
            QMessageBox.warning(self, '엑셀 다운로드', '정산 데이터가 없습니다. 먼저 [정산 재계산]을 실행하세요.')
            return

        default_name = f'간이지급명세서_{self.current_period}.xlsx'
        filepath, _ = QFileDialog.getSaveFileName(
            self, '홈택스 엑셀 저장', default_name,
            'Excel 파일 (*.xlsx);;모든 파일 (*.*)'
        )
        if not filepath:
            return

        try:
            import os
            crypto = CryptoManager()
            output_dir = os.path.dirname(filepath)
            result_path = generate_hometax_excel(self.repo, crypto, self.current_period, output_dir)
            QMessageBox.information(self, '다운로드 완료', f'홈택스 엑셀이 저장되었습니다:\n{result_path}')
        except Exception as e:
            QMessageBox.critical(self, '오류', f'엑셀 생성 실패:\n{str(e)}')

    def _auto_upload(self):
        """홈택스 자동 업로드 (RPA)"""
        from gui.rpa_progress_dialog import RPAProgressDialog
        from core.crypto import CryptoManager
        from core.excel_generator import generate_hometax_excel
        import os

        # 정산 데이터 확인
        settlements = self.repo.get_settlements_by_period(self.current_period)
        if not settlements:
            QMessageBox.warning(self, '자동 업로드',
                                '정산 데이터가 없습니다. 먼저 [정산 재계산]을 실행하세요.')
            return

        # 설정에서 인증 정보 로드
        crypto = CryptoManager()
        auth_method = (self.repo.get_setting('auth_method') or {}).get('value', 'certificate')
        cert_path = (self.repo.get_setting('cert_path') or {}).get('value', '')
        cert_pw_setting = self.repo.get_setting('cert_password')
        cert_password = ''
        if cert_pw_setting and cert_pw_setting.get('value'):
            try:
                cert_password = crypto.decrypt(cert_pw_setting['value'])
            except Exception:
                pass

        # 엑셀 파일 생성
        try:
            excel_path = generate_hometax_excel(self.repo, crypto, self.current_period)
        except Exception as e:
            QMessageBox.critical(self, '오류', f'엑셀 생성 실패:\n{str(e)}')
            return

        # RPA 다이얼로그 실행
        dialog = RPAProgressDialog(
            auth_method=auth_method,
            cert_path=cert_path,
            cert_password=cert_password,
            excel_path=excel_path,
            parent=self,
        )
        dialog.exec()
