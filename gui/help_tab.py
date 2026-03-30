from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QTextBrowser, QLineEdit, QSplitter, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui.widgets import Colors, Panel

HELP_ARTICLES = {
    "1. 클라우드 로그인 및 시작 가이드": """
<h2>클라우드 로그인 및 시작 가이드</h2>
<p>이 시스템은 담당자님의 과중한 강사료 세금 계산 및 홈택스 신고 등 반복적인 서류 업무를 자동화하기 위해 설계된 전용 <b>클라우드 기반 솔루션</b>입니다.</p>
<hr>
<h3>1. 다중 직원 가입 및 기관 코드 방을 통한 데이터 공유</h3>
<p>본 프로그램은 부서 내 실무자들이 언제 어디서든 동일한 실시간 데이터에 함께 접근할 수 있도록 클라우드 동기화로 작동합니다.</p>
<ul>
<li><b>[최초 1회] A기관을 위한 기관코드 생성:</b> 복지관에서 이 프로그램을 처음 사용할 때, <b>가장 먼저 아이디를 만드는 A직원</b>이 시작 화면에서 <b>[기관 등록]</b> 탭을 눌러 사용할 '기관명'과 나음대로 정한 '기관코드'를 기입하고 등록합니다. (예: 대치노인복지관 / 코드: adgwcs1234)</li>
<li><b>[그 이후] 동료 B직원의 회원가입:</b> 위에서 기관코드가 만들어졌다면, <b>두 번째 B직원부터는 일반 [직원 로그인] 창에서 본인이 쓸 이메일과 비밀번호, 그리고 만들어진 기관코드(adgwcs1234)를 입력하고 창 왼쪽 아래의 [회원가입] 버튼</b>을 누릅니다. 회원가입이 완료된 후 로그인하면 A직원과 완벽하게 동일한 강사 데이터를 공유하며 작업할 수 있습니다.</li>
</ul>

<h3>2. 데이터 보관 및 보안 메커니즘</h3>
<p>여러분이 입력하시는 강사 데이터(주민등록번호, 계좌번호 등)와 정산 내역은 철저하게 보호됩니다.</p>
<ul>
<li><b>Google Firebase 클라우드:</b> 모든 데이터는 글로벌 최고 수준의 보안 인프라인 <b>Google Firebase</b> 서버에 저장됩니다. 각 기관코드(예: adgwcs1234)별로 데이터 저장 공간이 완벽히 분리되어(테넌트 격리), 다른 기관에서는 절대 우리 기관의 데이터를 볼 수 없습니다.</li>
<li><b>로컬 암호화 (AES-256):</b> 주민등록번호와 같은 초민감 개인정보는 클라우드 서버에 전송되기 직전에, 담당자 PC 자체(로컬)에서 최고 등급의 암호화(CryptoManager) 과정을 거칩니다. 따라서 서버 관리자라 할지라도 해독된 원본 주민등록번호를 알아낼 수 없는 극강의 보안성을 제공합니다.</li>
</ul>
""",
    "2. 강사 개별 및 엑셀 일괄 등록": """
<h2>강사 정보 등록 가이드</h2>
<p>시스템 사용의 첫 단추인 강사 인적사항 데이터베이스 구축 방법입니다. 모든 강사의 정보는 주민등록번호를 기준으로 고유 식별되므로, 주민번호 기입 시 반드시 올바른 하이픈(-) 형식을 준수하십시오.</p>
<hr>
<h3>엑셀 일괄 등록 방법 (가장 추천하는 방식)</h3>
<p>신규 학기나 연초에 대규모로 강사를 세팅할 때 소요되는 시간을 압도적으로 단축시켜 드립니다.</p>
<ol>
<li>우측 상단의 <b>양식 다운로드</b> 버튼을 클릭하여 프로그램이 제공하는 공식 엑셀 폼을 PC에 저장합니다.</li>
<li>다운로드된 엑셀을 열고 각 강사님의 이름, 주민번호, 계좌 정보, 과목명, 회당 강사료를 입력합니다. (단위 강사료에는 쉼표 없이 숫자만 기입합니다.)</li>
<li>입력이 끝난 엑셀 파일을 <b>엑셀 일괄 등록</b> 버튼을 통해 시스템에 업로드합니다. 중복 강사는 자동으로 건너뛰거나 회당 강사료만 갱신됩니다.</li>
</ol>

<h3>개별 등록 및 수정</h3>
<p>강사 탭의 <b>강사 등록</b> 버튼을 눌러 소수의 인원을 즉시 보강할 수 있습니다. 이미 등록된 내용의 오타나 변동사항 (연락처, 은행 등)을 수정할 경우, 리스트 우측 끝에 위치한 <b>관리</b> 버튼 그룹 내 수정 아이콘을 클릭하여 기재 사항을 정정하십시오.</p>
""",
    "3. 당월 강의 세부 횟수 입력": """
<h2>강의 내역 및 회차 입력</h2>
<p>당월 지급될 강사료의 세액(소득세 3% 및 지방소득세 0.3%)을 산출하기 위한 필수 작업 공간입니다.</p>
<hr>
<h3>강의 내역 입력 방식</h3>
<p>우측 상단의 날짜 조회기(예: <b>2026년 3월</b>)가 이번 달 지급분과 일치하는지 먼저 확인하십시오.</p>
<ul>
<li><b>내용 자동 불러오기:</b> 신규 강의 기록 시, 앞서 등록해둔 강사님을 목록에서 선택하기만 하면 과목 내용과 약정된 1회당 강사료가 즉시 채워집니다.</li>
<li><b>세액 계산:</b> 산출 방식이 매우 간편합니다. 담당자는 단지 <b>수업 진행 횟수</b>(예: 4회)만 기입하십시오. 프로그램 내부 모듈이 전체 강사료 누적액과 관련 세금 공제액, 그리고 최종 실지급액을 밀리초 단위로 정확하게 산출하여 장부에 기재합니다.</li>
</ul>
<p>※ 만약 특정 강사님이 규정상 세금 공제 대상이 아니거나, 단수 차이로 인해 10원 단위 조절이 불가피한 예외 상황이 발생한다면 수동 조절(예외 처리) 기능을 활용하십시오.</p>
""",
    "4. 월별 합산 정산 및 마감 프로세스": """
<h2>월별 정산(합산) 및 결산 마감</h2>
<p>강사료 지급일 전, 지출 결의를 올리거나 기관 내부 검증을 진행할 때 가장 중요하게 참고하시는 대시보드 화면입니다.</p>
<hr>
<h3>합산 자동화 메커니즘</h3>
<p>강사 한 분이 2개 이상의 과목(예: 스마트폰 교실, 댄스 스포츠 교실)을 동시에 담당하여 출강하셨을 경우, 각각 분리되어 있던 강사료 내역을 월별 정산 탭에서 <b>주민등록번호 기준 단일 내역으로 완벽하게 병합(Merge)</b>합니다. 이는 국세청 간이지급명세서 제출 표준 포맷을 철저히 준수한 것입니다.</p>

<h3>정산 검증 절차</h3>
<ol>
<li>화면 상단(우측)에 명시된 주요 지표 [전체 강사 수], [총 지급액 합계], [총 세금 원천징수액] 이 기관 예산안 및 이체 예정 금액과 100% 일치하는지 마지막으로 눈으로 확인하십시오.</li>
<li>세부 스크롤을 내려 특정 강사의 이례적인 징수 금액이 없는지 점검합니다.</li>
</ol>
""",
    "5. 홈택스 간이지급명세서 제출": """
<h2>홈택스 엑셀 다운로드 및 자동 신고 가이드</h2>
<p>센터 업무의 가장 큰 허들인 관공서(홈택스) 전자신고를 단 몇 번의 마우스 클릭만으로 처리하는 강력한 기능입니다.</p>
<hr>
<h3>[방식 1] 홈택스 자동 업로드 (추천)</h3>
<p>프로그램이 알아서 홈택스에 로그인하고 간이지급명세서를 전송하는 무인 자동화 기능입니다.</p>
<p><b>※ 참고:</b> 홈택스 자동 업로드 버튼을 눌러 처음 창이 열릴 때 오류 메시지가 뜰 수 있습니다. 그럴 경우 창을 닫고 다시 재시도를 눌러주세요.</p>
<ol>
<li>정산 테이블 상단의 <b>[홈택스 자동 업로드]</b> 버튼을 누르십시오.</li>
<li>로그인 인증서 선택 창이 뜹니다. 기관 공인인증서를 선택하고 비밀번호를 입력합니다. (이 정보는 클라우드에 절대 저장되지 않으며 즉시 폐기됩니다)</li>
<li>프로그램이 홈택스 창을 띄우고 자동으로 로그인 및 파일 업로드 과정을 수행합니다. 화면이 스스로 움직이는 동안 마우스 조작을 잠시 멈춰주세요.</li>
</ol>

<h3>[방식 2] 홈택스 엑셀 다운로드 (수동 신고)</h3>
<p>담당자님이 직접 국세청 사이트에 제출하길 원하실 때 사용하는 보조 기능입니다.</p>
<ol>
<li><b>[홈택스 엑셀 다운로드]</b> 버튼을 눌러 국세청 전용 포맷의 엑셀 파일을 PC 바탕화면에 저장합니다.</li>
<li>국세청 홈택스 웹사이트에 기관 공인인증서로 수동 접속하십시오.</li>
<li><b>신고/납부 &gt; 일반신고 &gt; 간이지급명세서(거주자의 사업소득)</b> 메뉴에서 <b>'엑셀 업로드 방식'</b>을 선택해 저장한 엑셀을 업로드합니다.</li>
</ol>
""",
    "6. 통합 데이터 및 연말결산 요약표": """
<h2>연간 신고데이터 통합 열람</h2>
<p>외부 실사, 감사, 근로복지공단 보수총액 신고 및 매 연말정산 대비를 위해 기관의 1년치 금전 지급 이력을 관장하는 아카이브 탭입니다.</p>
<hr>
<h3>연도별 종합 필터링 통계</h3>
<p>검색하고자 하는 특정 회계 <b>연도</b>(예: 2026년)를 상단에서 드랍다운 방식으로 선택하십시오. 1월 1일부터 12월 31일까지 귀속된 기관 전체의 횡단면 데이터가 강사별 1개 행으로 누적 합산되어 리스트 업 됩니다.</p>

<ul>
<li><b>지급 총액 확인:</b> 강사별로 올 한 해 센터에서 수령하신 강사료의 총 파이를 한눈에 직관적으로 조회할 수 있습니다. </li>
<li><b>총 세액 파악:</b> 빨간색 조화로 명기된 합산 소득세와 지방세를 통해 센터 차원에서 납부 보류 및 환급해야 할 누적 자금 한도를 확인할 수 있습니다.</li>
<li><b>연말정산 연동 준비:</b> 상단에 마련된 '연말정산 엑셀 다운로드' 버튼은, 본 데이터베이스를 세무사 사무실 또는 상급 기관 제출용으로 가장 예쁘게 포장하여 내보내는 역할을 수행합니다.</li>
</ul>
"""
}

class HelpTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # Title and Search Bar
        header_layout = QHBoxLayout()
        lbl_title = QLabel("사용자 통합 매뉴얼")
        lbl_title.setFont(QFont('Pretendard', 24, QFont.Bold))
        lbl_title.setStyleSheet("color: #0F172A;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색어를 입력하세요 (예: 강사, 홈택스 등)")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 12px;
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
        """)
        self.search_input.setFixedWidth(350)
        self.search_input.textChanged.connect(self._filter_articles)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.search_input)

        main_layout.addLayout(header_layout)

        # Splitter Layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #E2E8F0;
                width: 1px;
            }
        """)

        # Left: Category List
        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont('Pretendard', 12))
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                background-color: white;
                padding: 10px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 12px;
                color: #1E293B;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: #F8FAFC;
            }}
            QListWidget::item:selected {{
                background-color: #E0E7FF;
                color: {Colors.PRIMARY};
                font-weight: bold;
            }}
        """)
        self.list_widget.itemSelectionChanged.connect(self._on_item_selected)

        # Right: Content Browser
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet(f"""
            QTextBrowser {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                background-color: white;
                padding: 24px;
                color: #334155;
                font-size: 14px;
                line-height: 1.6;
            }}
        """)

        # Add initial items
        for title in HELP_ARTICLES.keys():
            self.list_widget.addItem(title)

        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.text_browser)
        splitter.setSizes([250, 600])

        main_layout.addWidget(splitter)
        
        # Select first item by default
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _filter_articles(self, text):
        search_text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            title = item.text()
            content = HELP_ARTICLES.get(title, "")
            
            if search_text in title.lower() or search_text in content.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _on_item_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
            
        title = selected_items[0].text()
        content = HELP_ARTICLES.get(title, "")
        
        # We wrap HTML slightly for base styling inside QTextBrowser
        html_styled = f"""
        <style>
            h2 {{ color: #0F172A; margin-bottom: 12px; font-size: 22px; }}
            h3 {{ color: #1E293B; margin-top: 20px; font-size: 16px; margin-bottom: 8px; }}
            p, li {{ color: #475569; font-size: 14px; line-height: 1.6; }}
            b {{ color: #0F172A; }}
            hr {{ border: 0; border-top: 1px solid #E2E8F0; margin: 16px 0; }}
            ol, ul {{ margin-top: 8px; margin-bottom: 16px; }}
            li {{ margin-bottom: 6px; }}
        </style>
        {content}
        """
        self.text_browser.setHtml(html_styled)
