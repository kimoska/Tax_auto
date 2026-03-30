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
            req = urllib.request.Request(REPO_API_URL, headers={'User-Agent': 'TaxAuto-Updater'})
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get("tag_name", "")
                description = data.get("body", "최신 업데이트 내역이 없습니다.")
                assets = data.get("assets", [])
                
                if latest_version and latest_version != self.current_version:
                    download_url = None
                    for asset in assets:
                        if asset['name'].endswith('.zip'):
                            download_url = asset['browser_download_url']
                            break
                    
                    if download_url:
                        self.update_available.emit(latest_version, description, download_url)
                else:
                    # No update, but we can emit the description anyway to update Home screen
                    self.update_available.emit(self.current_version, description, "")
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
            temp_dir = tempfile.mkdtemp()
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
start "" "{current_exe}"
del "%~f0"
"""
    with open(bat_path, "w", encoding="euc-kr") as f:
        f.write(bat_content)

    subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit(0)
