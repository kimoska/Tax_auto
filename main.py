"""
AutoTax — 앱 진입점 (plan.md §8.1)
"""
import sys
import os

# 프로젝트 루트를 Python path에 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from core.firebase_auth import FirebaseAuth
from db.cloud_repository import CloudRepository
from core.crypto import CryptoManager
from gui.app import AutoTaxWindow
from gui.cloud_login_window import CloudLoginWindow


def setup_security() -> CryptoManager:
    """암호화 관리자 초기화 (.secret_key 자동 생성)"""
    return CryptoManager()


def main():
    # High DPI 스케일링 지원
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 기본 폰트 설정 (Pretendard 가용 시 사용, 없으면 시스템 폰트)
    font = QFont('Pretendard', 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    # 전역 스타일
    app.setStyleSheet("""
        QWidget {
            font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
        }
        QScrollArea {
            border: none;
        }
        QScrollBar:vertical {
            border: none;
            background: #F5F5F5;
            width: 8px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #C0C0C0;
            border-radius: 4px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: #A0A0A0;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
    """)

    # ★ 초기화 ★
    print("☁️ AutoTax 클라우드 버전 초기화 중...")
    auth = FirebaseAuth()
    login = CloudLoginWindow(auth)
    
    # 1) 로그인 창 실행
    if login.exec() != QDialog.Accepted:
        sys.exit(0)
        
    print("✅ 로그인 성공, 앱을 시작합니다.")
    
    # 2) 클라우드 리포지토리 생성
    repo = CloudRepository(auth)
    crypto = setup_security()

    # 메인 윈도우 생성 및 표시
    window = AutoTaxWindow(repo, crypto)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
