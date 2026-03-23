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

    def __init__(self, page, auth_method: str = 'certificate', cert_keyword: str = '', cert_drive: str = 'C', cert_password: str = ''):
        self.page = page
        self.auth_method = auth_method
        self.cert_keyword = cert_keyword
        self.cert_drive = cert_drive
        self.cert_password = cert_password
        self.is_logged_in = False

    async def login(self, progress_callback=None) -> bool:
        total = 7
        try:
            # ── 1: 홈택스 메인 접속 ──
            self._emit(progress_callback, 1, total, '홈택스 메인 페이지 접속 중...')
            await self.page.goto(self.HOMETAX_MAIN,
                                 wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_timeout(5000)

            # ── 2: 로그인 페이지 이동 (메인 → 로그인 클릭) ──
            self._emit(progress_callback, 2, total, '로그인 페이지로 이동...')
            await self._go_to_login()
            await self.page.wait_for_timeout(5000)

            # ── 3: 인증 탭 선택 (설정된 인증 방식) ──
            method_info = AUTH_METHODS.get(self.auth_method, AUTH_METHODS['certificate'])
            self._emit(progress_callback, 3, total,
                       f'[{method_info["label"]}] 탭 선택 중...')
            await self._click_auth_tab(method_info['tab_id'])
            await self.page.wait_for_timeout(1500)

            # ── 4: 실행 버튼(파란 버튼) 클릭 ──
            self._emit(progress_callback, 4, total,
                       f'[{method_info["label"]}] 인증 실행 버튼 클릭...')
            await self._click_action_button()
            await self.page.wait_for_timeout(2000)

            # ── 5: 방해되는 팝업창 정리 ──
            self._emit(progress_callback, 5, total, '불필요한 팝업창 정리 중...')
            await self._handle_popups()

            # ── 6: 웹 기반 공동인증서 팝업 자동 제어 (해당 시) ──
            if self.auth_method == 'certificate':
                self._emit(progress_callback, 6, total, '웹 공동인증서 팝업을 대기하고 비밀번호를 입력합니다...')
                await self._handle_web_certificate()
            else:
                self._emit(progress_callback, 6, total,
                           f'⏳ [{method_info["label"]}] 화면에서 직접 인증을 완료해주세요... (최대 3분 대기)')
            
            # 여기서 사용자가 직접 간편인증을 하거나, 위에서 자동 입력된 공동인증서 로그인이 완료될 때까지 대기
            logged_in = await self._wait_for_login(timeout_sec=180)

            # ── 7: 로그인 결과 처리 ──
            if logged_in:
                self.is_logged_in = True
                self._emit(progress_callback, 7, total, '✅ 로그인 성공!')
                return True
            else:
                self._emit(progress_callback, 7, total, '❌ 로그인 시간 초과')
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
            # 15초 정도 충분히 대기 (보안 모듈/JS 로딩 지연 대비)
            if await tab.is_visible(timeout=15000):
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
        # ── 1. 별도 팝업 창(새 창) 닫기 ──
        try:
            pages = self.page.context.pages
            for p in pages:
                if p != self.page:  # 메인 페이지가 아닌 경우
                    try:
                        title = await p.title()
                        # 팝업 제목 키워드 확인
                        if any(kw in title for kw in ['팝업', '안내', '공지', 'NOTICE']):
                            logger.info(f'새 창 팝업 발견 및 닫기: {title}')
                            
                            # '오늘 더 이상 보지 않음' 있으면 클릭 시도
                            try:
                                checkbox = p.get_by_text('보지 않음')
                                if await checkbox.is_visible(timeout=500):
                                    await checkbox.click()
                                    await p.wait_for_timeout(300)
                            except Exception:
                                pass

                            await p.close()
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f'별도 창 닫기 중 오류: {e}')

        # ── 2. 레이어(페이지 내) 팝업 닫기 ──
        try:
            # 보강된 셀렉터 목록
            close_selectors = [
                '#mf_wq_uuid_35 ~ button',
                '.w2window_close',
                'button:has-text("닫기")',
                'a:has-text("닫기")',
                '.close',
                'img[alt="닫기"]',
                'text=오늘은 더 이상 이 창을 띄우지 않음',
                'button:has-text("×")',
                'a:has-text("×")',
                'span:has-text("×")',
            ]
            
            # 모든 'X' 모양 버튼이나 닫기 버튼을 찾아서 클릭
            for sel in close_selectors:
                try:
                    locs = self.page.locator(sel)
                    count = await locs.count()
                    for i in range(count):
                        loc = locs.nth(i)
                        if await loc.is_visible(timeout=1000):
                            await loc.click()
                            logger.info(f'레이어 팝업 닫기: {sel}')
                            await self.page.wait_for_timeout(500)
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f'레이어 팝업 닫기 중 오류: {e}')

        # ── 4. 보안 프로그램 권한 '허용' 클릭 ──
        try:
            await self.page.context.grant_permissions(['notifications'],
                                                       origin='https://hometax.go.kr')
        except Exception:
            pass

    async def _open_dropdown_and_select(self, target_frame, target_drive_text: str, max_attempts: int = 3) -> bool:
        """
        #stg_hdd 탭 클릭 → 드롭다운 열림 확인 → target_drive_text 클릭.
        """
        for attempt in range(1, max_attempts + 1):
            logger.info(f"--- 드라이브 선택 시도 {attempt}/{max_attempts}: '{target_drive_text}' ---")
            
            # 1) #stg_hdd 탭 클릭 → 드롭다운 열기
            stg_hdd = target_frame.locator('#stg_hdd')
            try:
                await stg_hdd.wait_for(state='visible', timeout=5000)
                await stg_hdd.click()
                logger.info("#stg_hdd 탭 클릭, 드롭다운 대기...")
            except Exception as e:
                logger.warning(f"시도 {attempt}: #stg_hdd 클릭 실패: {e}")
                await target_frame.wait_for_timeout(1000)
                continue

            # 2) 드롭다운이 열릴 때까지 대기 (최대 3초)
            dropdown_ready = False
            for _ in range(6):
                await target_frame.wait_for_timeout(500)
                try:
                    # get_by_text(exact=True)로 정확한 요소만 찾기
                    loc = target_frame.get_by_text(target_drive_text, exact=True).first
                    if await loc.is_visible(timeout=300):
                        dropdown_ready = True
                        logger.info(f"드롭다운 열림 확인: '{target_drive_text}' 발견")
                        break
                except Exception:
                    pass

            # 드롭다운 안 보이면: 토글 시도 (이미 열려서 닫힌 상태일 수 있음)
            if not dropdown_ready:
                logger.warning(f"시도 {attempt}: 드롭다운에서 '{target_drive_text}' 안 보임, 토글 재시도")
                try:
                    await stg_hdd.click()
                    await target_frame.wait_for_timeout(1500)
                    loc = target_frame.get_by_text(target_drive_text, exact=True).first
                    if await loc.is_visible(timeout=1500):
                        dropdown_ready = True
                        logger.info(f"토글 후 드롭다운 열림 확인")
                except Exception:
                    pass
            
            if not dropdown_ready:
                logger.warning(f"시도 {attempt}: 드롭다운 열림 실패, 재시도...")
                await target_frame.wait_for_timeout(500)
                continue

            # 3) 드롭다운 항목 클릭 — get_by_text(exact=True) 사용
            try:
                item = target_frame.get_by_text(target_drive_text, exact=True).first
                await item.click()
                await target_frame.wait_for_timeout(2000)
                logger.info(f"✔ get_by_text '{target_drive_text}' 클릭 성공!")
                return True
            except Exception as e:
                logger.warning(f"시도 {attempt}: get_by_text 클릭 실패: {e}")

            # 4) 폴백: JavaScript — innermost(가장 짧은 텍스트) 요소 클릭
            try:
                js_result = await target_frame.evaluate(f'''() => {{
                    const target = '{target_drive_text}';
                    const all = document.querySelectorAll('a, li, div, span, option, button, p, td');
                    let bestEl = null;
                    let bestLen = 99999;
                    
                    for (const el of all) {{
                        if (el.id === 'stg_hdd') continue;
                        if (el.closest && el.closest('#stg_hdd')) continue;
                        if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;
                        
                        const txt = (el.textContent || '').trim();
                        if (txt.includes(target) && txt.length < bestLen) {{
                            bestEl = el;
                            bestLen = txt.length;
                        }}
                    }}
                    
                    if (bestEl) {{
                        bestEl.click();
                        return 'clicked(len=' + bestLen + '): ' + bestEl.textContent.trim().substring(0, 30);
                    }}
                    return 'not_found';
                }}''')
                logger.info(f"JS 결과: {js_result}")
                if 'clicked' in js_result:
                    await target_frame.wait_for_timeout(2000)
                    return True
            except Exception as e:
                logger.debug(f"JS 선택 실패: {e}")

            logger.warning(f"시도 {attempt} 실패")
            await target_frame.wait_for_timeout(1000)

        logger.error(f"❌ {max_attempts}회 시도 모두 실패: '{target_drive_text}'")
        return False

    async def _handle_web_certificate(self):
        """
        웹 기반 공동인증서 팝업창 자동 제어.
        
        하드디스크/이동식디스크 완전 분리:
        - 하드디스크(C:) → #stg_hdd 클릭 → 드롭다운에서 "OS (C)" 명시적 클릭
        - 이동식(D: 등) → #stg_hdd 클릭 → 드롭다운에서 "이동식 디스크 (D)" 명시적 클릭
        """
        import time
        try:
            logger.info(f"웹 공동인증서 팝업 대기 중... (cert_drive={self.cert_drive}, cert_keyword={self.cert_keyword})")
            
            target_frame = None
            
            # ── 팝업 프레임 감지 (최대 30초) ──
            start_time = time.time()
            while time.time() - start_time < 30:
                for selector in ['#stg_hdd', '#input_cert_pw']:
                    try:
                        if await self.page.locator(selector).is_visible():
                            target_frame = self.page
                            break
                    except Exception:
                        continue
                if target_frame: break

                for frame in self.page.frames:
                    try:
                        for selector in ['#stg_hdd', '#input_cert_pw']:
                            if await frame.locator(selector).is_visible():
                                target_frame = frame
                                break
                        if target_frame: break
                    except Exception:
                        continue
                        
                if target_frame is not None:
                    break
                await self.page.wait_for_timeout(500)
                
            if target_frame is None:
                logger.error("웹 공동인증서 팝업을 30초 내에 찾지 못했습니다.")
                return

            # ══════════════════════════════════════════════
            # 매체(드라이브) 선택 — HDD / USB 완전 분리
            # ══════════════════════════════════════════════
            if self.cert_drive == 'C':
                # ── 경로 1: 하드디스크 (OS C:) ──
                logger.info("═══ 경로 1: 하드디스크(C:) 로그인 ═══")
                success = await self._open_dropdown_and_select(target_frame, 'OS (C)')
                if not success:
                    logger.error("하드디스크 선택 실패. OS(C) 항목을 찾지 못했습니다.")
            else:
                # ── 경로 2: 이동식디스크 (USB) ──
                drive_letter = self.cert_drive
                target_text = f'이동식 디스크 ({drive_letter})'
                logger.info(f"═══ 경로 2: 이동식디스크({drive_letter}:) 로그인 ═══")
                success = await self._open_dropdown_and_select(target_frame, target_text)
                if not success:
                    logger.error(f"이동식디스크 선택 실패. '{target_text}' 항목을 찾지 못했습니다.")

            # ── 인증서 목록에서 대상 검색 및 선택 ──
            if self.cert_keyword:
                logger.info(f"인증서 목록에서 '{self.cert_keyword}' 검색")
                search_kw = self.cert_keyword.split('(')[0].strip() if '(' in self.cert_keyword else self.cert_keyword.strip()
                
                await target_frame.wait_for_timeout(2000)
                
                cert_row = target_frame.locator(f'tr:has-text("{search_kw}")').first
                try:
                    await cert_row.wait_for(state='visible', timeout=5000)
                    await cert_row.click()
                    await target_frame.wait_for_timeout(500)
                    logger.info(f"✔ 인증서 '{search_kw}' 선택 완료")
                except Exception:
                    logger.error(f"❌ 인증서 목록에서 '{search_kw}'를 찾을 수 없습니다.")

            # ── 비밀번호 입력 ──
            pw_input = target_frame.locator('#input_cert_pw')
            
            if self.cert_password:
                logger.info("비밀번호 자동 기입 및 엔터키 전송")
                await pw_input.fill(self.cert_password, timeout=15000)
                await target_frame.wait_for_timeout(500)
                await pw_input.press('Enter')
                logger.info("✔ 공동인증서 자동 입력 및 로그인 요청 완료")
            else:
                logger.warning("저장된 비밀번호가 없습니다. 수동 입력을 대기합니다.")
                
        except Exception as e:
            logger.warning(f"웹 공동인증서 자동 제어 실패 (수동 입력 필요): {e}")

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
