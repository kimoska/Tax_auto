"""
AutoTax — 인증서 팝업 자동 제어 모듈
=====================================
MagicLine4NX (DREAM SECURITY) 기반의 '인증서 선택창'을 pywinauto로 자동 조작.

지원 흐름:
  1. 홈택스 로그인 → '인증하기' 클릭 후 인증서 팝업이 뜸
  2. 이 모듈이 팝업을 감지
  3. 인증서 저장 위치 탭 클릭 (하드디스크/이동식 등)
  4. 인증서 목록에서 원하는 인증서 선택
  5. 비밀번호 입력
  6. '확인' 버튼 클릭
"""
import logging
import time
import threading

logger = logging.getLogger(__name__)

try:
    from pywinauto import Desktop
    from pywinauto.application import Application
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    logger.warning('pywinauto가 설치되지 않았습니다. 인증서 팝업 자동화를 사용할 수 없습니다.')


# ── 인증서 저장 위치 매핑 ──
CERT_LOCATION_MAP = {
    'browser':    '브라우저',
    'financial':  '금융인증서',
    'harddisk':   '하드디스크',
    'removable':  '이동식',
    'mobile':     '휴대전화',
    'smart':      '스마트인증',
}

# ── 인증서 팝업 창을 찾기 위한 키워드 ──
POPUP_TITLE_KEYWORDS = [
    '인증서 선택',
    '인증서선택',
    'MagicLine',
    'DREAM',
]

# ── 팝업 클래스명 후보 ──
POPUP_CLASS_NAMES = [
    '#32770',  # 표준 Win32 Dialog
]


class CertPopupHandler:
    """
    인증서 팝업 자동 제어기.

    사용법:
        handler = CertPopupHandler(
            cert_password='mypassword',
            cert_location='harddisk',      # 또는 'removable', 'browser' 등
            cert_keyword='김관영',           # 인증서 목록에서 이 키워드가 포함된 인증서 선택
        )
        handler.start_watching()   # 백그라운드 스레드로 팝업 감시 시작
        # ... Playwright가 '인증하기' 버튼 클릭 ...
        success = handler.wait_for_completion(timeout=60)
    """

    def __init__(self, cert_password: str,
                 cert_location: str = 'harddisk',
                 cert_keyword: str = '',
                 progress_callback=None):
        """
        Args:
            cert_password: 인증서 비밀번호 (평문)
            cert_location: 인증서 저장 위치 키 (CERT_LOCATION_MAP의 키)
            cert_keyword: 인증서 목록에서 찾을 키워드 (소유자명의 일부)
            progress_callback: 진행 상황 콜백 (message: str)
        """
        self.cert_password = cert_password
        self.cert_location = cert_location
        self.cert_keyword = cert_keyword
        self._progress_callback = progress_callback

        self._completed = threading.Event()
        self._success = False
        self._error_message = ''
        self._watching = False
        self._thread = None

    def _emit(self, message: str):
        """진행 메시지 전달"""
        logger.info(f'[CertPopup] {message}')
        if self._progress_callback:
            try:
                self._progress_callback(message)
            except Exception:
                pass

    # ──────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────

    def start_watching(self):
        """백그라운드 스레드로 팝업 감시 시작"""
        if not PYWINAUTO_AVAILABLE:
            self._emit('❌ pywinauto 미설치 — 수동 인증 필요')
            return

        self._watching = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        self._emit('🔍 인증서 팝업 감시 시작...')

    def stop_watching(self):
        """감시 중단"""
        self._watching = False

    def wait_for_completion(self, timeout: int = 120) -> bool:
        """
        팝업 처리 완료 대기.
        Returns: True면 성공, False면 실패/타임아웃
        """
        self._completed.wait(timeout=timeout)
        self.stop_watching()
        return self._success

    @property
    def error_message(self) -> str:
        return self._error_message

    # ──────────────────────────────────────────
    # 내부: 팝업 감시 루프
    # ──────────────────────────────────────────

    def _watch_loop(self):
        """인증서 팝업이 나타날 때까지 반복 점검"""
        poll_interval = 1.0  # 1초 간격으로 확인
        max_wait = 120       # 최대 2분 대기

        elapsed = 0
        while self._watching and elapsed < max_wait:
            popup = self._find_cert_popup()
            if popup is not None:
                self._emit('✅ 인증서 팝업 발견! 자동 처리 시작...')
                try:
                    self._handle_popup(popup)
                    self._success = True
                    self._emit('✅ 인증서 인증 완료!')
                except Exception as e:
                    self._error_message = str(e)
                    self._emit(f'❌ 팝업 처리 실패: {e}')
                    self._success = False
                finally:
                    self._completed.set()
                return

            time.sleep(poll_interval)
            elapsed += poll_interval

        # 타임아웃
        if not self._completed.is_set():
            self._error_message = '인증서 팝업을 찾지 못했습니다 (시간 초과)'
            self._emit(f'⏰ {self._error_message}')
            self._completed.set()

    def _find_cert_popup(self):
        """
        현재 화면에서 인증서 팝업 창을 탐색.
        win32 백엔드 사용 (MagicLine4NX는 Win32 Dialog 기반).
        """
        for backend in ['win32', 'uia']:
            try:
                desktop = Desktop(backend=backend)
                windows = desktop.windows()

                for w in windows:
                    try:
                        title = w.window_text()
                        cls = w.class_name()

                        # 제목 기반 매칭
                        title_match = any(kw in title for kw in POPUP_TITLE_KEYWORDS)

                        # MagicLine4NX 전용 매칭 (제목이 정확히 'MagicLine4NX'인 경우)
                        magicline_match = 'MagicLine' in title

                        if title_match or magicline_match:
                            logger.info(f'팝업 후보 발견: title="{title}", class="{cls}", backend={backend}')

                            # 크기 확인 — 너무 작으면 알림 창이므로 제외
                            try:
                                rect = w.rectangle()
                                width = rect.right - rect.left
                                height = rect.bottom - rect.top
                                if width < 200 or height < 200:
                                    logger.debug(f'크기 너무 작음 ({width}x{height}), 건너뜀')
                                    continue
                            except Exception:
                                pass

                            return w

                    except Exception:
                        continue
            except Exception:
                continue

        return None

    # ──────────────────────────────────────────
    # 내부: 팝업 자동 조작
    # ──────────────────────────────────────────

    def _handle_popup(self, popup_window):
        """
        인증서 팝업의 전체 처리 흐름:
          1. 저장 위치 탭 선택
          2. 인증서 선택
          3. 비밀번호 입력
          4. 확인 클릭
        """
        time.sleep(1)  # 팝업이 완전히 로딩될 때까지 잠시 대기

        # ── 1. 인증서 저장 위치 탭 선택 ──
        self._select_cert_location(popup_window)
        time.sleep(1)

        # ── 2. 인증서 목록에서 선택 ──
        self._select_certificate(popup_window)
        time.sleep(0.5)

        # ── 3. 비밀번호 입력 ──
        self._enter_password(popup_window)
        time.sleep(0.5)

        # ── 4. 확인 버튼 클릭 ──
        self._click_confirm(popup_window)

    def _select_cert_location(self, popup):
        """인증서 위치 탭 클릭 (하드디스크, 이동식 등)"""
        location_text = CERT_LOCATION_MAP.get(self.cert_location, '하드디스크')
        self._emit(f'📂 인증서 위치 선택: {location_text}')

        try:
            # 방법 1: 텍스트가 포함된 버튼/탭 찾기
            children = self._get_all_descendants(popup)
            for child in children:
                try:
                    text = child.window_text()
                    if location_text in text:
                        child.click_input()
                        self._emit(f'  → "{text}" 탭 클릭 성공')
                        return
                except Exception:
                    continue

            # 방법 2: 부분 매칭 (예: '하드디스크\n이동식' 인 경우)
            for child in children:
                try:
                    text = child.window_text()
                    # '하드디스크'가 포함된 텍스트 찾기
                    if any(part in text for part in location_text.split()):
                        child.click_input()
                        self._emit(f'  → "{text}" 탭 클릭 성공 (부분 매칭)')
                        return
                except Exception:
                    continue

            self._emit(f'  ⚠️ "{location_text}" 탭을 찾지 못함 — 기본 위치 사용')

        except Exception as e:
            self._emit(f'  ⚠️ 위치 선택 실패: {e}')

    def _select_certificate(self, popup):
        """인증서 목록에서 키워드 매칭으로 인증서 선택"""
        self._emit(f'🔐 인증서 선택 중... (키워드: "{self.cert_keyword or "첫 번째 인증서"}")')

        try:
            children = self._get_all_descendants(popup)

            # ListView 또는 리스트 항목 찾기
            list_items = []
            for child in children:
                try:
                    ctrl_type = getattr(child, 'friendly_class_name', lambda: '')()
                    text = child.window_text()

                    # 리스트 뷰 항목이거나, 인증서 정보가 포함된 텍스트
                    if any(x in ctrl_type.lower() for x in ['listview', 'list', 'syslistview']):
                        list_items.append(child)
                    elif self.cert_keyword and self.cert_keyword in text:
                        # 직접 키워드 매칭
                        child.click_input()
                        self._emit(f'  → 인증서 선택: "{text[:50]}"')
                        return
                except Exception:
                    continue

            # ListView를 찾은 경우 → 항목 선택
            for lv in list_items:
                try:
                    # ListView의 항목들 순회
                    items = lv.items() if hasattr(lv, 'items') else lv.children()
                    for item in items:
                        try:
                            item_text = item.window_text() if hasattr(item, 'window_text') else str(item)
                            if not self.cert_keyword or self.cert_keyword in item_text:
                                if hasattr(item, 'click_input'):
                                    item.click_input()
                                elif hasattr(item, 'select'):
                                    item.select()
                                self._emit(f'  → 인증서 선택: "{item_text[:50]}"')
                                return
                        except Exception:
                            continue
                except Exception:
                    continue

            # 못 찾은 경우 — 첫 번째 항목 클릭 시도
            self._emit('  ⚠️ 키워드로 인증서를 찾지 못함 — 첫 번째 인증서가 이미 선택되어 있다고 가정')

        except Exception as e:
            self._emit(f'  ⚠️ 인증서 선택 실패: {e}')

    def _enter_password(self, popup):
        """비밀번호 입력"""
        self._emit('🔑 비밀번호 입력 중...')

        try:
            children = self._get_all_descendants(popup)

            # Edit 컨트롤 찾기 (비밀번호 입력란)
            edit_controls = []
            for child in children:
                try:
                    cls = child.class_name()
                    ctrl_type = getattr(child, 'friendly_class_name', lambda: '')()

                    if 'Edit' in cls or 'edit' in ctrl_type.lower():
                        edit_controls.append(child)
                except Exception:
                    continue

            if not edit_controls:
                raise Exception('비밀번호 입력란을 찾지 못했습니다')

            # 마지막 Edit 컨트롤이 보통 비밀번호 입력란
            # (첫 번째는 검색창일 수 있으므로)
            pw_edit = edit_controls[-1]

            # 포커스 → 기존 내용 지우기 → 입력
            pw_edit.set_focus()
            time.sleep(0.3)
            pw_edit.set_edit_text('')
            time.sleep(0.1)

            # 한 글자씩 입력 (보안 키보드 우회)
            pw_edit.type_keys(self.cert_password, with_spaces=True, pause=0.05)

            self._emit('  → 비밀번호 입력 완료')

        except Exception as e:
            self._emit(f'  ❌ 비밀번호 입력 실패: {e}')
            raise

    def _click_confirm(self, popup):
        """확인 버튼 클릭"""
        self._emit('✅ 확인 버튼 클릭...')

        try:
            children = self._get_all_descendants(popup)

            # '확인' 텍스트가 있는 버튼 찾기
            for child in children:
                try:
                    text = child.window_text()
                    cls = child.class_name()

                    if '확인' in text and ('Button' in cls or 'button' in cls.lower()):
                        child.click_input()
                        self._emit('  → 확인 버튼 클릭 성공')
                        return
                except Exception:
                    continue

            # Fallback: '확인' 텍스트만으로 찾기
            for child in children:
                try:
                    text = child.window_text()
                    if text.strip() == '확인':
                        child.click_input()
                        self._emit('  → 확인 버튼 클릭 성공 (텍스트 매칭)')
                        return
                except Exception:
                    continue

            raise Exception('"확인" 버튼을 찾지 못했습니다')

        except Exception as e:
            self._emit(f'  ❌ 확인 버튼 클릭 실패: {e}')
            raise

    # ──────────────────────────────────────────
    # 유틸리티
    # ──────────────────────────────────────────

    def _get_all_descendants(self, window, max_depth=8):
        """창의 모든 하위 요소를 재귀적으로 수집"""
        result = []
        self._collect_children(window, result, 0, max_depth)
        return result

    def _collect_children(self, element, result, depth, max_depth):
        """재귀적으로 하위 요소 수집"""
        if depth >= max_depth:
            return
        try:
            children = element.children()
            for child in children:
                result.append(child)
                self._collect_children(child, result, depth + 1, max_depth)
        except Exception:
            pass
