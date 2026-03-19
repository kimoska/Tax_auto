"""
AutoTax — 인증서 팝업 구조 탐색 스크립트
==========================================

사용법:
  1. 홈택스(https://hometax.go.kr)에서 로그인 클릭
  2. '공동·금융인증서' 탭 선택 → 파란 '인증하기' 버튼 클릭
  3. 인증서 선택 팝업이 화면에 뜬 상태 유지
  4. 이 스크립트 실행:
     python rpa/inspect_cert_popup.py

결과:
  - 화면에 열려있는 모든 창 목록 출력
  - 인증서 팝업으로 추정되는 창의 전체 컨트롤 구조 출력
  - 결과가 rpa/popup_inspection_result.txt 에 저장됨
"""

import sys
import os
import time
import datetime

# ── pywinauto 설치 확인 ──
try:
    import pywinauto
    from pywinauto import Desktop
    from pywinauto.application import Application
except ImportError:
    print("=" * 60)
    print("❌ pywinauto가 설치되지 않았습니다.")
    print()
    print("설치 방법:")
    print("  pip install pywinauto")
    print()
    print("또는 Python 경로를 직접 지정:")
    print("  python -m pip install pywinauto")
    print("=" * 60)
    sys.exit(1)


def get_output_path():
    """결과 저장 경로"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'popup_inspection_result.txt')


def inspect_all_windows(output_lines: list):
    """현재 열려있는 모든 최상위 창 목록 출력"""
    output_lines.append("=" * 70)
    output_lines.append(f"[1단계] 현재 열려있는 모든 창 목록")
    output_lines.append(f"    시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append("=" * 70)

    desktop = Desktop(backend="uia")
    windows = desktop.windows()

    for i, w in enumerate(windows):
        try:
            title = w.window_text()
            cls = w.class_name()
            rect = w.rectangle()
            output_lines.append(
                f"  [{i+1:3d}] 제목: '{title}'"
                f"  |  클래스: '{cls}'"
                f"  |  위치: ({rect.left}, {rect.top}, {rect.right}, {rect.bottom})"
            )
        except Exception as e:
            output_lines.append(f"  [{i+1:3d}] (읽기 실패: {e})")

    output_lines.append(f"\n  → 총 {len(windows)}개 창 발견")
    output_lines.append("")


def find_cert_popup_windows(output_lines: list) -> list:
    """인증서 팝업으로 추정되는 창 찾기"""
    output_lines.append("=" * 70)
    output_lines.append("[2단계] 인증서 팝업 후보 창 탐색")
    output_lines.append("=" * 70)

    # 인증서 팝업의 창 제목에 포함될 수 있는 키워드들
    keywords = [
        '인증', '인증서', 'certificate', 'cert',
        'CrossCert', 'KICA', 'KOSCOM', 'NPS',
        '공동인증', '금융인증', 'SignKorea',
        '본인확인', '전자서명', 'NPKI',
        'iniLINE', 'XecureSmart', 'INISAFE',
        'Veraport', '보안', 'Security',
        'UbiKey', 'RaonSecure',
        # 일반적인 보안 프로그램 관련
        '비밀번호', 'password',
    ]

    desktop = Desktop(backend="uia")
    all_windows = desktop.windows()
    candidates = []

    for w in all_windows:
        try:
            title = w.window_text().lower()
            cls = w.class_name().lower()
            matched_keywords = [kw for kw in keywords if kw.lower() in title or kw.lower() in cls]
            if matched_keywords:
                candidates.append(w)
                output_lines.append(
                    f"  ✅ 매칭! 제목: '{w.window_text()}'"
                    f"  |  클래스: '{w.class_name()}'"
                    f"  |  매칭 키워드: {matched_keywords}"
                )
        except Exception:
            continue

    if not candidates:
        output_lines.append("  ⚠️ 인증서 팝업 키워드에 매칭되는 창을 찾지 못했습니다.")
        output_lines.append("  → 홈택스에서 인증서 팝업이 떠 있는지 확인해주세요.")
        output_lines.append("  → 또는 키워드에 없는 창 제목일 수 있습니다.")
        output_lines.append("")
        output_lines.append("  [대안] 모든 창을 탐색하겠습니다...")
        # 모든 창 중 크기가 적당한 것들 추가
        for w in all_windows:
            try:
                rect = w.rectangle()
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                title = w.window_text()
                # 팝업 크기 범위 (너무 작거나 너무 큰 것 제외)
                if 200 < width < 1200 and 200 < height < 900 and title:
                    candidates.append(w)
            except Exception:
                continue

    output_lines.append(f"\n  → 총 {len(candidates)}개 후보 창 발견")
    output_lines.append("")
    return candidates


def inspect_window_controls(window, output_lines: list, depth_limit=5):
    """특정 창의 모든 컨트롤 구조를 상세 출력"""
    try:
        title = window.window_text()
    except Exception:
        title = "(제목 읽기 실패)"

    output_lines.append("=" * 70)
    output_lines.append(f"[3단계] 창 컨트롤 상세 구조: '{title}'")
    output_lines.append("=" * 70)

    try:
        # print_control_identifiers 의 출력을 캡처
        import io
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        window.print_control_identifiers(depth=depth_limit)

        sys.stdout = old_stdout
        control_tree = buffer.getvalue()

        output_lines.append(control_tree)

    except Exception as e:
        output_lines.append(f"  ❌ 컨트롤 구조 읽기 실패: {e}")
        output_lines.append("")

        # Fallback: 직접 children 탐색
        output_lines.append("  [대안] 직접 하위 요소 탐색 중...")
        try:
            _inspect_children_recursive(window, output_lines, indent=2, max_depth=depth_limit)
        except Exception as e2:
            output_lines.append(f"  ❌ 대안 탐색도 실패: {e2}")

    output_lines.append("")


def _inspect_children_recursive(element, output_lines, indent=2, max_depth=5, current_depth=0):
    """하위 요소 재귀 탐색"""
    if current_depth >= max_depth:
        return

    try:
        children = element.children()
    except Exception:
        return

    prefix = " " * indent
    for i, child in enumerate(children):
        try:
            ctrl_type = child.element_info.control_type or "Unknown"
            name = child.element_info.name or ""
            cls = child.element_info.class_name or ""
            auto_id = child.element_info.automation_id or ""

            line = (
                f"{prefix}[{i}] {ctrl_type}"
                f"  name='{name}'"
                f"  class='{cls}'"
                f"  auto_id='{auto_id}'"
            )

            # 값이 있는 요소는 표시
            try:
                if hasattr(child, 'get_value'):
                    val = child.get_value()
                    if val:
                        line += f"  value='{val}'"
            except Exception:
                pass

            output_lines.append(line)
            _inspect_children_recursive(child, output_lines, indent + 4, max_depth, current_depth + 1)

        except Exception as e:
            output_lines.append(f"{prefix}[{i}] (읽기 실패: {e})")


def try_win32_backend(output_lines: list):
    """win32 백엔드로도 시도 (레거시 ActiveX 팝업일 경우)"""
    output_lines.append("=" * 70)
    output_lines.append("[4단계] win32 백엔드로 추가 탐색")
    output_lines.append("=" * 70)

    try:
        desktop = Desktop(backend="win32")
        windows = desktop.windows()

        keywords = ['인증', 'cert', 'CrossCert', 'KICA', 'INISAFE',
                     'XecureSmart', '보안', '비밀번호', 'SignKorea']

        found = False
        for w in windows:
            try:
                title = w.window_text()
                cls = w.class_name()
                matched = [kw for kw in keywords if kw.lower() in title.lower() or kw.lower() in cls.lower()]
                if matched:
                    found = True
                    output_lines.append(f"\n  ✅ [win32] 매칭: '{title}' (class: '{cls}')")
                    output_lines.append(f"     매칭 키워드: {matched}")

                    # 컨트롤 구조 출력
                    import io
                    old_stdout = sys.stdout
                    sys.stdout = buffer = io.StringIO()
                    w.print_control_identifiers()
                    sys.stdout = old_stdout
                    output_lines.append(buffer.getvalue())

            except Exception:
                continue

        if not found:
            output_lines.append("  → win32 백엔드에서도 인증서 팝업을 찾지 못했습니다.")

    except Exception as e:
        output_lines.append(f"  ❌ win32 탐색 실패: {e}")

    output_lines.append("")


def main():
    print("=" * 60)
    print("  AutoTax — 인증서 팝업 구조 탐색")
    print("=" * 60)
    print()
    print("⚠️  이 스크립트를 실행하기 전에:")
    print("   1. 홈택스에서 로그인 → 공동·금융인증서 → '인증하기' 클릭")
    print("   2. 인증서 선택 팝업이 화면에 떠 있는 상태를 유지")
    print()
    print("탐색을 시작합니다... (약 5~10초 소요)")
    print()

    output_lines = []
    output_lines.append("AutoTax — 인증서 팝업 구조 탐색 결과")
    output_lines.append(f"생성 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append(f"pywinauto 버전: {pywinauto.__version__}")
    output_lines.append("")

    # 1단계: 모든 창 목록
    print("  [1/4] 모든 창 목록 수집 중...")
    inspect_all_windows(output_lines)

    # 2단계: 인증서 팝업 후보 찾기
    print("  [2/4] 인증서 팝업 후보 탐색 중...")
    candidates = find_cert_popup_windows(output_lines)

    # 3단계: 후보 창의 컨트롤 구조 상세 출력
    print("  [3/4] 후보 창 컨트롤 구조 분석 중...")
    for i, w in enumerate(candidates[:5]):  # 최대 5개만
        try:
            title = w.window_text()
            print(f"        분석 중: '{title}'...")
            inspect_window_controls(w, output_lines)
        except Exception as e:
            output_lines.append(f"  ❌ 창 분석 실패: {e}")

    # 4단계: win32 백엔드 추가 탐색
    print("  [4/4] win32 백엔드 추가 탐색 중...")
    try_win32_backend(output_lines)

    # 결과 저장
    output_path = get_output_path()
    full_output = "\n".join(output_lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_output)

    print()
    print("=" * 60)
    print(f"✅ 탐색 완료! 결과가 저장되었습니다:")
    print(f"   {output_path}")
    print()
    print("이 파일의 내용을 개발자에게 공유해주세요.")
    print("=" * 60)

    # 콘솔에도 핵심 부분 출력
    print()
    print("─── [요약] 인증서 팝업 후보 창 ───")
    for line in output_lines:
        if '✅ 매칭' in line:
            print(line)
    print()


if __name__ == '__main__':
    main()
