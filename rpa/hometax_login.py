"""
AutoTax — 홈택스 로그인 (F12 검증 완료 셀렉터)
2026-03-17 사용자 F12 확인 기반.

인증 탭 셀렉터 (검증 완료):
  1. 공동·금융 인증    → #mf_txppWframe_anchor13  (data-tab=login_tab1)
  2. 간편 인증          → #mf_txppWframe_anchor14  (data-tab=login_tab2)
  3. 모바일신분증       → #mf_txppWframe_anchor16  (data-tab=login_tab6)
  4. 아이디 로그인      → (4번째 탭 — 사용자 확인 필요)
  5. 생체(얼굴·지문)   → #mf_txppWframe_anchor17  (data-tab=login_tab4)
  6. 비회원 로그인      → #mf_txppWframe_anchor19  (data-tab=login_tab5)

실행 버튼: #mf_txppWframe_anchor22 (탭에 따라 텍스트 변경)
팝업 닫기: #mf_wq_uuid_35 이미지 팝업 → X 버튼 클릭
권한 요청: 'hometax.go.kr에서 다음 권한을 요청합니다' → '허용' 클릭
"""
import logging

logger = logging.getLogger(__name__)

# 인증 방법별 셀렉터 매핑
AUTH_METHODS = {
    'certificate': {
        'tab_id': '#mf_txppWframe_anchor13',
        'label': '공동·금융인증서',
    },
    'simple': {
        'tab_id': '#mf_txppWframe_anchor14',
        'label': '간편인증(민간인증서)',
    },
    'mobile_id': {
        'tab_id': '#mf_txppWframe_anchor16',
        'label': '모바일신분증',
    },
    'bio': {
        'tab_id': '#mf_txppWframe_anchor17',
        'label': '생체(얼굴·지문)인증',
    },
    'non_member': {
        'tab_id': '#mf_txppWframe_anchor19',
        'label': '비회원 로그인',
    },
}

# 실행 버튼 (탭 선택 후 누르는 파란색 버튼)
ACTION_BUTTON = '#mf_txppWframe_anchor22'


class HometaxLogin:
    """
    홈택스 자동 로그인.
    headless=False — 사용자가 인증서 팝업을 직접 처리.

    흐름:
      1. 홈택스 접속
      2. 로그인 페이지 이동
      3. 인증 방식 탭 클릭
      4. 실행 버튼(파란 버튼) 클릭
      5. 팝업 이미지 닫기 (X)
      6. 브라우저 권한 '허용' 클릭
      7. 사용자가 인증서 선택/비밀번호 입력
      8. 로그인 완료 폴링
    """

    HOMETAX_MAIN = 'https://hometax.go.kr'
    LOGIN_URL = ('https://hometax.go.kr/websquare/websquare.html'
                 '?w2xPath=/ui/pp/index_pp.xml&menuCd=index3')

    def __init__(self, page, auth_method: str = 'certificate'):
        self.page = page
        self.auth_method = auth_method
        self.is_logged_in = False

    async def login(self, progress_callback=None) -> bool:
        total = 7
        try:
            # ── 1: 홈택스 접속 ──
            self._emit(progress_callback, 1, total, '홈택스 접속 중...')
            await self.page.goto(self.HOMETAX_MAIN,
                                 wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_timeout(4000)

            # ── 2: 로그인 페이지 이동 ──
            self._emit(progress_callback, 2, total, '로그인 페이지로 이동...')
            await self._go_to_login()
            await self.page.wait_for_timeout(3000)

            # ── 3: 인증 탭 선택 ──
            method_info = AUTH_METHODS.get(self.auth_method, AUTH_METHODS['certificate'])
            self._emit(progress_callback, 3, total,
                       f'[{method_info["label"]}] 탭 선택 중...')
            await self._click_auth_tab(method_info['tab_id'])
            await self.page.wait_for_timeout(1500)

            # ── 4: 실행 버튼(파란 버튼) 클릭 ──
            self._emit(progress_callback, 4, total,
                       f'[{method_info["label"]}] 실행 버튼 클릭...')
            await self._click_action_button()
            await self.page.wait_for_timeout(2000)

            # ── 5: 팝업 닫기 + 권한 허용 ──
            self._emit(progress_callback, 5, total,
                       '팝업 닫기 및 권한 허용 처리 중...')
            await self._handle_popups()
            await self.page.wait_for_timeout(2000)

            # ── 6: 사용자 인증 대기 ──
            self._emit(progress_callback, 6, total,
                       '⏳ 인증서 선택/비밀번호 입력을 완료해주세요... (3분 대기)')
            logged_in = await self._wait_for_login(timeout_sec=180)

            # ── 7: 결과 ──
            if logged_in:
                self.is_logged_in = True
                self._emit(progress_callback, 7, total, '✅ 로그인 성공!')
                return True
            else:
                self._emit(progress_callback, 7, total, '❌ 로그인 시간 초과 (3분)')
                return False

        except Exception as e:
            logger.error(f'홈택스 로그인 오류: {e}')
            self._emit(progress_callback, total, total, f'오류: {str(e)[:60]}')
            return False

    async def _go_to_login(self):
        """로그인 페이지 이동"""
        try:
            btn = self.page.locator('#mf_wfHeader_group1503')
            if await btn.is_visible(timeout=5000):
                await btn.click()
                logger.info('로그인 버튼 클릭')
                return
        except Exception:
            pass
        # Fallback: URL 직접
        await self.page.goto(self.LOGIN_URL,
                             wait_until='domcontentloaded', timeout=30000)

    async def _click_auth_tab(self, tab_selector: str):
        """인증 방식 탭 클릭 (F12 검증 ID)"""
        try:
            tab = self.page.locator(tab_selector)
            if await tab.is_visible(timeout=5000):
                await tab.click()
                logger.info(f'인증 탭 클릭: {tab_selector}')
                return
        except Exception:
            pass

        # Fallback: JS click
        try:
            tab_id = tab_selector.lstrip('#')
            await self.page.evaluate(f'''() => {{
                const el = document.getElementById("{tab_id}");
                if (el) el.click();
            }}''')
            logger.info(f'인증 탭 JS 클릭: {tab_selector}')
        except Exception as e:
            logger.warning(f'인증 탭 클릭 실패: {e}')

    async def _click_action_button(self):
        """파란색 실행 버튼 클릭 (#mf_txppWframe_anchor22)"""
        try:
            btn = self.page.locator(ACTION_BUTTON)
            if await btn.is_visible(timeout=5000):
                await btn.click()
                logger.info('실행 버튼 클릭')
                return
        except Exception:
            pass

        # Fallback: JS click
        try:
            await self.page.evaluate('''() => {
                const el = document.getElementById("mf_txppWframe_anchor22");
                if (el) el.click();
            }''')
            logger.info('실행 버튼 JS 클릭')
        except Exception as e:
            logger.warning(f'실행 버튼 클릭 실패: {e}')

    async def _handle_popups(self):
        """
        팝업 처리:
        1. 크롬/엣지 안내 이미지 팝업 → X 버튼으로 닫기
        2. 브라우저 권한 요청 → '허용' 클릭
        """
        # ── 1. 이미지 팝업 닫기 ──
        # #mf_wq_uuid_35 이미지 팝업의 X 버튼
        try:
            # 팝업 닫기 X 버튼 (이미지 팝업 상단의 닫기 버튼)
            close_selectors = [
                'button:has-text("닫기")',
                'a:has-text("닫기")',
                'button.close',
                '[class*="close"]',
                'img#mf_wq_uuid_35 ~ button',
                'text=닫기',
                # X 버튼 텍스트
                'button:has-text("×")',
                'a:has-text("×")',
            ]
            for sel in close_selectors:
                try:
                    loc = self.page.locator(sel).first
                    if await loc.is_visible(timeout=1500):
                        await loc.click()
                        logger.info(f'팝업 닫기: {sel}')
                        await self.page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f'팝업 닫기 시도 중 오류: {e}')

        # ── 2. 브라우저 권한 '허용' 클릭 ──
        # Chromium 권한 요청(로컬 네트워크 접근 등) → 자동 허용
        try:
            # Playwright는 브라우저 팝업을 page.on('dialog')로 처리 가능
            # 하지만 권한 요청은 dialog가 아닌 브라우저 UI이므로
            # context의 grant_permissions 또는 CDP로 처리
            await self.page.context.grant_permissions(['notifications'],
                                                       origin='https://hometax.go.kr')
        except Exception:
            pass

        # 페이지 내 '허용' 버튼 (혹시 페이지 내 요소인 경우)
        try:
            allow_btn = self.page.get_by_text('허용', exact=True).first
            if await allow_btn.is_visible(timeout=2000):
                await allow_btn.click()
                logger.info('허용 버튼 클릭')
        except Exception:
            pass

    async def _wait_for_login(self, timeout_sec: int = 180) -> bool:
        """로그인 완료 폴링"""
        poll = 3
        elapsed = 0
        while elapsed < timeout_sec:
            for sel in ['text=로그아웃', 'a:has-text("로그아웃")',
                        'text=마이홈택스']:
                try:
                    if await self.page.locator(sel).first.is_visible(timeout=500):
                        logger.info(f'로그인 확인: {sel}')
                        return True
                except Exception:
                    continue
            await self.page.wait_for_timeout(poll * 1000)
            elapsed += poll
        return False

    @staticmethod
    def _emit(cb, step, total, msg):
        if cb:
            cb(step, total, msg)
