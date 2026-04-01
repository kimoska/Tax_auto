"""
AutoTax — [탭3] 월별 정산 탭 (홈택스 제출용)
plan.md §5.4 + prototype.html 정산 로직 이식
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QDialog,
    QHeaderView, QAbstractItemView, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QShortcut, QKeySequence

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

        # ── 년/월 선택 영역 (패널 위 별도 행, 오른쪽 정렬) ──
        combo_style = f"QComboBox {{ border: 1px solid {Colors.BORDER}; border-radius: 6px; padding: 4px 8px; font-size: 13px; min-width: 80px; }}"
        period_row = QHBoxLayout()
        period_row.setContentsMargins(0, 0, 0, 0)
        period_row.addStretch()

        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet(combo_style)
        for y in range(2024, 2031):
            self.year_combo.addItem(f"{y}년", str(y))
        self.year_combo.setCurrentText(self.current_period.split('-')[0] + '년')
        period_row.addWidget(self.year_combo)

        self.month_combo = QComboBox()
        self.month_combo.setStyleSheet(combo_style.replace("80px", "60px"))
        for m in range(1, 13):
            self.month_combo.addItem(f"{m}월", f"{m:02d}")
        self.month_combo.setCurrentIndex(int(self.current_period.split('-')[1]) - 1)
        period_row.addWidget(self.month_combo)

        layout.addLayout(period_row)

        # ── 정산 테이블 패널 ──
        self.panel = Panel('간이지급명세서 미리보기')

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

        # 시그널 연결은 모든 초기화 후에
        self.year_combo.currentIndexChanged.connect(self._on_period_changed)
        self.month_combo.currentIndexChanged.connect(self._on_period_changed)

        # 테이블 (홈택스 간이지급명세서 11칸럼 + 관리)
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            '번호', '귀속연도', '귀속월', '업종코드', '소득자성명',
            '주민등록번호', '내외국인', '지급액', '세율(%)',
            '소득세', '지방소득세', '실지급액', '관리'
        ])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(60)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        header.setSectionResizeMode(0, QHeaderView.Fixed)            # 번호
        header.setSectionResizeMode(12, QHeaderView.Fixed)           # 관리
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(12, 110)
        
        # 비율 기반 초기 너비
        self._col_ratios = [0, 0.07, 0.05, 0.08, 0.10, 0.15, 0.05, 0.11, 0.05, 0.08, 0.08, 0.18, 0]
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

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
            QTableWidget::item:selected {{
                background-color: #E0E7FF;
                color: #1E293B;
                font-weight: bold;
            }}
            QTableWidget::item:alternate {{ background: #FAFCFE; }}
            QTableWidget::item:hover {{ background-color: transparent; }}
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
        fixed = self.table.columnWidth(0) + self.table.columnWidth(12)
        avail = total - fixed
        if avail <= 0:
            return
            
        used = 0
        last_interactive = 11
        
        for i, ratio in enumerate(self._col_ratios):
            if ratio > 0:
                w = int(avail * ratio)
                self.table.setColumnWidth(i, w)
                used += w
                
        if avail > used:
            self.table.setColumnWidth(last_interactive, self.table.columnWidth(last_interactive) + (avail - used))

    def _on_period_changed(self):
        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        self.current_period = f"{year}-{month}"
        self.refresh_data()

    def set_period(self, period: str):
        self.current_period = period
        self.refresh_data()

    def refresh_data(self):
        """정산 테이블 갱신 (캐시된 데이터만 로드, DB 쓰기 없음)"""
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
            pay_item.setForeground(QColor("#DC2626")) # Red
            self.table.setItem(row, 7, pay_item)

            # 세율
            rate_item = QTableWidgetItem(str(s['tax_rate']))
            rate_item.setForeground(Qt.black)
            self.table.setItem(row, 8, rate_item)

            # 소득세
            tax_item = QTableWidgetItem(format_money(s['final_income_tax']))
            tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tax_item.setForeground(Qt.black)
            self.table.setItem(row, 9, tax_item)

            # 지방소득세
            local_item = QTableWidgetItem(format_money(s['final_local_tax']))
            local_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            local_item.setForeground(Qt.black)
            self.table.setItem(row, 10, local_item)

            # 실지급액
            net_item = QTableWidgetItem(format_money(s['final_net_payment']))
            net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            net_item.setForeground(QColor("#DC2626")) # Red
            self.table.setItem(row, 11, net_item)

            # 관리 버튼
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            btn_ovr = QPushButton('수정')
            btn_ovr.setStyleSheet("""
                QPushButton { 
                    color: #2563EB; 
                    background: transparent;
                    border: 1px solid #BFDBFE;
                    border-radius: 4px;
                    padding: 4px 8px; 
                    font-size: 12px; 
                }
                QPushButton:hover { background: #EFF6FF; }
            """)
            btn_ovr.setCursor(Qt.PointingHandCursor)
            btn_ovr.clicked.connect(lambda _, sid=s['id']: self._open_override(sid))
            btn_layout.addWidget(btn_ovr)

            if s.get('ovr_income_tax') is not None:
                btn_revert = QPushButton('되돌리기')
                btn_revert.setStyleSheet("""
                    QPushButton { 
                        color: #DC2626; 
                        background: transparent;
                        border: 1px solid #FECACA;
                        border-radius: 4px;
                        padding: 4px 8px; 
                        font-size: 12px; 
                    }
                    QPushButton:hover { background: #FEF2F2; }
                """)
                btn_revert.setCursor(Qt.PointingHandCursor)
                btn_revert.clicked.connect(lambda _, sid=s['id']: self._revert_override(sid))
                btn_layout.addWidget(btn_revert)

            self.table.setCellWidget(row, 12, btn_widget)

        # KPI 갱신
        self.kpi_instructors.set_value(str(len(settlements)))
        self.kpi_total.set_value(f'{format_money(sum_total)}원')
        self.kpi_tax.set_value(f'{format_money(sum_tax + sum_local)}원')
        self.kpi_net.set_value(f'{format_money(sum_net)}원')

    def _sync_settlements_from_lectures(self):
        """강의 데이터 기반으로 정산 동기화 (기존 정산 삭제 후 재생성)"""
        lectures = self.repo.get_lectures_by_period(self.current_period)
        # 기존 정산 데이터 전부 삭제
        self.repo.delete_settlements_by_period(self.current_period)

    def recalculate_settlements(self):
        """강의 내역 → 정산 재계산 (plan.md §4.1 파이프라인) - 수동 트리거"""
        from PySide6.QtWidgets import QApplication, QProgressDialog
        
        # 안내 모달창 표시
        dialog = QProgressDialog("클라우드 통신 중입니다. 잠시만 기다려주세요...", None, 0, 0, self)
        dialog.setWindowTitle("정산 데이터 동기화")
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.show()
        QApplication.processEvents()

        try:
            dialog.setLabelText("정산 기록을 동기화하고 있습니다...")
            QApplication.processEvents()
            
            # 레포지토리의 동기화 메서드 호출 (강의 없으면 정산 삭제 처리됨)
            self.repo.sync_settlements_for_period(self.current_period)
            
            dialog.setLabelText("화면에 데이터를 불러오는 중입니다...")
            QApplication.processEvents()
            
            self.refresh_data()
            aggregated = aggregate_lectures_to_settlements(lectures)
            
            dialog.append_log(f"[{self.current_period}] 정산이 성공적으로 완료되었습니다.")
            QApplication.processEvents()

            # 잠깐 대기 후 닫기
            import time
            time.sleep(0.5)

        except Exception as e:
            dialog.append_log(f"오류가 발생했습니다: {e}")
            QMessageBox.critical(self, "오류", f"정산 처리 중 통신 오류가 발생했습니다:\n{e}")
        finally:
            dialog.close()

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
            output_dir = os.path.dirname(filepath)
            result_path = generate_hometax_excel(self.repo, self.current_period, output_dir)
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

        # 엑셀 파일 생성
        try:
            excel_path = generate_hometax_excel(self.repo, self.current_period)
        except Exception as e:
            QMessageBox.critical(self, '오류', f'엑셀 생성 실패:\n{str(e)}')
            return
        
        # [수정 사항] 홈택스 업로드 시작 전 로그인/인증서 선택 창 표시
        from gui.login_window import LoginWindow
        from core.crypto import CryptoManager
        from PySide6.QtWidgets import QDialog
        
        crypto_mgr = CryptoManager()
        login_dialog = LoginWindow(repo=self.repo, crypto=crypto_mgr, parent=self)
        if login_dialog.exec() != QDialog.Accepted:
            # 사용자가 로그인 창을 닫거나 취소한 경우 중단
            return

        # 방금 로그인 창에서 선택한 인증서 정보 직접 추출 (체크박스 무관하게 최신값 반영)
        selected_cert = login_dialog.selected_cert
        
        auth_method = 'certificate'
        cert_keyword = selected_cert.subject_cn if selected_cert else ''
        cert_drive = selected_cert.path[0].upper() if selected_cert and selected_cert.path else 'C'
        cert_password = login_dialog.pw_input.text()

        # 정산 데이터를 RPA에 전달 (홈택스 목록 수정용)
        settlement_data = [
            {
                'name': s.get('name', ''),
                'resident_id': s.get('resident_id', ''),
                'total_payment': s.get('total_payment', 0),
                'industry_code': s.get('industry_code', '940909'),
                'is_foreigner': s.get('is_foreigner', '1'),
                'period': self.current_period,
            }
            for s in settlements
        ]

        # RPA 다이얼로그 실행
        dialog = RPAProgressDialog(
            excel_path=excel_path,
            auth_method=auth_method,
            cert_keyword=cert_keyword,
            cert_drive=cert_drive,
            cert_password=cert_password,
            settlements=settlement_data,
            parent=self,
        )
        dialog.exec()
