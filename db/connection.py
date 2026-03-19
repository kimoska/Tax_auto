"""
AutoTax — SQLite 커넥션 관리 (싱글턴)
"""
import sqlite3
import os
import threading


class DatabaseConnection:
    """SQLite 싱글턴 커넥션 관리자"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path=None):
        if self._initialized:
            return
        self._initialized = True

        if db_path is None:
            # 실행 파일과 같은 디렉토리에 autotax.db 생성
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'autotax.db')

        self.db_path = db_path
        self._conn = None

    def get_connection(self) -> sqlite3.Connection:
        """커넥션 반환 (lazy initialization)"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # WAL 모드: 읽기/쓰기 동시 성능 향상
            self._conn.execute("PRAGMA journal_mode=WAL")
            # 외래키 제약조건 활성화
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """SQL 실행 + 자동 커밋"""
        conn = self.get_connection()
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """다중 행 INSERT/UPDATE"""
        conn = self.get_connection()
        cursor = conn.executemany(sql, params_list)
        conn.commit()
        return cursor

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        """단일 행 조회 → dict 또는 None"""
        conn = self.get_connection()
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        """다중 행 조회 → list[dict]"""
        conn = self.get_connection()
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """커넥션 종료"""
        if self._conn:
            self._conn.close()
            self._conn = None

    @classmethod
    def reset(cls):
        """싱글턴 인스턴스 초기화 (테스트용)"""
        with cls._lock:
            if cls._instance and cls._instance._conn:
                cls._instance._conn.close()
            cls._instance = None
