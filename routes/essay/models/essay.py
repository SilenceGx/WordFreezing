"""作文数据操作"""

from database.db import get_db, dicts_from_rows


class EssayModel:

    @staticmethod
    def get_by_book(book_id):
        """获取作文本下的所有作文"""
        db = get_db()
        rows = db.execute(
            '''SELECT * FROM essays
               WHERE essay_book_id = ?
               ORDER BY created_at DESC''',
            (book_id,)
        ).fetchall()
        return dicts_from_rows(rows)

    @staticmethod
    def get_by_id(essay_id):
        """获取单篇作文"""
        db = get_db()
        row = db.execute(
            'SELECT * FROM essays WHERE id = ?',
            (essay_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(book_id, title, content, author='', summary=''):
        """创建作文"""
        db = get_db()
        cur = db.execute(
            'INSERT INTO essays (essay_book_id, title, author, content, summary) VALUES (?, ?, ?, ?, ?)',
            (book_id, title, author, content, summary)
        )
        # 更新作文本的更新时间
        db.execute(
            'UPDATE essay_books SET updated_at = datetime(\'now\',\'localtime\') WHERE id = ?',
            (book_id,)
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update(essay_id, title, author, content, summary=''):
        """更新作文"""
        db = get_db()
        db.execute(
            'UPDATE essays SET title = ?, author = ?, content = ?, summary = ? WHERE id = ?',
            (title, author, content, summary, essay_id)
        )
        db.commit()

    @staticmethod
    def delete(essay_id):
        """删除作文"""
        db = get_db()
        db.execute('DELETE FROM essays WHERE id = ?', (essay_id,))
        db.commit()
