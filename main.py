"""
AutoTax — 앱 진입점 (plan.md §8.1)
"""
import sys
import os

# 프로젝트 루트를 Python path에 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from db.connection import DatabaseConnection
from db.schema import initialize_database
from db.repository import Repository
from core.crypto import CryptoManager
from gui.app import AutoTaxWindow


def setup_database() -> Repository:
    """데이터베이스 초기화 및 Repository 생성"""
    db = DatabaseConnection()
    initialize_database(db)
    return Repository(db)


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
    print("🔧 AutoTax 초기화 중...")
    crypto = setup_security()
    repo = setup_database()
    print("✅ 초기화 완료")

    # 메인 윈도우 생성 및 표시
    window = AutoTaxWindow(repo, crypto)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
