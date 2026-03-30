"""
AutoTax — [탭2] 강의 내역 탭
prototype.html 강의 CRUD + 세액 자동계산 로직 이식
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QDialog,
    QHeaderView, QAbstractItemView, QMessageBox, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui.widgets import (
    Panel, Colors, format_money,
    BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER, BTN_GHOST_DANGER, BTN_SUCCESS,
    CheckBoxDelegate
)
from db.repository import Repository
from core.tax_calculator import calculate_taxes, get_tax_rate


class LectureTab(QWidget):
    """강의 내역 탭 — 강의 CRUD + 세액 자동계산"""
    data_changed = Signal()  # 데이터 변경 시그널 (삭제/추가/수정 후 다른 탭 갱신용)

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.current_period = '2026-03'
        self.setObjectName('lectureTab')
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

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

        # ── 강의 내역 패널 ──
        self.panel = Panel('강의 내역')

        # 헤더 위젯들
        input_style = f"""
            QLineEdit {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }}
        """

        self.filter_category = QLineEdit()
        self.filter_category.setPlaceholderText('과목 필터')
        self.filter_category.setFixedWidth(90)
        self.filter_category.setStyleSheet(input_style)
        self.filter_category.textChanged.connect(self._apply_filter)
        self.panel.add_header_widget(self.filter_category)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('검색')
        self.search_input.setFixedWidth(90)
        self.search_input.setStyleSheet(input_style)
        self.search_input.textChanged.connect(self._apply_filter)
        self.panel.add_header_widget(self.search_input)

        btn_excel = QPushButton('양식 출력')
        btn_excel.setStyleSheet(BTN_SUCCESS)
        btn_excel.setCursor(Qt.PointingHandCursor)
        btn_excel.clicked.connect(self._export_custom_excel)
        self.panel.add_header_widget(btn_excel)

        btn_prev = QPushButton('데이터 불러오기')
        btn_prev.setStyleSheet(BTN_SECONDARY)
        btn_prev.setCursor(Qt.PointingHandCursor)
        btn_prev.clicked.connect(self._load_previous_month)
        self.panel.add_header_widget(btn_prev)

        btn_all_select = QPushButton('전체 선택')
        btn_all_select.setStyleSheet(BTN_SECONDARY)
        btn_all_select.setCursor(Qt.PointingHandCursor)
        btn_all_select.clicked.connect(self._toggle_all_selection)
        self.panel.add_header_widget(btn_all_select)

        btn_delete_selected = QPushButton('선택 삭제')
        btn_delete_selected.setStyleSheet(BTN_DANGER)
        btn_delete_selected.setCursor(Qt.PointingHandCursor)
        btn_delete_selected.clicked.connect(self._delete_selected_lectures)
        self.panel.add_header_widget(btn_delete_selected)

        btn_add = QPushButton('+ 강의 추가')
        btn_add.setStyleSheet(BTN_PRIMARY)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._open_add_dialog)
        self.panel.add_header_widget(btn_add)

        # 시그널 연결은 모든 초기화 후에
        self.year_combo.currentIndexChanged.connect(self._on_period_changed)
        self.month_combo.currentIndexChanged.connect(self._on_period_changed)

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            '선택', '강사명', '과목구분', '프로그램', '회당 강사료',
            '횟수', '총 강사료', '소득세', '지방소득세', '실지급액', '관리'
        ])
        header = self.table.horizontalHeader()
        # 모든 칸럼 균등 배분 (Stretch) 후 특정 칸럼만 Fixed
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)            # 선택
        header.setSectionResizeMode(10, QHeaderView.Fixed)           # 관리
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(10, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
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
            QTableWidget::item:alternate {{
                background: #FAFCFE;
            }}
        """)
        # 체크박스 커스텀 렌더러 적용 (검정 테두리 + 빨간 V 표시)
        self.table.setItemDelegateForColumn(0, CheckBoxDelegate(self.table))
        self.table.setSortingEnabled(True)
        self.panel.body_layout.addWidget(self.table)
        layout.addWidget(self.panel)

    def _on_period_changed(self):
        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        self.current_period = f"{year}-{month}"
        self.refresh_data()

    def set_period(self, period: str):
        """외부에서 기간 설정"""
        self.current_period = period
        self.refresh_data()

    def refresh_data(self):
        """DB에서 강의 내역 새로고침"""
        lectures = self.repo.get_lectures_by_period(self.current_period)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(lectures))

        for row, lec in enumerate(lectures):
            total = lec['payment_amount']
            rate = get_tax_rate(lec['industry_code'])
            taxes = calculate_taxes(total, rate)

            # 체크박스
            cb_item = QTableWidgetItem()
            cb_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            cb_item.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, cb_item)

            # 강사명
            name_item = QTableWidgetItem(lec.get('instructor_name', ''))
            name_item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
            name_item.setData(Qt.UserRole, lec['id'])
            name_item.setForeground(Qt.black)
            self.table.setItem(row, 1, name_item)

            # 과목구분
            cat_item = QTableWidgetItem(lec.get('program_category', ''))
            cat_item.setForeground(Qt.black)
            self.table.setItem(row, 2, cat_item)

            # 프로그램명
            prog_item = QTableWidgetItem(lec.get('program_name', ''))
            prog_item.setForeground(Qt.black)
            self.table.setItem(row, 3, prog_item)

            # 회당 강사료
            fee_item = QTableWidgetItem(format_money(lec['fee_per_session']))
            fee_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            fee_item.setForeground(Qt.black)
            self.table.setItem(row, 4, fee_item)

            # 횟수
            cnt_item = QTableWidgetItem(f"{lec['session_count']}회")
            cnt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cnt_item.setForeground(Qt.red)
            cnt_item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
            self.table.setItem(row, 5, cnt_item)

            # 총 강사료
            total_item = QTableWidgetItem(format_money(total))
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
            total_item.setForeground(Qt.red)
            self.table.setItem(row, 6, total_item)

            # 소득세
            tax_item = QTableWidgetItem(format_money(taxes['income_tax']))
            tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tax_item.setForeground(Qt.black)
            self.table.setItem(row, 7, tax_item)

            # 지방소득세
            local_item = QTableWidgetItem(format_money(taxes['local_tax']))
            local_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            local_item.setForeground(Qt.black)
            self.table.setItem(row, 8, local_item)

            # 실지급액
            net_item = QTableWidgetItem(format_money(taxes['net_payment']))
            net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            net_item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
            net_item.setForeground(Qt.red)
            self.table.setItem(row, 9, net_item)

            # 관리 버튼
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            btn_edit = QPushButton('수정')
            btn_edit.setStyleSheet("""
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
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(lambda _, lid=lec['id']: self._open_edit_dialog(lid))

            btn_del = QPushButton('삭제')
            btn_del.setStyleSheet("""
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
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda _, lid=lec['id']: self._delete_lecture(lid))

            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 10, btn_widget)

        self.table.setSortingEnabled(True)
        self._apply_filter()

    def _apply_filter(self):
        """과목구분 + 검색어 필터"""
        cat_filter = self.filter_category.text().strip().lower()
        search = self.search_input.text().strip().lower()

        for row in range(self.table.rowCount()):
            show = True
            # 과목구분 필터 (열 2)
            if cat_filter:
                cat_item = self.table.item(row, 2)
                if cat_item and cat_filter not in cat_item.text().lower():
                    show = False
            # 검색 필터 (전 열)
            if show and search:
                match = False
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and search in item.text().lower():
                        match = True
                        break
                if not match:
                    show = False
            self.table.setRowHidden(row, not show)

    def _open_add_dialog(self):
        dialog = LectureDialog(self.repo, self.current_period, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_data()

    def _open_edit_dialog(self, lecture_id: int):
        dialog = LectureDialog(self.repo, self.current_period,
                               lecture_id=lecture_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_data()

    def _delete_lecture(self, lecture_id: int):
        reply = QMessageBox.question(
            self, '삭제 확인', '정말 삭제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.repo.delete_lecture(lecture_id)
            self.refresh_data()
            self.data_changed.emit()

    def _toggle_all_selection(self):
        """전체 선택/해제 토글"""
        any_unchecked = False
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() != Qt.Checked:
                any_unchecked = True
                break
        
        target_state = Qt.Checked if any_unchecked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(target_state)
        self.table.viewport().update()

    def _delete_selected_lectures(self):
        """선택 항목 삭제 로직"""
        selected_ids = []
        for row in range(self.table.rowCount()):
            cb_item = self.table.item(row, 0)
            if cb_item and cb_item.checkState() == Qt.Checked:
                name_item = self.table.item(row, 1)
                selected_ids.append((name_item.data(Qt.UserRole), name_item.text()))
                
        if not selected_ids:
            QMessageBox.warning(self, '선택 오류', '삭제할 강의 내역을 먼저 체크박스에 선택하세요.')
            return
            
        names = ", ".join([n for i, n in selected_ids])
        reply = QMessageBox.question(
            self, '일괄 삭제 확인',
            f"선택한 {len(selected_ids)}건의 강의 내역을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for lid, _ in selected_ids:
                self.repo.delete_lecture(lid)
            self.refresh_data()
            self.data_changed.emit()

    def _load_previous_month(self):
        """전월 데이터 복사 (prototype.html 로직 이식)"""
        year, month = self.current_period.split('-')
        y, m = int(year), int(month)
        m -= 1
        if m < 1:
            m = 12
            y -= 1
        prev_period = f"{y}-{m:02d}"

        prev_lectures = self.repo.get_lectures_by_period(prev_period)
        if not prev_lectures:
            QMessageBox.information(self, '전월 데이터', f'전월({prev_period}) 데이터가 없습니다.')
            return

        reply = QMessageBox.question(
            self, '전월 데이터 복사',
            f'전월({prev_period}) 강의 내역 {len(prev_lectures)}건을 당월로 복사하시겠습니까?\n'
            '이미 등록된 건이 있다면 중복될 수 있습니다.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for lec in prev_lectures:
                self.repo.create_lecture({
                    'instructor_id': lec['instructor_id'],
                    'program_id': lec['program_id'],
                    'period': self.current_period,
                    'payment_month': self.current_period,
                    'session_count': lec['session_count'],
                    'fee_per_session': lec['fee_per_session'],
                })
            self.refresh_data()
            QMessageBox.information(self, '복사 완료',
                                    f'{len(prev_lectures)}건 복사 완료. 강의 횟수를 수정해주세요.')

    def _export_custom_excel(self):
        """기안용 맞춤형 엑셀 출력"""
        from PySide6.QtWidgets import QFileDialog
        from core.excel_generator import generate_custom_excel
        import os

        cat_filter = self.filter_category.text().strip() or None
        
        prefix = f"{cat_filter} " if cat_filter else ""
        default_name = f'{prefix}강사료 지급내역_{self.current_period}.xlsx'
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, '기안용 엑셀 저장', default_name,
            'Excel 파일 (*.xlsx);;모든 파일 (*.*)'
        )
        if not filepath:
            return

        try:
            output_dir = os.path.dirname(filepath)
            result_path = generate_custom_excel(
                self.repo, self.current_period, cat_filter, output_dir
            )
            
            # 자동 열기 (Windows)
            try:
                os.startfile(result_path)
            except Exception as e:
                print(f"파일 자동 열기 실패: {e}")
                
            QMessageBox.information(self, '저장 완료', f'기안용 엑셀이 저장 및 실행되었습니다:\n{result_path}')
        except ValueError as e:
            QMessageBox.warning(self, '오류', str(e))
        except Exception as e:
            QMessageBox.critical(self, '오류', f'엑셀 생성 실패:\n{str(e)}')


# ═══════════════════════════════════════════════
# 강의 등록/수정 다이얼로그
# ═══════════════════════════════════════════════

class LectureDialog(QDialog):
    """강의 내역 등록/수정 모달"""

    def __init__(self, repo: Repository, current_period: str,
                 lecture_id: int = None, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.current_period = current_period
        self.lecture_id = lecture_id

        self.setWindowTitle('강의 수정' if lecture_id else '강의 내역 등록')
        self.setMinimumWidth(550)
        self.setStyleSheet(f"QDialog {{ background: white; }}")

        self._setup_ui()
        if lecture_id:
            self._load_data(lecture_id)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 0)
        layout.setSpacing(16)

        input_style = f"""
            QLineEdit, QComboBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {Colors.ACCENT};
            }}
        """
        label_style = f"font-size: 13px; font-weight: 500; color: {Colors.TEXT_PRIMARY};"

        # 강사 선택
        row1 = QHBoxLayout()
        inst_col = QVBoxLayout()
        lbl = QLabel('강사 선택 *')
        lbl.setStyleSheet(label_style)
        inst_col.addWidget(lbl)
        self.inst_combo = QComboBox()
        self.inst_combo.setStyleSheet(input_style)
        self.inst_combo.currentIndexChanged.connect(self._on_instructor_changed)
        inst_col.addWidget(self.inst_combo)

        prog_col = QVBoxLayout()
        lbl2 = QLabel('프로그램 선택 *')
        lbl2.setStyleSheet(label_style)
        prog_col.addWidget(lbl2)
        self.prog_combo = QComboBox()
        self.prog_combo.setStyleSheet(input_style)
        self.prog_combo.currentIndexChanged.connect(self._recalculate)
        prog_col.addWidget(self.prog_combo)

        row1.addLayout(inst_col)
        row1.addLayout(prog_col)
        layout.addLayout(row1)

        # 귀속연월 + 강의 횟수
        row2 = QHBoxLayout()
        period_col = QVBoxLayout()
        lbl3 = QLabel('귀속연월 *')
        lbl3.setStyleSheet(label_style)
        period_col.addWidget(lbl3)
        period_row = QHBoxLayout()
        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet(input_style)
        for y in range(2024, 2031):
            self.year_combo.addItem(f'{y}년', str(y))
        self.month_combo = QComboBox()
        self.month_combo.setStyleSheet(input_style)
        for m in range(1, 13):
            self.month_combo.addItem(f'{m}월', f'{m:02d}')
        # 현재 기간 설정
        cy, cm = self.current_period.split('-')
        idx_y = self.year_combo.findData(cy)
        if idx_y >= 0: self.year_combo.setCurrentIndex(idx_y)
        idx_m = self.month_combo.findData(cm)
        if idx_m >= 0: self.month_combo.setCurrentIndex(idx_m)
        period_row.addWidget(self.year_combo)
        period_row.addWidget(self.month_combo)
        period_col.addLayout(period_row)

        cnt_col = QVBoxLayout()
        lbl4 = QLabel('강의 횟수 *')
        lbl4.setStyleSheet(label_style)
        cnt_col.addWidget(lbl4)
        self.count_input = QLineEdit()
        self.count_input.setStyleSheet(input_style)
        self.count_input.setPlaceholderText('횟수')
        self.count_input.textChanged.connect(self._recalculate)
        cnt_col.addWidget(self.count_input)

        row2.addLayout(period_col)
        row2.addLayout(cnt_col)
        layout.addLayout(row2)

        # 세액 계산 박스 (prototype.html calc-box 이식)
        calc_frame = QFrame()
        calc_frame.setStyleSheet(f"""
            QFrame {{
                background: #F8F9FF;
                border: 1px solid #D0E2FF;
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        calc_layout = QVBoxLayout(calc_frame)
        calc_layout.setSpacing(8)

        row_style = f"font-size: 14px; color: {Colors.TEXT_PRIMARY}; border: none;"
        red_style = f"font-size: 14px; color: {Colors.ERROR}; border: none;"
        bold_style = f"font-size: 16px; font-weight: 600; color: {Colors.ACCENT}; border: none;"

        def make_calc_row(label, value_id, style=row_style):
            r = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet(style)
            v = QLabel('0')
            v.setStyleSheet(style + " font-weight: 600;")
            v.setAlignment(Qt.AlignRight)
            r.addWidget(l)
            r.addWidget(v)
            return r, v

        r1, self.calc_total = make_calc_row('총 강사료', 'total')
        calc_layout.addLayout(r1)

        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background: #D0E2FF; border: none;")
        calc_layout.addWidget(sep1)

        r2, self.calc_tax = make_calc_row('소득세 (자동)', 'tax', red_style)
        calc_layout.addLayout(r2)
        r3, self.calc_local = make_calc_row('지방소득세 (자동)', 'local', red_style)
        calc_layout.addLayout(r3)

        sep2 = QFrame()
        sep2.setFixedHeight(2)
        sep2.setStyleSheet(f"background: {Colors.PRIMARY}; border: none;")
        calc_layout.addWidget(sep2)

        r4, self.calc_net = make_calc_row('실지급액', 'net', bold_style)
        calc_layout.addLayout(r4)

        layout.addWidget(calc_frame)

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

        btn_save = QPushButton('저장')
        btn_save.setStyleSheet(BTN_PRIMARY)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save)

        footer_layout.addWidget(btn_cancel)
        footer_layout.addWidget(btn_save)
        layout.addWidget(footer)

        # 강사 콤보박스 데이터 로드
        self._load_instructors()

    def _load_instructors(self):
        instructors = self.repo.get_all_instructors()
        self.inst_combo.clear()
        self.inst_combo.addItem('강사 선택', None)
        for inst in instructors:
            self.inst_combo.addItem(inst['name'], inst['id'])

    def _on_instructor_changed(self):
        """강사 선택 시 프로그램 콤보 갱신"""
        inst_id = self.inst_combo.currentData()
        self.prog_combo.clear()
        if inst_id:
            programs = self.repo.get_programs_by_instructor(inst_id)
            for p in programs:
                self.prog_combo.addItem(
                    f"[{p['category']}] {p['program_name']} ({format_money(p['fee_per_session'])}원)",
                    {'id': p['id'], 'fee': p['fee_per_session'], 'category': p['category']}
                )
        self._recalculate()

    def _recalculate(self):
        """세액 자동계산 (prototype.html updateLectureCalc 이식)"""
        inst_id = self.inst_combo.currentData()
        prog_data = self.prog_combo.currentData()
        count_text = self.count_input.text().strip()

        if inst_id and prog_data and count_text:
            try:
                count = int(count_text)
            except ValueError:
                count = 0

            if count > 0:
                fee = prog_data['fee']
                total = fee * count

                # 강사의 업종코드 조회
                inst = self.repo.get_instructor(inst_id)
                rate = get_tax_rate(inst['industry_code']) if inst else 3
                taxes = calculate_taxes(total, rate)

                self.calc_total.setText(format_money(total))
                self.calc_tax.setText(format_money(taxes['income_tax']))
                self.calc_local.setText(format_money(taxes['local_tax']))
                self.calc_net.setText(format_money(taxes['net_payment']))
                return

        self.calc_total.setText('0')
        self.calc_tax.setText('0')
        self.calc_local.setText('0')
        self.calc_net.setText('0')

    def _load_data(self, lecture_id: int):
        """수정 모드: 기존 데이터 로드"""
        lec = self.repo.get_lecture(lecture_id)
        if not lec:
            return

        # 강사 선택
        idx = self.inst_combo.findData(lec['instructor_id'])
        if idx >= 0:
            self.inst_combo.setCurrentIndex(idx)

        # 프로그램 선택 (강사 변경 후)
        for i in range(self.prog_combo.count()):
            data = self.prog_combo.itemData(i)
            if data and data['id'] == lec['program_id']:
                self.prog_combo.setCurrentIndex(i)
                break

        # 기간
        year, month = lec['period'].split('-')
        iy = self.year_combo.findData(year)
        if iy >= 0: self.year_combo.setCurrentIndex(iy)
        im = self.month_combo.findData(month)
        if im >= 0: self.month_combo.setCurrentIndex(im)

        # 횟수
        self.count_input.setText(str(lec['session_count']))

    def _save(self):
        inst_id = self.inst_combo.currentData()
        prog_data = self.prog_combo.currentData()
        count_text = self.count_input.text().strip()

        if not inst_id:
            QMessageBox.warning(self, '입력 오류', '강사를 선택하세요.')
            return
        if not prog_data:
            QMessageBox.warning(self, '입력 오류', '프로그램을 선택하세요.')
            return
        if not count_text:
            QMessageBox.warning(self, '입력 오류', '강의 횟수를 입력하세요.')
            return

        try:
            count = int(count_text)
        except ValueError:
            QMessageBox.warning(self, '입력 오류', '강의 횟수는 숫자로 입력하세요.')
            return

        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        period = f"{year}-{month}"

        data = {
            'instructor_id': inst_id,
            'program_id': prog_data['id'],
            'period': period,
            'payment_month': period,
            'session_count': count,
            'fee_per_session': prog_data['fee'],
        }

        if self.lecture_id:
            self.repo.update_lecture(self.lecture_id, data)
        else:
            self.repo.create_lecture(data)

        self.accept()
