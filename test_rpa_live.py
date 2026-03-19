"""
AutoTax — RPA 실제 브라우저 단계별 테스트
headless=False로 창을 열고 홈택스에 접속, 각 단계를 실행하며 결과 JSON 저장.
로그인은 시도하지 않음 (설정 미완료) — 접속 + 페이지 분석만 수행.
"""
import asyncio
import json
import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

RESULT_FILE = os.path.join(BASE_DIR, 'rpa_live_test_result.json')


async def run_live_test():
    results = {
        'steps': [],
        'errors': [],
        'final_url': '',
        'screenshots': [],
    }

    def log_step(name, status, detail=''):
        entry = {'step': name, 'status': status, 'detail': detail}
        results['steps'].append(entry)
        icon = '✅' if status == 'OK' else ('❌' if status == 'FAIL' else '⚠️')
        print(f'{icon} [{name}] {status}: {detail}')

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        # ═══ STEP 1: 브라우저 실행 ═══
        try:
            browser = await pw.chromium.launch(
                headless=False,
                slow_mo=500,
                args=['--start-maximized'],
            )
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 900},
                locale='ko-KR',
            )
            page = await context.new_page()
            log_step('브라우저 실행', 'OK', 'Chromium headless=False')
        except Exception as e:
            log_step('브라우저 실행', 'FAIL', str(e))
            save_results(results)
            return

        # ═══ STEP 2: 홈택스 메인 접속 ═══
        try:
            resp = await page.goto('https://hometax.go.kr',
                                   wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(4000)
            status = resp.status if resp else '?'
            log_step('홈택스 접속', 'OK', f'status={status}, url={page.url}')
        except Exception as e:
            log_step('홈택스 접속', 'FAIL', str(e))
            await browser.close()
            save_results(results)
            return

        # ═══ STEP 3: 로그인 버튼 찾기 ═══
        login_found = False
        login_selectors = [
            ('#mf_wfHeader_group1503', 'ID 셀렉터'),
            ('a:has-text("로그인")', '텍스트 셀렉터'),
            ('text=로그인', 'text= 셀렉터'),
        ]
        for sel, desc in login_selectors:
            try:
                loc = page.locator(sel).first
                visible = await loc.is_visible(timeout=3000)
                if visible:
                    log_step('로그인 버튼 탐색', 'OK', f'{desc}: {sel}')
                    login_found = True
                    break
            except Exception:
                continue

        if not login_found:
            log_step('로그인 버튼 탐색', 'FAIL', '모든 셀렉터 실패')

        # ═══ STEP 4: 로그인 버튼 클릭 ═══
        if login_found:
            try:
                await loc.click()
                await page.wait_for_timeout(4000)
                log_step('로그인 버튼 클릭', 'OK', f'이동 URL: {page.url}')
            except Exception as e:
                log_step('로그인 버튼 클릭', 'FAIL', str(e))

        # ═══ STEP 5: 로그인 페이지 분석 ═══
        try:
            await page.wait_for_timeout(3000)
            # 로그인 페이지 내부 요소 전부 캡처
            login_elements = await page.evaluate('''() => {
                const results = [];
                const all = document.querySelectorAll('a, button, span, input, label, div, li, img');
                all.forEach(el => {
                    const text = (el.innerText || el.value || el.placeholder || el.alt || '').trim();
                    const rect = el.getBoundingClientRect();
                    // 화면에 보이는 요소만 (높이/너비 > 0, viewport 내)
                    if (text.length > 0 && rect.width > 0 && rect.height > 0
                        && rect.top < 1200 && rect.left < 1400) {
                        results.push({
                            tag: el.tagName,
                            id: el.id || '',
                            cls: (el.className && typeof el.className === 'string')
                                 ? el.className.substring(0, 80) : '',
                            text: text.replace(/\\n/g, ' ').substring(0, 80),
                            type: el.type || '',
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height),
                        });
                    }
                });
                return results;
            }''')

            # 인증 관련 요소 필터
            auth_keywords = ['인증', '공동', '간편', '아이디', '비밀번호', '로그인',
                             '금융', 'cert', 'password', '확인', '선택']
            auth_elements = [e for e in login_elements
                             if any(k in (e['text']+e.get('id','')+e.get('cls','')).lower()
                                    for k in auth_keywords)]

            log_step('로그인 페이지 분석', 'OK',
                     f'총 {len(login_elements)}개 보이는 요소, 인증관련 {len(auth_elements)}개')

            # 인증 관련 요소 상세 출력
            print('\n  === 로그인 페이지 인증 관련 요소 ===')
            for el in auth_elements:
                eid = f' id="{el["id"]}"' if el['id'] else ''
                cls = f' cls="{el["cls"][:30]}"' if el['cls'] else ''
                tp = f' type={el["type"]}' if el['type'] else ''
                print(f'  <{el["tag"]}{eid}{cls}{tp}> "{el["text"][:50]}" '
                      f'at({el["x"]},{el["y"]}) {el["w"]}x{el["h"]}')

            results['login_elements'] = auth_elements
            results['login_all_count'] = len(login_elements)

        except Exception as e:
            log_step('로그인 페이지 분석', 'FAIL', str(e))

        # ═══ STEP 6: 공동인증서 탭 찾기 ═══
        cert_found = False
        cert_selectors = [
            ('text=공동·금융인증서', '텍스트(·)'),
            ('text=공동ㆍ금융인증서', '텍스트(ㆍ)'),
            ('a:has-text("공동")', 'a태그-공동'),
            ('span:has-text("공동")', 'span태그-공동'),
            ('text=인증서 로그인', '인증서 로그인'),
            ('[class*="cert"]', 'class cert'),
        ]
        for sel, desc in cert_selectors:
            try:
                loc = page.locator(sel).first
                visible = await loc.is_visible(timeout=2000)
                if visible:
                    log_step('공동인증서 탭 탐색', 'OK', f'{desc}: {sel}')
                    cert_found = True
                    break
            except Exception:
                continue

        if not cert_found:
            log_step('공동인증서 탭 탐색', 'WARN',
                     '자동 탐색 실패 — F12에서 인증서 탭의 id를 확인해주세요')

        # ═══ STEP 7: GNB 메뉴 "지급명세" 탐색 (로그인 없이도 확인 가능) ═══
        # 메인 페이지로 돌아가서 GNB 메뉴 탐색
        try:
            await page.goto('https://hometax.go.kr', wait_until='domcontentloaded',
                            timeout=30000)
            await page.wait_for_timeout(3000)

            # GNB 1depth 메뉴 전체 수집
            gnb_menus = await page.evaluate('''() => {
                const results = [];
                // 1depth GNB 메뉴 찾기 (menu_1st 하위의 LI > A)
                const menuList = document.querySelector('#mf_wfHeader_hdGroup911');
                if (menuList) {
                    const firstLevel = menuList.querySelectorAll(':scope > li > a');
                    firstLevel.forEach(el => {
                        results.push({
                            tag: 'GNB-1depth',
                            id: el.id || el.parentElement.id || '',
                            text: (el.innerText || '').trim().split('\\n')[0].trim(),
                        });
                    });
                }
                // 더 넓은 범위로도 시도
                const allGnbA = document.querySelectorAll('.menu_1st > li > a.w2group');
                allGnbA.forEach(el => {
                    const txt = (el.innerText || '').trim().split('\\n')[0].trim();
                    if (txt && !results.find(r => r.text === txt)) {
                        results.push({
                            tag: 'GNB-1depth-wide',
                            id: el.id || el.parentElement.id || '',
                            text: txt,
                        });
                    }
                });
                return results;
            }''')

            print('\n  === GNB 1depth 메뉴 ===')
            for m in gnb_menus:
                marker = '★' if '지급' in m['text'] else ' '
                print(f'  {marker} [{m["id"]}] "{m["text"]}"')

            # "지급명세" 관련 요소 별도 탐색
            jigup_elements = await page.evaluate('''() => {
                const results = [];
                const all = document.querySelectorAll('a, span, li');
                all.forEach(el => {
                    const text = (el.innerText || '').trim();
                    if (text.includes('지급명세') || text.includes('간이지급') ||
                        text.includes('직접작성')) {
                        results.push({
                            tag: el.tagName,
                            id: el.id || '',
                            cls: (el.className && typeof el.className === 'string')
                                 ? el.className.substring(0, 60) : '',
                            text: text.split('\\n')[0].trim().substring(0, 60),
                        });
                    }
                });
                return results;
            }''')

            if jigup_elements:
                log_step('GNB "지급명세" 메뉴 탐색', 'OK', f'{len(jigup_elements)}개 발견')
                print('\n  === "지급명세" 관련 요소 ===')
                for el in jigup_elements:
                    eid = f' id="{el["id"]}"' if el['id'] else ''
                    print(f'  ★ <{el["tag"]}{eid}> "{el["text"][:50]}"')
            else:
                log_step('GNB "지급명세" 메뉴 탐색', 'WARN',
                         'DOM에서 "지급명세" 텍스트 미발견 — 메뉴가 동적 로딩될 수 있음')

            results['gnb_menus'] = gnb_menus
            results['jigup_elements'] = jigup_elements

        except Exception as e:
            log_step('GNB 메뉴 탐색', 'FAIL', str(e))

        # ═══ STEP 8: 전체메뉴 버튼으로 지급명세 찾기 ═══
        try:
            allMenu = page.locator('#mf_wfHeader_hdGroup005')
            if await allMenu.is_visible(timeout=3000):
                await allMenu.click()
                await page.wait_for_timeout(2000)
                log_step('전체메뉴 클릭', 'OK', '')

                # 전체메뉴 팝업에서 지급명세 검색
                jigup_in_allmenu = await page.evaluate('''() => {
                    const results = [];
                    const all = document.querySelectorAll('a, span, li, div');
                    all.forEach(el => {
                        const text = (el.innerText || '').trim();
                        if ((text.includes('지급명세') || text.includes('간이지급') ||
                             text.includes('직접작성') || text.includes('사업소득'))
                            && text.length < 80) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                results.push({
                                    tag: el.tagName,
                                    id: el.id || '',
                                    text: text.substring(0, 60),
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                });
                            }
                        }
                    });
                    return results;
                }''')

                if jigup_in_allmenu:
                    log_step('전체메뉴→지급명세 탐색', 'OK', f'{len(jigup_in_allmenu)}개')
                    print('\n  === 전체메뉴 내 "지급명세" 관련 ===')
                    for el in jigup_in_allmenu:
                        eid = f' id="{el["id"]}"' if el['id'] else ''
                        print(f'  ★ <{el["tag"]}{eid}> "{el["text"][:50]}" at({el["x"]},{el["y"]})')
                    results['allmenu_jigup'] = jigup_in_allmenu
                else:
                    log_step('전체메뉴→지급명세 탐색', 'WARN', '전체메뉴에서도 미발견')

        except Exception as e:
            log_step('전체메뉴 탐색', 'FAIL', str(e))

        # ═══ 완료 — 브라우저 20초 후 닫기 ═══
        results['final_url'] = page.url
        print(f'\n현재 URL: {page.url}')
        print('20초 후 브라우저를 닫습니다...')

        await page.wait_for_timeout(20000)
        await browser.close()

    save_results(results)
    print('\n=== 테스트 요약 ===')
    for s in results['steps']:
        icon = '✅' if s['status'] == 'OK' else ('❌' if s['status'] == 'FAIL' else '⚠️')
        print(f'{icon} {s["step"]}: {s["detail"][:60]}')


def save_results(results):
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n결과 저장: {RESULT_FILE}')


if __name__ == '__main__':
    print('='*60)
    print('AutoTax RPA 실제 브라우저 단계별 테스트')
    print('headless=False — 실제 창이 열립니다')
    print('='*60 + '\n')
    asyncio.run(run_live_test())
