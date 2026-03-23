"""
AutoTax — 홈택스 엑셀 업로더 (2차 검증 반영)
핵심 수정: GNB 메뉴는 hover 필요, dispatchEvent/click({force:true}) 적용.
"""
import os
import logging

logger = logging.getLogger(__name__)


class HometaxUploader:
    """
    홈택스 간이지급명세서(사업소득) 엑셀 업로드.
    로그인 완료 후 호출.

    검증된 메뉴 경로:
      GNB: "지급명세·자료·공익법인" → #mf_wfHeader_wq_uuid_438 (hover 필요)
      2depth: LI #mf_wfHeader_hdGroup918 (부모)
      3depth: "직접작성 제출" → #menuAtag_4401100000
    """

    MAIN_URL = 'https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml'

    def __init__(self, page):
        self.page = page

    async def upload_excel(self, excel_path: str, progress_callback=None) -> bool:
        if not os.path.exists(excel_path):
            self._emit(progress_callback, 1, 5, f'❌ 파일 없음: {excel_path}')
            return False

        total = 5
        try:
            # ── 1: 메인 페이지로 이동 (로그인 후 리다이렉트 대응) ──
            self._emit(progress_callback, 1, total,
                       '홈택스 메인 페이지로 이동...')
            await self.page.goto(self.MAIN_URL,
                                 wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_timeout(3000)

            # ── 2: GNB 메뉴 → 직접작성 제출 ──
            self._emit(progress_callback, 2, total,
                       '[지급명세·자료·공익법인] → [직접작성 제출]...')
            await self._navigate_to_direct_submit()

            # ── 3: 간이지급명세서(거주자의 사업소득) 선택 ──
            self._emit(progress_callback, 3, total,
                       '[간이지급명세서(거주자의 사업소득)] 선택 중...')
            await self._select_income_type()

            # ── 4: 상세내역 작성하기 버튼 대기 및 클릭 ──
            self._emit(progress_callback, 4, total,
                       '원천징수의무자 확인 과정 대기 및 [상세내역 작성하기] 클릭...')
            await self._click_write_details()

            # ── 5: 완료 ──
            self._emit(progress_callback, 5, total,
                       '✅ 폼 진입 완료! 사업소득자 상세내역을 개별 작성해 주세요.')
            return True

        except Exception as e:
            logger.error(f'홈택스 업로드 실패: {e}')
            self._emit(progress_callback, total, total, f'❌ 오류: {str(e)[:80]}')
            return False

    async def _navigate_to_direct_submit(self):
        """
        GNB 메뉴 이동: 지급명세 → 직접작성 제출.
        GNB 드롭다운은 hover로 나타나므로 hover → click 순서.
        """
        success = False

        # ─── 방법 1: GNB hover → 하위메뉴 클릭 ───
        try:
            # 1depth: "지급명세·자료·공익법인" 부모 LI에 hover
            gnb_parent = self.page.locator('#mf_wfHeader_hdGroup918')
            gnb_link = self.page.locator('#mf_wfHeader_wq_uuid_438')

            # hover로 드롭다운 활성화
            await gnb_parent.hover(timeout=5000)
            await self.page.wait_for_timeout(1000)

            # 텍스트로도 시도
            if not await gnb_link.is_visible(timeout=1000):
                gnb_link = self.page.locator('a:has-text("지급명세·자료·공익법인")').first

            await gnb_link.hover()
            await self.page.wait_for_timeout(1000)

            # "직접작성 제출" 하위 메뉴 클릭
            direct = self.page.locator('#menuAtag_4401100000')
            if await direct.is_visible(timeout=3000):
                await direct.click()
                await self.page.wait_for_timeout(3000)
                logger.info('GNB hover → 직접작성 제출 클릭 성공')
                success = True
        except Exception as e:
            logger.debug(f'GNB hover 방식 실패: {e}')

        # ─── 방법 2: JavaScript로 강제 클릭 ───
        if not success:
            try:
                await self.page.evaluate('''() => {
                    const el = document.getElementById('menuAtag_4401100000');
                    if (el) { el.click(); return true; }
                    return false;
                }''')
                await self.page.wait_for_timeout(3000)
                logger.info('JS 강제 클릭으로 직접작성 제출 이동')
                success = True
            except Exception as e:
                logger.debug(f'JS 클릭 실패: {e}')

        # ─── 방법 3: force click (Playwright) ───
        if not success:
            try:
                direct = self.page.locator('#menuAtag_4401100000')
                await direct.click(force=True, timeout=5000)
                await self.page.wait_for_timeout(3000)
                logger.info('force click으로 직접작성 제출 이동')
                success = True
            except Exception as e:
                logger.debug(f'force click 실패: {e}')

        # ─── 방법 4: 전체메뉴 경유 ───
        if not success:
            try:
                await self.page.locator('#mf_wfHeader_hdGroup005').click()
                await self.page.wait_for_timeout(2000)

                tab = self.page.locator(
                    '#mf_wfHeader_UTXPPBAD22_wframe_wq_uuid_989_tab_tabs5_tabHTML')
                if await tab.is_visible(timeout=3000):
                    await tab.click()
                    await self.page.wait_for_timeout(2000)
                    logger.info('전체메뉴 → 지급명세 탭 경유')
                    success = True
            except Exception as e:
                logger.debug(f'전체메뉴 경유 실패: {e}')

        if not success:
            logger.warning('모든 메뉴 이동 방법 실패')

    async def _select_income_type(self):
        """직접작성 제출 페이지 내 간이지급명세서(거주자의 사업소득) 선택"""
        # 1. 지급명세서 선택 Dropdown — 정확한 ID: mf_txppWframe_mateKndCd
        try:
            select_box = self.page.locator('#mf_txppWframe_mateKndCd')
            
            if await select_box.is_visible(timeout=10000):
                # select_option으로 label 기반 선택
                await select_box.select_option(label='간이지급명세서(거주자의 사업소득)')
                logger.info('[지급명세서 선택] 간이지급명세서(거주자의 사업소득) 선택 완료')
                await self.page.wait_for_timeout(2000)
            else:
                # JS fallback: WebSquare 커스텀 셀렉트박스일 수 있으므로 JS로 값 변경 시도
                logger.warning('select_option 실패 — JS로 값 세팅 시도')
                await self.page.evaluate('''() => {
                    const sel = document.getElementById('mf_txppWframe_mateKndCd');
                    if (sel) {
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].text.includes('거주자의 사업소득')) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                break;
                            }
                        }
                    }
                }''')
                await self.page.wait_for_timeout(2000)
                logger.info('[JS fallback] 간이지급명세서(거주자의 사업소득) 선택 시도 완료')
        except Exception as e:
            logger.warning(f'지급명세서 드롭다운 선택 실패: {e}')

    async def _click_write_details(self):
        """상세내역 작성하기 버튼 클릭 후, 나타나는 팝업/폼 내용을 캡처"""
        try:
            btn = self.page.locator('#mf_txppWframe_btnDpclWrt')
            
            logger.info("상세내역 작성하기 버튼 클릭 시도!")
            if await btn.is_visible(timeout=5000):
                await btn.click(force=True)
                logger.info("상세내역 작성하기 버튼 클릭 완료! 팝업/폼 로딩 대기...")
                await self.page.wait_for_timeout(5000)
            else:
                logger.warning("상세내역 작성하기 버튼이 보이지 않습니다.")
                return
            
            # 버튼 클릭 후 나타나는 팝업(작성 중 데이터 있음/전월 불러오기 등) + 폼 내용을 캡처
            try:
                dump_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'popup_inspection_result.txt')
                
                # 1. 팝업/모달 다이얼로그 캡처 (w2window, w2alert, confirm 등)
                popup_html = await self.page.evaluate('''() => {
                    const popups = Array.from(document.querySelectorAll(
                        '.w2window, .w2alert, .w2confirm, [class*="popup"], [class*="modal"], [class*="dialog"], [role="dialog"], [role="alertdialog"]'
                    ));
                    // 보이는 팝업만 수집
                    const visible = popups.filter(el => {
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    });
                    return visible.map(el => el.outerHTML).join('\n--- POPUP SEPARATOR ---\n');
                }''')
                
                # 2. 페이지 전체에서 보이는 버튼/입력칸 캡처
                form_html = await self.page.evaluate('''() => {
                    const els = Array.from(document.querySelectorAll('input, select, button, textarea'));
                    const visible = els.filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    });
                    return visible.map(el => el.outerHTML.replace(/\\s+/g, ' ')).join('\n');
                }''')
                
                with open(dump_path, 'w', encoding='utf-8') as f:
                    f.write("=== POPUP/MODAL (상세내역 작성하기 클릭 후 나타난 팝업) ===\n")
                    f.write(popup_html if popup_html else "(팝업 없음)")
                    f.write("\n\n=== VISIBLE FORM ELEMENTS (화면에 보이는 입력칸/버튼) ===\n")
                    f.write(form_html)
                
                logger.info(f"클릭 후 화면 상태를 '{dump_path}'에 저장했습니다.")
            except Exception as inner_e:
                logger.debug(f"HTML 덤프 실패: {inner_e}")

        except Exception as e:
            logger.warning(f'상세내역 작성하기 버튼 제어 중 오류 발생: {e}')

    async def _try_click(self, selectors: list, label: str) -> bool:
        for sel in selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.is_visible(timeout=2000):
                    await loc.click()
                    logger.info(f'[{label}] 클릭: {sel}')
                    return True
            except Exception:
                continue
        logger.warning(f'[{label}] 클릭 실패')
        return False

    @staticmethod
    def _emit(cb, step, total, msg):
        if cb:
            cb(step, total, msg)
