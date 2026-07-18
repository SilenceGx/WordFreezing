"""题本数据操作"""
from database.db import get_db, dict_from_row, dicts_from_rows
from datetime import datetime


class ProblemBookModel:
    """题本 CRUD"""

    @staticmethod
    def create(name):
        """创建新题本"""
        db = get_db()
        cursor = db.execute(
            'INSERT INTO problem_books (name) VALUES (?)',
            (name,)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_all():
        """获取所有题本及其统计"""
        db = get_db()
        rows = db.execute(
            'SELECT * FROM problem_books ORDER BY created_at DESC'
        ).fetchall()
        books = dicts_from_rows(rows)

        for bk in books:
            stats = db.execute('''
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN p.status='new' THEN 1 ELSE 0 END), 0) as new_count,
                    COALESCE(SUM(CASE WHEN p.status='learning' THEN 1 ELSE 0 END), 0) as learning_count,
                    COALESCE(SUM(CASE WHEN p.status='mastered' THEN 1 ELSE 0 END), 0) as mastered_count
                FROM problems p WHERE p.book_id = ?
            ''', (bk['id'],)).fetchone()
            bk.update(dict(stats))
        return books

    @staticmethod
    def get_by_id(book_id):
        """获取单个题本"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM problem_books WHERE id = ?',
            (book_id,)
        ).fetchone()
        bk = dict_from_row(row)
        if bk:
            stats = db.execute('''
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN p.status='new' THEN 1 ELSE 0 END), 0) as new_count,
                    COALESCE(SUM(CASE WHEN p.status='learning' THEN 1 ELSE 0 END), 0) as learning_count,
                    COALESCE(SUM(CASE WHEN p.status='mastered' THEN 1 ELSE 0 END), 0) as mastered_count
                FROM problems p WHERE p.book_id = ?
            ''', (book_id,)).fetchone()
            bk.update(dict(stats))
        return bk

    @staticmethod
    def get_today_review_count(book_id=None):
        """获取今日待复习的关键节点数"""
        db = get_db()
        today = datetime.now().strftime('%Y-%m-%d')
        if book_id:
            row = db.execute('''
                SELECT COUNT(*) as cnt FROM key_nodes kn
                JOIN problems p ON kn.problem_id = p.id
                WHERE p.book_id = ? AND kn.status='learning'
                  AND kn.next_review_date <= ?
            ''', (book_id, today)).fetchone()
        else:
            row = db.execute('''
                SELECT COUNT(*) as cnt FROM key_nodes
                WHERE status='learning' AND next_review_date <= ?
            ''', (today,)).fetchone()
        return row['cnt']

    @staticmethod
    def get_stats():
        """获取全局统计"""
        db = get_db()
        row = db.execute('''
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN status='new' THEN 1 ELSE 0 END), 0) as new_count,
                COALESCE(SUM(CASE WHEN status='learning' THEN 1 ELSE 0 END), 0) as learning_count,
                COALESCE(SUM(CASE WHEN status='mastered' THEN 1 ELSE 0 END), 0) as mastered_count
            FROM problems
        ''').fetchone()
        return dict(row)

    @staticmethod
    def update_name(book_id, name):
        """更新题本名称"""
        db = get_db()
        db.execute(
            'UPDATE problem_books SET name = ? WHERE id = ?',
            (name, book_id)
        )
        db.commit()

    @staticmethod
    def delete(book_id):
        """删除题本（级联删除所有题目和节点）"""
        db = get_db()
        db.execute('DELETE FROM problem_books WHERE id = ?', (book_id,))
        db.commit()
