"""
AutoTax — [탭1] 강사 관리 탭
plan.md §5.4 + prototype.html 강사 CRUD 로직 이식
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QDialog, QFormLayout,
    QRadioButton, QButtonGroup, QHeaderView, QAbstractItemView,
    QMessageBox, QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui.widgets import (
    KPICard, Panel, StatusBadge, Colors, format_money,
    BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER, BTN_GHOST_DANGER, BTN_SUCCESS
)
from db.repository import Repository
from db.schema import initialize_database
from core.crypto import CryptoManager
from core.validator import (
    validate_resident_id, normalize_resident_id,
    validate_industry_code, INDUSTRY_CODE_NAMES
)


class InstructorTab(QWidget):
    """강사 관리 탭 — 강사 CRUD + 프로그램 관리"""

    def __init__(self, repo: Repository, crypto: CryptoManager, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.crypto = crypto
        self.setObjectName('instructorTab')
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ── KPI 요약 카드 ──
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)
        self.kpi_total = KPICard('등록 강사', '0')
        self.kpi_active = KPICard('활성 강사', '0', Colors.ACCENT)
        self.kpi_programs = KPICard('등록 프로그램 총계', '0')
        kpi_layout.addWidget(self.kpi_total)
        kpi_layout.addWidget(self.kpi_active)
        kpi_layout.addWidget(self.kpi_programs)
        layout.addLayout(kpi_layout)

        # ── 강사 목록 패널 ──
        self.panel = Panel('강사 목록')

        # 헤더에 검색 + 등록 버튼
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('강사 검색...')
        self.search_input.setFixedWidth(180)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
        """)
        self.search_input.textChanged.connect(self._filter_table)
        self.panel.add_header_widget(self.search_input)

        btn_add = QPushButton('+ 강사 등록')
        btn_add.setStyleSheet(BTN_PRIMARY)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._open_add_dialog)
        self.panel.add_header_widget(btn_add)

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            '강사명', '업종코드', '할당 프로그램', '연락처', '상태', '관리'
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                font-size: 13px;
                gridline-color: {Colors.BORDER};
            }}
            QTableWidget::item {{
                padding: 8px 12px;
            }}
            QHeaderView::section {{
                background: #FAFAFA;
                color: {Colors.TEXT_SECONDARY};
                font-weight: 500;
                font-size: 13px;
                padding: 10px 12px;
                border: none;
                border-bottom: 2px solid {Colors.BORDER};
            }}
            QTableWidget::item:alternate {{
                background: #FAFCFE;
            }}
        """)
        self.table.setSortingEnabled(True)

        self.panel.body_layout.addWidget(self.table)
        layout.addWidget(self.panel)

    def refresh_data(self):
        """DB에서 강사 목록 새로고침"""
        instructors = self.repo.get_all_instructors()
        total_programs = 0

        self.table.setRowCount(len(instructors))

        for row, inst in enumerate(instructors):
            # 프로그램 목록 조회
            programs = self.repo.get_programs_by_instructor(inst['id'])
            total_programs += len(programs)

            # 강사명
            name_item = QTableWidgetItem(inst['name'])
            name_item.setFont(QFont('Pretendard', 10, QFont.DemiBold))
            name_item.setData(Qt.UserRole, inst['id'])  # ID 저장
            self.table.setItem(row, 0, name_item)

            # 업종코드
            self.table.setItem(row, 1, QTableWidgetItem(inst['industry_code']))

            # 프로그램 목록 (뱃지 형태로 텍스트)
            prog_texts = [f"[{p['category']}] {p['program_name']}" for p in programs]
            prog_text = ', '.join(prog_texts) if prog_texts else '(미등록)'
            self.table.setItem(row, 2, QTableWidgetItem(prog_text))

            # 연락처
            self.table.setItem(row, 3, QTableWidgetItem(inst.get('phone', '') or '-'))

            # 상태 뱃지 (위젯)
            badge = StatusBadge('등록됨')
            self.table.setCellWidget(row, 4, badge)

            # 관리 버튼
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            btn_edit = QPushButton('수정')
            btn_edit.setStyleSheet(BTN_SECONDARY + "QPushButton { padding: 4px 12px; font-size: 12px; }")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(lambda checked, iid=inst['id']: self._open_edit_dialog(iid))

            btn_del = QPushButton('삭제')
            btn_del.setStyleSheet(BTN_GHOST_DANGER)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda checked, iid=inst['id']: self._delete_instructor(iid))

            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 5, btn_widget)

        # KPI 업데이트
        self.kpi_total.set_value(str(len(instructors)))
        self.kpi_active.set_value(str(len(instructors)))
        self.kpi_programs.set_value(str(total_programs))

    def _filter_table(self, text: str):
        """검색어로 테이블 필터링"""
        text = text.lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def _open_add_dialog(self):
        """새 강사 등록 다이얼로그"""
        dialog = InstructorDialog(self.repo, self.crypto, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_data()

    def _open_edit_dialog(self, instructor_id: int):
        """강사 수정 다이얼로그"""
        dialog = InstructorDialog(self.repo, self.crypto,
                                  instructor_id=instructor_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_data()

    def _delete_instructor(self, instructor_id: int):
        """강사 삭제 확인"""
        inst = self.repo.get_instructor(instructor_id)
        if not inst:
            return

        reply = QMessageBox.question(
            self, '강사 삭제',
            f"'{inst['name']}' 강사를 삭제하시겠습니까?\n"
            "연결된 프로그램과 강의 내역도 삭제될 수 있습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.repo.delete_instructor(instructor_id)
            self.refresh_data()


# ═══════════════════════════════════════════════
# 강사 등록/수정 다이얼로그 (prototype.html 모달 이식)
# ═══════════════════════════════════════════════

class InstructorDialog(QDialog):
    """강사 등록/수정 모달 다이얼로그"""

    def __init__(self, repo: Repository, crypto: CryptoManager,
                 instructor_id: int = None, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.crypto = crypto
        self.instructor_id = instructor_id
        self.temp_programs = []

        self.setWindowTitle('강사 수정' if instructor_id else '강사 등록')
        self.setMinimumWidth(600)
        self.setMaximumHeight(700)
        self.setStyleSheet(f"""
            QDialog {{
                background: white;
            }}
            QLabel {{
                font-size: 13px;
                font-weight: 500;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        self._setup_ui()

        if instructor_id:
            self._load_data(instructor_id)

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
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

        # ── 기본 정보 ──
        row1 = QHBoxLayout()
        name_col = QVBoxLayout()
        name_col.addWidget(QLabel('강사명 *'))
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(input_style)
        name_col.addWidget(self.name_input)

        rid_col = QVBoxLayout()
        rid_col.addWidget(QLabel('주민등록번호 *'))
        self.rid_input = QLineEdit()
        self.rid_input.setPlaceholderText('000000-0000000')
        self.rid_input.setStyleSheet(input_style)
        rid_col.addWidget(self.rid_input)

        row1.addLayout(name_col)
        row1.addLayout(rid_col)
        layout.addLayout(row1)

        # 업종코드
        layout.addWidget(QLabel('업종코드 *'))
        self.code_combo = QComboBox()
        self.code_combo.setStyleSheet(input_style)
        for code, name in sorted(INDUSTRY_CODE_NAMES.items()):
            self.code_combo.addItem(f'{code} ({name})', code)
        # 기본값: 940909
        idx = self.code_combo.findData('940909')
        if idx >= 0:
            self.code_combo.setCurrentIndex(idx)
        layout.addWidget(self.code_combo)

        # 내외국인
        fg_layout = QHBoxLayout()
        fg_layout.addWidget(QLabel('내외국인 *'))
        fg_layout.addStretch()
        self.fg_group = QButtonGroup(self)
        self.fg_korean = QRadioButton('1 (내국인)')
        self.fg_foreign = QRadioButton('9 (외국인)')
        self.fg_korean.setChecked(True)
        self.fg_group.addButton(self.fg_korean, 1)
        self.fg_group.addButton(self.fg_foreign, 9)
        fg_layout.addWidget(self.fg_korean)
        fg_layout.addWidget(self.fg_foreign)
        layout.addLayout(fg_layout)

        # ── 프로그램 영역 ──
        prog_frame = QFrame()
        prog_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                background: #FAFBFC;
            }}
        """)
        prog_layout = QVBoxLayout(prog_frame)
        prog_layout.setContentsMargins(16, 12, 16, 12)

        prog_title = QLabel('프로그램 (1개 이상 필수)')
        prog_title.setStyleSheet('font-size: 14px; font-weight: 600; border: none;')
        prog_layout.addWidget(prog_title)

        # 프로그램 입력 행
        prog_input = QHBoxLayout()
        self.prog_category = QLineEdit()
        self.prog_category.setPlaceholderText('과목구분')
        self.prog_category.setStyleSheet(input_style)
        self.prog_name = QLineEdit()
        self.prog_name.setPlaceholderText('프로그램명')
        self.prog_name.setStyleSheet(input_style)
        self.prog_fee = QLineEdit()
        self.prog_fee.setPlaceholderText('회당 강사료')
        self.prog_fee.setStyleSheet(input_style)
        self.prog_fee.setFixedWidth(120)

        btn_add_prog = QPushButton('추가')
        btn_add_prog.setStyleSheet(BTN_SECONDARY + "QPushButton { padding: 8px 16px; }")
        btn_add_prog.setCursor(Qt.PointingHandCursor)
        btn_add_prog.clicked.connect(self._add_program)

        prog_input.addWidget(self.prog_category)
        prog_input.addWidget(self.prog_name)
        prog_input.addWidget(self.prog_fee)
        prog_input.addWidget(btn_add_prog)
        prog_layout.addLayout(prog_input)

        # 프로그램 목록 영역
        self.prog_list_layout = QVBoxLayout()
        prog_layout.addLayout(self.prog_list_layout)

        layout.addWidget(prog_frame)

        # ── 추가 정보 (선택) ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        layout.addWidget(sep)

        opt_label = QLabel('추가 정보 (선택)')
        opt_label.setStyleSheet(f'font-size: 13px; color: {Colors.TEXT_SECONDARY};')
        layout.addWidget(opt_label)

        row_contact = QHBoxLayout()
        phone_col = QVBoxLayout()
        phone_col.addWidget(QLabel('연락처'))
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText('010-0000-0000')
        self.phone_input.setStyleSheet(input_style)
        phone_col.addWidget(self.phone_input)

        email_col = QVBoxLayout()
        email_col.addWidget(QLabel('이메일'))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('email@domain.com')
        self.email_input.setStyleSheet(input_style)
        email_col.addWidget(self.email_input)
        row_contact.addLayout(phone_col)
        row_contact.addLayout(email_col)
        layout.addLayout(row_contact)

        addr_col = QVBoxLayout()
        addr_col.addWidget(QLabel('주소'))
        self.address_input = QLineEdit()
        self.address_input.setStyleSheet(input_style)
        addr_col.addWidget(self.address_input)
        layout.addLayout(addr_col)

        row_bank = QHBoxLayout()
        bank_col = QVBoxLayout()
        bank_col.addWidget(QLabel('은행'))
        self.bank_input = QLineEdit()
        self.bank_input.setStyleSheet(input_style)
        bank_col.addWidget(self.bank_input)

        account_col = QVBoxLayout()
        account_col.addWidget(QLabel('계좌번호'))
        self.account_input = QLineEdit()
        self.account_input.setStyleSheet(input_style)
        account_col.addWidget(self.account_input)
        row_bank.addLayout(bank_col)
        row_bank.addLayout(account_col)
        layout.addLayout(row_bank)

        memo_col = QVBoxLayout()
        memo_col.addWidget(QLabel('비고/메모'))
        self.memo_input = QLineEdit()
        self.memo_input.setStyleSheet(input_style)
        memo_col.addWidget(self.memo_input)
        layout.addLayout(memo_col)

        scroll.setWidget(inner)

        # ── 하단 버튼 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton('취소')
        btn_cancel.setStyleSheet(BTN_SECONDARY)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton('저장')
        btn_save.setStyleSheet(BTN_PRIMARY)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)

        # 전체 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background: #FAFAFA;
                border-top: 1px solid {Colors.BORDER};
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)
        footer_layout.addStretch()
        footer_layout.addWidget(btn_cancel)
        footer_layout.addWidget(btn_save)
        main_layout.addWidget(footer)

    def _load_data(self, instructor_id: int):
        """수정 모드: 기존 데이터 로드"""
        inst = self.repo.get_instructor(instructor_id)
        if not inst:
            return

        self.name_input.setText(inst['name'])

        # 주민번호 복호화
        try:
            decrypted_rid = self.crypto.decrypt(inst['resident_id'])
            self.rid_input.setText(decrypted_rid)
        except Exception:
            self.rid_input.setText(inst['resident_id'])

        # 업종코드
        idx = self.code_combo.findData(inst['industry_code'])
        if idx >= 0:
            self.code_combo.setCurrentIndex(idx)

        # 내외국인
        if inst.get('is_foreigner') == '9':
            self.fg_foreign.setChecked(True)
        else:
            self.fg_korean.setChecked(True)

        # 선택 정보
        self.phone_input.setText(inst.get('phone', '') or '')
        self.email_input.setText(inst.get('email', '') or '')
        self.address_input.setText(inst.get('address', '') or '')
        self.bank_input.setText(inst.get('bank_name', '') or '')
        self.account_input.setText(inst.get('account_number', '') or '')
        self.memo_input.setText(inst.get('memo', '') or '')

        # 프로그램 목록 로드
        programs = self.repo.get_programs_by_instructor(instructor_id)
        for p in programs:
            self.temp_programs.append({
                'id': p['id'],
                'category': p['category'],
                'program_name': p['program_name'],
                'fee_per_session': p['fee_per_session'],
            })
        self._render_programs()

    def _add_program(self):
        """임시 프로그램 추가"""
        category = self.prog_category.text().strip()
        name = self.prog_name.text().strip()
        fee_text = self.prog_fee.text().strip()

        if not category or not name or not fee_text:
            QMessageBox.warning(self, '입력 오류', '과목구분, 프로그램명, 회당 강사료를 모두 입력하세요.')
            return

        try:
            fee = int(fee_text)
        except ValueError:
            QMessageBox.warning(self, '입력 오류', '회당 강사료는 숫자로 입력하세요.')
            return

        self.temp_programs.append({
            'id': None,  # 신규
            'category': category,
            'program_name': name,
            'fee_per_session': fee,
        })

        self.prog_category.clear()
        self.prog_name.clear()
        self.prog_fee.clear()
        self._render_programs()

    def _render_programs(self):
        """임시 프로그램 목록 렌더링"""
        # 기존 위젯 제거
        while self.prog_list_layout.count():
            item = self.prog_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, p in enumerate(self.temp_programs):
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background: white;
                    border: 1px solid {Colors.BORDER};
                    border-radius: 6px;
                    padding: 6px 12px;
                }}
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 6, 12, 6)

            info_text = f"[{p['category']}]  {p['program_name']}  ({format_money(p['fee_per_session'])}원)"
            info_label = QLabel(info_text)
            info_label.setStyleSheet('font-size: 13px; border: none;')

            btn_del = QPushButton('삭제')
            btn_del.setStyleSheet(BTN_GHOST_DANGER)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda checked, idx=i: self._remove_program(idx))

            row_layout.addWidget(info_label)
            row_layout.addStretch()
            row_layout.addWidget(btn_del)

            self.prog_list_layout.addWidget(row)

    def _remove_program(self, index: int):
        """프로그램 삭제"""
        if 0 <= index < len(self.temp_programs):
            self.temp_programs.pop(index)
            self._render_programs()

    def _save(self):
        """저장 (등록 또는 수정)"""
        name = self.name_input.text().strip()
        rid_raw = self.rid_input.text().strip()

        # 필수 검증
        if not name:
            QMessageBox.warning(self, '입력 오류', '강사명을 입력하세요.')
            return

        if not rid_raw:
            QMessageBox.warning(self, '입력 오류', '주민등록번호를 입력하세요.')
            return

        # 주민번호 검증
        rid_normalized = normalize_resident_id(rid_raw)
        ok, msg = validate_resident_id(rid_normalized)
        if not ok:
            QMessageBox.warning(self, '입력 오류', msg)
            return

        if len(self.temp_programs) == 0:
            QMessageBox.warning(self, '입력 오류', '프로그램을 1개 이상 등록하세요.')
            return

        # 업종코드
        industry_code = self.code_combo.currentData()
        is_foreigner = '9' if self.fg_foreign.isChecked() else '1'

        # 주민번호 암호화
        encrypted_rid = self.crypto.encrypt(rid_normalized)

        data = {
            'name': name,
            'resident_id': encrypted_rid,
            'industry_code': industry_code,
            'is_foreigner': is_foreigner,
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'address': self.address_input.text().strip(),
            'bank_name': self.bank_input.text().strip(),
            'account_number': self.account_input.text().strip(),
            'memo': self.memo_input.text().strip(),
        }

        if self.instructor_id:
            # 수정
            self.repo.update_instructor(self.instructor_id, data)
            # 프로그램: 기존 삭제 후 재등록
            self.repo.delete_programs_by_instructor(self.instructor_id)
            for p in self.temp_programs:
                self.repo.create_program({
                    'instructor_id': self.instructor_id,
                    'category': p['category'],
                    'program_name': p['program_name'],
                    'fee_per_session': p['fee_per_session'],
                })
        else:
            # 신규 등록
            new_id = self.repo.create_instructor(data)
            for p in self.temp_programs:
                self.repo.create_program({
                    'instructor_id': new_id,
                    'category': p['category'],
                    'program_name': p['program_name'],
                    'fee_per_session': p['fee_per_session'],
                })

        self.accept()
