"""作文本数据操作"""

from database.db import get_db, dicts_from_rows


class EssayBookModel:

    @staticmethod
    def get_all():
        """获取所有作文本（含作文数）"""
        db = get_db()
        rows = db.execute(
            '''SELECT eb.*, COUNT(e.id) as essay_count
               FROM essay_books eb
               LEFT JOIN essays e ON e.essay_book_id = eb.id
               GROUP BY eb.id
               ORDER BY eb.updated_at DESC'''
        ).fetchall()
        return dicts_from_rows(rows)

    @staticmethod
    def get_by_id(book_id):
        """获取单个作文本"""
        db = get_db()
        row = db.execute(
            '''SELECT eb.*, COUNT(e.id) as essay_count
               FROM essay_books eb
               LEFT JOIN essays e ON e.essay_book_id = eb.id
               WHERE eb.id = ?
               GROUP BY eb.id''',
            (book_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(name):
        """创建作文本"""
        db = get_db()
        cur = db.execute('INSERT INTO essay_books (name) VALUES (?)', (name,))
        db.commit()
        return cur.lastrowid

    @staticmethod
    def update_name(book_id, name):
        """更新作文本名称"""
        db = get_db()
        db.execute(
            'UPDATE essay_books SET name = ?, updated_at = datetime(\'now\',\'localtime\') WHERE id = ?',
            (name, book_id)
        )
        db.commit()

    @staticmethod
    def delete(book_id):
        """删除作文本（级联删除作文）"""
        db = get_db()
        db.execute('DELETE FROM essay_books WHERE id = ?', (book_id,))
        db.commit()
