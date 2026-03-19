import sys
import os
import datetime
from pywinauto import Desktop

def main():
    print("=" * 60)
    print("  AutoTax — 인증서 팝업 구조 탐색 (v3)")
    print("=" * 60)
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'popup_inspection_result.txt')
    output = []
    
    # UIA 모드와 Win32 모드 둘 다 시도할 겁니다
    for backend_name in ["uia", "win32"]:
        try:
            print(f"\n[{backend_name}] 모드로 모든 창을 낚아보는 중...")
            output.append(f"\n--- backend: {backend_name} ---")
            
            desktop = Desktop(backend=backend_name)
            windows = desktop.windows()
            
            for i, w in enumerate(windows):
                try:
                    title = w.window_text()
                    cls = w.class_name()
                    rect = w.rectangle()
                    print(f"  [{i}] 창 발견: {title} ({cls})")
                    
                    output.append(f"\n[{i}] 제목: {title} | 클래스: {cls} | 위치: {rect}")
                    
                    # 제목이 '인증'을 포함하거나, 창 크기가 적당하면 상세 분석
                    width = rect.right - rect.left
                    if "인증" in title or (300 < width < 600):
                        import io
                        f = io.StringIO()
                        w.print_control_identifiers(filename=f) # outfile 대신 filename 사용
                        output.append(f.getvalue())
                except:
                    continue
        except:
            continue

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    
    print(f"\n✅ 완료! {output_path} 파일을 다시 확인해주세요.")

if __name__ == "__main__":
    main()
