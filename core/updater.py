import os
import sys
import json
import urllib.request
import subprocess
import zipfile
import tempfile
import ssl
from PySide6.QtCore import QObject, Signal, QThread

REPO_API_URL = "https://api.github.com/repos/kimoska/Tax_auto/releases/latest"

class UpdateChecker(QThread):
    update_available = Signal(str, str, str) # version, description, download_url
    error_occurred = Signal(str)
    
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    def run(self):
        try:
            # 여러 릴리스를 가져오기 위해 /latest 제거
            repo_api_list_url = REPO_API_URL.replace("/latest", "")
            req = urllib.request.Request(repo_api_list_url, headers={'User-Agent': 'TaxAuto-Updater'})
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                releases = json.loads(response.read().decode('utf-8'))
                
                if not releases or not isinstance(releases, list):
                    self.update_available.emit(self.current_version, "업데이트 정보를 불러올 수 없습니다.", "")
                    return
                
                latest_release = releases[0]
                latest_version = latest_release.get("tag_name", "")
                
                # 전체 릴리스 내역 포맷팅 (최대 10개)
                all_desc = []
                for idx, r in enumerate(releases[:10]):
                    v = r.get("tag_name", "")
                    date = r.get("published_at", "")[:10]  # YYYY-MM-DD
                    body = r.get("body", "내용 없음")
                    # 최신 버전에는 [New] 표시
                    prefix = "🆕 " if idx == 0 else "✓ "
                    all_desc.append(f"<b>{prefix}[{v}] 업데이트 ({date})</b><br><br>{body}")
                
                full_description = "<hr>".join(all_desc)
                
                assets = latest_release.get("assets", [])
                
                # 태그명에 온점(.)이 잘못 찍힌 경우(v.1.1.1 등)를 대비해 숫자/문자만 추출비교
                clean_latest = latest_version.replace(".", "")
                clean_current = self.current_version.replace(".", "")
                
                if latest_version and clean_latest != clean_current:
                    download_url = None
                    for asset in assets:
                        if asset['name'].endswith('.zip'):
                            download_url = asset['browser_download_url']
                            break
                    
                    if download_url:
                        self.update_available.emit(latest_version, full_description, download_url)
                    else:
                        self.update_available.emit(latest_version, full_description, "")
                else:
                    self.update_available.emit(self.current_version, full_description, "")
        except Exception as e:
            self.error_occurred.emit(str(e))

class UpdateDownloader(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            # ALYac 백신(ESTsoft)의 임시 폴더(CreatorTemp) 간섭을 피하기 위해 
            # 사용자 홈 디렉토리 밑에 전용 업데이트 폴더를 생성합니다.
            user_home = os.path.expanduser('~')
            temp_dir = os.path.join(user_home, ".autotax_update_temp")
            os.makedirs(temp_dir, exist_ok=True)
            zip_path = os.path.join(temp_dir, "update.zip")
            
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'TaxAuto-Updater'})
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                chunk_size = 1024 * 128
                
                with open(zip_path, 'wb') as file:
                    while True:
                        buffer = response.read(chunk_size)
                        if not buffer:
                            break
                        file.write(buffer)
                        downloaded += len(buffer)
                        if total_size > 0:
                            p = int((downloaded / total_size) * 100)
                            self.progress.emit(p)
                            
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            self.finished.emit(extract_dir)
            
        except Exception as e:
            self.error.emit(str(e))

def apply_update_and_restart(extracted_dir):
    if not getattr(sys, 'frozen', False):
        print("개발 환경에서는 업데이트 매크로가 작동하지 않습니다.")
        return

    current_exe = sys.executable
    current_dir = os.path.dirname(current_exe)
    
    # 압축된 파일 내부에서 TaxAuto.exe가 들어있는 진짜 폴더 찾기
    source_dir = extracted_dir
    for root, dirs, files in os.walk(extracted_dir):
        if "main.exe" in files or "TaxAuto.exe" in files:
            source_dir = root
            break
            
    bat_path = os.path.join(tempfile.gettempdir(), "tax_updater.bat")
    
    bat_content = f"""@echo off
echo =======================================
echo 강사관리 시스템 업데이트를 이식 중입니다.
echo 창을 닫지 마시고 잠시만 기다려주세요...
echo =======================================
title Tax Auto Updater
:wait_loop
timeout /t 2 /nobreak > NUL
del /f /q "{current_exe}" 2>NUL
if exist "{current_exe}" goto wait_loop

xcopy /s /e /y "{source_dir}\\*" "{current_dir}\\"
rmdir /s /q "%USERPROFILE%\\.autotax_update_temp" 2>NUL
start "" "{current_exe}"
del "%~f0"
"""
    with open(bat_path, "w", encoding="euc-kr") as f:
        f.write(bat_content)

    subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit(0)
