"""词本数据操作"""

from database.db import get_db, dict_from_row, dicts_from_rows
from datetime import datetime


class WordbookModel:
    """词本 CRUD"""

    @staticmethod
    def create(name):
        """创建新词本"""
        db = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = db.execute(
            'INSERT INTO wordbooks (name, created_at, updated_at) VALUES (?, ?, ?)',
            (name, now, now)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_all():
        """获取所有词本及其统计"""
        db = get_db()
        rows = db.execute('SELECT * FROM wordbooks ORDER BY updated_at DESC').fetchall()
        wordbooks = dicts_from_rows(rows)

        for wb in wordbooks:
            stats = db.execute('''
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN status='new' THEN 1 ELSE 0 END), 0) as new_count,
                    COALESCE(SUM(CASE WHEN status='learning' THEN 1 ELSE 0 END), 0) as learning_count,
                    COALESCE(SUM(CASE WHEN status='mastered' THEN 1 ELSE 0 END), 0) as mastered_count
                FROM words WHERE wordbook_id = ?
            ''', (wb['id'],)).fetchone()
            wb.update(dict(stats))
        return wordbooks

    @staticmethod
    def get_by_id(wordbook_id):
        """获取单个词本"""
        db = get_db()
        row = db.execute('SELECT * FROM wordbooks WHERE id = ?', (wordbook_id,)).fetchone()
        wb = dict_from_row(row)
        if wb:
            stats = db.execute('''
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN status='new' THEN 1 ELSE 0 END), 0) as new_count,
                    COALESCE(SUM(CASE WHEN status='learning' THEN 1 ELSE 0 END), 0) as learning_count,
                    COALESCE(SUM(CASE WHEN status='mastered' THEN 1 ELSE 0 END), 0) as mastered_count
                FROM words WHERE wordbook_id = ?
            ''', (wordbook_id,)).fetchone()
            wb.update(dict(stats))
        return wb

    @staticmethod
    def update_name(wordbook_id, name):
        """更新词本名称"""
        db = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.execute(
            'UPDATE wordbooks SET name = ?, updated_at = ? WHERE id = ?',
            (name, now, wordbook_id)
        )
        db.commit()

    @staticmethod
    def delete(wordbook_id):
        """删除词本（级联删除所有单词）"""
        db = get_db()
        db.execute('DELETE FROM wordbooks WHERE id = ?', (wordbook_id,))
        db.commit()
