"""数据库连接管理"""

import sqlite3
import os
from flask import g

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'wordfreezing.db')
SCHEMA_PATH = os.path.join(DATABASE_DIR, 'schema.sql')


def get_db():
    """获取当前请求的数据库连接（flask g 上下文）"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
        _ensure_tables(g.db)
        _run_migrations(g.db)
    return g.db


def _ensure_tables(db):
    """确保数据库表存在（不存在则初始化）"""
    try:
        row = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='wordbooks'"
        ).fetchone()
        if not row:
            # 表不存在，执行建表
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                db.executescript(f.read())
            db.commit()
    except Exception:
        # SQLite 可能还没连接或文件访问出错
        pass


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库（建表 + 迁移）"""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    _run_migrations(db)
    db.commit()
    db.close()


def _run_migrations(db):
    """执行数据库迁移（兼容旧库新增字段）"""
    # 迁移 1: wordbooks 表添加 mode 列
    try:
        db.execute("ALTER TABLE wordbooks ADD COLUMN mode TEXT DEFAULT 'writing'")
    except sqlite3.OperationalError:
        pass  # 列已存在

    # 迁移 2: words 表添加 input_example 列
    try:
        db.execute("ALTER TABLE words ADD COLUMN input_example TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # 列已存在


def dict_from_row(row):
    """将 sqlite3.Row 转为 dict"""
    if row is None:
        return None
    return dict(row)


def dicts_from_rows(rows):
    """将 sqlite3.Row 列表转为 dict 列表"""
    return [dict(row) for row in rows]
