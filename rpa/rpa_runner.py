"""
AutoTax — RPA 오케스트레이터 (실제 구현)
login → 메뉴 이동 → upload 파이프라인.
로그인 세션 재사용 지원 (storage_state).
"""
import asyncio
import json
import logging
import os

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# 세션 파일 경로 (재로그인 방지)
SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           '.hometax_session')
SESSION_FILE = os.path.join(SESSION_DIR, 'state.json')


class RPARunner:
    """
    RPA 실행 관리자.
    1. Playwright → Chromium (headless=False)
    2. 세션 파일이 있으면 재사용 시도
    3. HometaxLogin 으로 로그인
    4. HometaxUploader 로 엑셀 업로드
    5. 사용자에게 제출 확인 안내
    6. 브라우저 열어둠 (사용자가 확인/제출)
    """

    def __init__(self, auth_method: str = 'certificate',
                 cert_path: str = '', cert_password: str = '',
                 cert_location: str = 'harddisk', cert_keyword: str = '',
                 excel_path: str = ''):
        self.auth_method = auth_method
        self.cert_path = cert_path
        self.cert_password = cert_password
        self.cert_location = cert_location
        self.cert_keyword = cert_keyword
        self.excel_path = excel_path
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """진행 콜백: callback(step, total, message)"""
        self._progress_callback = callback

    def _emit(self, step: int, total: int, message: str):
        if self._progress_callback:
            self._progress_callback(step, total, message)
        logger.info(f'[RPA {step}/{total}] {message}')

    async def run(self) -> dict:
        """
        RPA 전체 파이프라인 실행.
        Returns: {'success': bool, 'message': str}
        """
        result = {'success': False, 'message': ''}

        if not self.excel_path or not os.path.exists(self.excel_path):
            result['message'] = f'엑셀 파일을 찾을 수 없습니다: {self.excel_path}'
            return result

        try:
            self._emit(1, 10, 'Playwright 브라우저 시작 중...')

            async with async_playwright() as pw:
                # Chromium 실행 (headless=False — 사용자가 화면 확인)
                browser = await pw.chromium.launch(
                    headless=False,
                    slow_mo=300,  # 안정성을 위한 딜레이
                    args=[
                        '--start-maximized',
                        '--disable-blink-features=AutomationControlled',
                    ],
                )

                # 세션 복원 시도
                context = await self._create_context(browser)
                page = await context.new_page()

                # ── 1단계: 로그인 ──
                self._emit(2, 10, '홈택스 로그인 시작...')

                from rpa.hometax_login import HometaxLogin
                login_handler = HometaxLogin(
                    page,
                    auth_method=self.auth_method,
                    cert_password=self.cert_password,
                    cert_location=self.cert_location,
                    cert_keyword=self.cert_keyword,
                )

                def login_progress(step, total, msg):
                    # 로그인은 step 2~5 범위
                    mapped_step = 2 + int(step * 3 / total)
                    self._emit(mapped_step, 10, f'[로그인] {msg}')

                login_success = await login_handler.login(progress_callback=login_progress)

                if not login_success:
                    result['message'] = (
                        '홈택스 로그인에 실패했습니다.\n'
                        '인증서를 선택하지 않았거나 시간이 초과되었을 수 있습니다.\n'
                        '다시 시도해주세요.'
                    )
                    # 브라우저는 열어둠 — 사용자가 수동 로그인 가능
                    self._emit(10, 10, '❌ 로그인 실패 — 브라우저를 닫지 않고 유지')
                    await self._keep_browser_open(page, browser)
                    return result

                # 로그인 성공 → 세션 저장
                await self._save_session(context)

                # ── 2단계: 엑셀 업로드 ──
                self._emit(6, 10, '간이지급명세서 업로드 시작...')

                from rpa.hometax_uploader import HometaxUploader
                uploader = HometaxUploader(page)

                def upload_progress(step, total, msg):
                    mapped_step = 6 + int(step * 3 / total)
                    self._emit(mapped_step, 10, f'[업로드] {msg}')

                upload_success = await uploader.upload_excel(
                    self.excel_path,
                    progress_callback=upload_progress,
                )

                if upload_success:
                    result['success'] = True
                    result['message'] = (
                        '✅ 엑셀 업로드 완료!\n\n'
                        '⚠️ 중요:\n'
                        '1. 홈택스 화면에서 오류가 없는지 확인하세요.\n'
                        '2. 확인 후 [제출] 버튼을 직접 클릭하세요.\n'
                        '3. 제출 후 접수증을 다운로드/보관하세요.\n\n'
                        '브라우저를 닫지 마세요!'
                    )
                else:
                    result['message'] = (
                        '엑셀 업로드 과정에서 문제가 발생했습니다.\n'
                        '브라우저 화면을 확인하고 수동으로 진행해주세요.'
                    )

                self._emit(10, 10, '완료 — 브라우저에서 확인 후 제출하세요')
                await self._keep_browser_open(page, browser)

        except Exception as e:
            logger.error(f'RPA 실행 오류: {e}')
            result['message'] = f'RPA 실행 중 오류가 발생했습니다:\n{str(e)}'

        return result

    async def _create_context(self, browser):
        """브라우저 컨텍스트 생성 (세션 복원 포함)"""
        context_opts = {
            'viewport': {'width': 1280, 'height': 900},
            'locale': 'ko-KR',
            'timezone_id': 'Asia/Seoul',
        }

        # 저장된 세션 파일이 있으면 복원 시도
        if os.path.exists(SESSION_FILE):
            try:
                context_opts['storage_state'] = SESSION_FILE
                logger.info('이전 세션 복원 시도 중...')
            except Exception:
                logger.warning('세션 복원 실패 — 새 세션 사용')

        return await browser.new_context(**context_opts)

    async def _save_session(self, context):
        """로그인 세션 저장 (다음 실행 시 재사용)"""
        try:
            os.makedirs(SESSION_DIR, exist_ok=True)
            await context.storage_state(path=SESSION_FILE)
            logger.info(f'세션 저장 완료: {SESSION_FILE}')
        except Exception as e:
            logger.warning(f'세션 저장 실패: {e}')

    async def _keep_browser_open(self, page, browser):
        """브라우저를 열어둔 채 사용자 확인 대기 (5분)"""
        try:
            await page.wait_for_timeout(300_000)  # 5분
        except Exception:
            pass
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    def run_sync(self) -> dict:
        """동기 래퍼 (GUI 스레드에서 호출용)"""
        return asyncio.run(self.run())
