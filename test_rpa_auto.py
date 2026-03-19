"""
AutoTax — RPA 자동 테스트 (비대화형)
Playwright로 홈택스 접속 → 페이지 분석 → 결과 파일로 저장
"""
import asyncio
import sys
import os
import json
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

RESULT_FILE = os.path.join(BASE_DIR, 'rpa_test_result.json')


async def run_test():
    results = {
        'playwright_install': False,
        'browser_launch': False,
        'hometax_connect': False,
        'main_page_elements': [],
        'login_page_reached': False,
        'login_page_elements': [],
        'errors': [],
    }

    # 1. Playwright import 확인
    try:
        from playwright.async_api import async_playwright
        results['playwright_install'] = True
        print('[OK] playwright import 성공')
    except ImportError as e:
        results['errors'].append(f'playwright import 실패: {e}')
        print(f'[FAIL] playwright import 실패: {e}')
        save_results(results)
        return results

    try:
        async with async_playwright() as pw:
            # 2. 브라우저 실행
            try:
                browser = await pw.chromium.launch(headless=True)
                results['browser_launch'] = True
                print('[OK] Chromium 브라우저 실행 성공')
            except Exception as e:
                results['errors'].append(f'브라우저 실행 실패: {e}')
                print(f'[FAIL] 브라우저 실행 실패: {e}')
                save_results(results)
                return results

            context = await browser.new_context(
                viewport={'width': 1280, 'height': 900},
                locale='ko-KR',
            )
            page = await context.new_page()

            # 3. 홈택스 접속
            try:
                print('[...] 홈택스 접속 시도 중 (hometax.go.kr)...')
                resp = await page.goto('https://hometax.go.kr',
                                       wait_until='domcontentloaded',
                                       timeout=30000)
                results['hometax_connect'] = True
                results['hometax_status'] = resp.status if resp else 'unknown'
                print(f'[OK] 홈택스 접속 성공 (status={results["hometax_status"]})')
                await page.wait_for_timeout(5000)
            except Exception as e:
                results['errors'].append(f'홈택스 접속 실패: {e}')
                print(f'[FAIL] 홈택스 접속 실패: {e}')
                await browser.close()
                save_results(results)
                return results

            # 4. 메인 페이지 요소 탐색
            try:
                print('[...] 메인 페이지 요소 분석 중...')
                elements = await page.evaluate('''() => {
                    const results = [];
                    const selectors = 'a, button, span, input, li, nav, [class*="menu"], [class*="login"], [class*="gnb"]';
                    const all = document.querySelectorAll(selectors);
                    all.forEach(el => {
                        const text = (el.innerText || el.value || '').trim().substring(0, 60);
                        if (text && text.length > 0) {
                            results.push({
                                tag: el.tagName,
                                id: el.id || '',
                                cls: (el.className && typeof el.className === 'string') ? el.className.substring(0, 80) : '',
                                text: text.replace(/\\n/g, ' ').substring(0, 60),
                                href: el.href || '',
                            });
                        }
                    });
                    return results.slice(0, 200);
                }''')
                results['main_page_elements'] = elements
                print(f'[OK] 메인 페이지 요소 {len(elements)}개 발견')

                # 핵심 요소 필터링 출력
                important_keywords = ['로그인', '로그아웃', '지급명세', '간이', '명세서', '메뉴',
                                      '인증', 'login', 'menu', 'gnb']
                for el in elements:
                    text_lower = el['text'].lower()
                    if any(kw in text_lower or kw in el.get('id', '').lower() or
                           kw in el.get('cls', '').lower() for kw in important_keywords):
                        tag = el['tag']
                        eid = f' id="{el["id"]}"' if el['id'] else ''
                        cls = f' class="{el["cls"][:40]}"' if el['cls'] else ''
                        print(f'  ★ <{tag}{eid}{cls}> "{el["text"][:40]}"')

            except Exception as e:
                results['errors'].append(f'메인 페이지 분석 오류: {e}')
                print(f'[WARN] 메인 페이지 분석 오류: {e}')

            # 5. 로그인 페이지 이동 시도
            try:
                print('[...] 로그인 버튼 탐색 및 클릭 시도...')
                login_selectors = [
                    'a:has-text("로그인")',
                    'button:has-text("로그인")',
                    'span:has-text("로그인")',
                    'text=로그인',
                ]
                clicked = False
                for sel in login_selectors:
                    try:
                        loc = page.locator(sel).first
                        if await loc.is_visible(timeout=3000):
                            await loc.click()
                            await page.wait_for_timeout(3000)
                            clicked = True
                            results['login_page_reached'] = True
                            print(f'[OK] 로그인 클릭 성공: {sel}')
                            break
                    except Exception:
                        continue

                if not clicked:
                    print('[WARN] 로그인 버튼 못 찾음 — URL 직접 이동 시도')
                    await page.goto(
                        'https://hometax.go.kr/websquare/websquare.wq?w2xPath=/ui/pp/index_pp.xml',
                        wait_until='domcontentloaded', timeout=30000
                    )
                    await page.wait_for_timeout(3000)
                    results['login_page_reached'] = True
                    print('[OK] 로그인 페이지 직접 이동')

            except Exception as e:
                results['errors'].append(f'로그인 페이지 이동 실패: {e}')
                print(f'[FAIL] 로그인 페이지 이동 실패: {e}')

            # 6. 로그인 페이지 요소 분석
            if results['login_page_reached']:
                try:
                    print('[...] 로그인 페이지 요소 분석 중...')
                    current_url = page.url
                    print(f'  현재 URL: {current_url}')

                    login_elements = await page.evaluate('''() => {
                        const results = [];
                        const all = document.querySelectorAll('a, button, span, input, label, div[onclick], [class*="login"], [class*="cert"], [class*="tab"]');
                        all.forEach(el => {
                            const text = (el.innerText || el.value || el.placeholder || '').trim().substring(0, 60);
                            if (text && text.length > 0) {
                                results.push({
                                    tag: el.tagName,
                                    id: el.id || '',
                                    cls: (el.className && typeof el.className === 'string') ? el.className.substring(0, 80) : '',
                                    text: text.replace(/\\n/g, ' ').substring(0, 60),
                                    type: el.type || '',
                                    name: el.name || '',
                                });
                            }
                        });
                        return results.slice(0, 200);
                    }''')
                    results['login_page_elements'] = login_elements
                    results['login_page_url'] = current_url
                    print(f'[OK] 로그인 페이지 요소 {len(login_elements)}개 발견')

                    login_keywords = ['인증', '로그인', '공동', '간편', '아이디', '비밀번호',
                                      '확인', '제출', 'cert', 'password', 'submit']
                    for el in login_elements:
                        text_lower = (el['text'] + el.get('id', '') + el.get('cls', '')).lower()
                        if any(kw in text_lower for kw in login_keywords):
                            tag = el['tag']
                            eid = f' id="{el["id"]}"' if el['id'] else ''
                            cls = f' class="{el["cls"][:40]}"' if el['cls'] else ''
                            tp = f' type="{el["type"]}"' if el['type'] else ''
                            print(f'  ★ <{tag}{eid}{cls}{tp}> "{el["text"][:40]}"')

                except Exception as e:
                    results['errors'].append(f'로그인 페이지 분석 오류: {e}')
                    print(f'[WARN] 로그인 페이지 분석 오류: {e}')

            await browser.close()

    except Exception as e:
        results['errors'].append(f'전체 오류: {traceback.format_exc()}')
        print(f'[FAIL] 전체 오류: {e}')

    save_results(results)
    return results


def save_results(results):
    # 결과에서 큰 리스트는 요약
    summary = dict(results)
    summary['main_page_elements_count'] = len(results.get('main_page_elements', []))
    summary['login_page_elements_count'] = len(results.get('login_page_elements', []))
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f'\n결과 저장: {RESULT_FILE}')


if __name__ == '__main__':
    print('='*60)
    print('AutoTax RPA 자동 테스트')
    print('='*60)
    asyncio.run(run_test())
