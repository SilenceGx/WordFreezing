"""单词数据操作"""

from database.db import get_db, dict_from_row, dicts_from_rows
import json
from datetime import datetime


class WordModel:
    """单词 CRUD"""

    @staticmethod
    def create(wordbook_id, word, pos='', phonetic='', definition='', examples=None, input_example=''):
        """创建单词"""
        db = get_db()
        examples_json = json.dumps(examples or [], ensure_ascii=False)
        cursor = db.execute(
            '''INSERT INTO words (wordbook_id, word, pos, phonetic, definition, examples, input_example)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (wordbook_id, word, pos, phonetic, definition, examples_json, input_example)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def batch_create(words_data):
        """批量创建单词
        words_data: list of dicts
        """
        db = get_db()
        for w in words_data:
            examples_json = json.dumps(w.get('examples', []), ensure_ascii=False)
            db.execute(
                '''INSERT INTO words (wordbook_id, word, pos, phonetic, definition, examples, input_example)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (w['wordbook_id'], w['word'], w.get('pos', ''),
                 w.get('phonetic', ''), w.get('definition', ''),
                 examples_json, w.get('input_example', ''))
            )
        db.commit()

    @staticmethod
    def get_by_wordbook(wordbook_id, search='', status='', page=1, per_page=50):
        """获取词本中的单词列表（分页 + 搜索 + 筛选）"""
        db = get_db()
        conditions = ['wordbook_id = ?']
        params = [wordbook_id]

        if search:
            conditions.append('word LIKE ?')
            params.append(f'%{search}%')
        if status and status in ('new', 'learning', 'mastered'):
            conditions.append('status = ?')
            params.append(status)

        # 总计数
        count_row = db.execute(
            f'SELECT COUNT(*) as cnt FROM words WHERE {" AND ".join(conditions)}',
            params
        ).fetchone()
        total = count_row['cnt']

        # 分页
        offset = (page - 1) * per_page
        rows = db.execute(
            f'SELECT * FROM words WHERE {" AND ".join(conditions)} ORDER BY id ASC LIMIT ? OFFSET ?',
            params + [per_page, offset]
        ).fetchall()

        words = dicts_from_rows(rows)
        for w in words:
            try:
                w['examples'] = json.loads(w['examples'])
            except (json.JSONDecodeError, TypeError):
                w['examples'] = []

        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            'words': words,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
        }

    @staticmethod
    def get_by_id(word_id):
        """获取单个单词"""
        db = get_db()
        row = db.execute('SELECT * FROM words WHERE id = ?', (word_id,)).fetchone()
        w = dict_from_row(row)
        if w:
            try:
                w['examples'] = json.loads(w['examples'])
            except (json.JSONDecodeError, TypeError):
                w['examples'] = []
        return w

    @staticmethod
    def update(word_id, **kwargs):
        """更新单词字段"""
        db = get_db()
        allowed = {'word', 'pos', 'phonetic', 'definition', 'examples', 'input_example',
                   'status', 'review_stage', 'correct_count',
                   'last_review_date', 'next_review_date'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return

        if 'examples' in updates and isinstance(updates['examples'], (list, tuple)):
            updates['examples'] = json.dumps(updates['examples'], ensure_ascii=False)

        set_clause = ', '.join(f'{k} = ?' for k in updates)
        values = list(updates.values()) + [word_id]
        db.execute(f'UPDATE words SET {set_clause} WHERE id = ?', values)
        db.commit()

    @staticmethod
    def delete(word_id):
        """删除单词"""
        db = get_db()
        db.execute('DELETE FROM words WHERE id = ?', (word_id,))
        db.commit()

    @staticmethod
    def batch_delete(word_ids):
        """批量删除单词"""
        if not word_ids:
            return
        db = get_db()
        placeholders = ','.join('?' * len(word_ids))
        db.execute(f'DELETE FROM words WHERE id IN ({placeholders})', word_ids)
        db.commit()

    @staticmethod
    def batch_update_status(word_ids, status):
        """批量更新单词状态"""
        if not word_ids:
            return
        db = get_db()
        placeholders = ','.join('?' * len(word_ids))
        db.execute(
            f'UPDATE words SET status = ? WHERE id IN ({placeholders})',
            [status] + word_ids
        )
        db.commit()

    @staticmethod
    def get_due_reviews(wordbook_id, limit=50):
        """获取今日到期的复习单词（先复习再学新词）"""
        db = get_db()
        today = datetime.now().strftime('%Y-%m-%d')
        rows = db.execute('''
            SELECT * FROM words
            WHERE wordbook_id = ?
              AND status = 'learning'
              AND next_review_date <= ?
            ORDER BY next_review_date ASC
            LIMIT ?
        ''', (wordbook_id, today, limit)).fetchall()
        words = dicts_from_rows(rows)
        for w in words:
            try:
                w['examples'] = json.loads(w['examples'])
            except (json.JSONDecodeError, TypeError):
                w['examples'] = []
        return words

    @staticmethod
    def get_new_words(wordbook_id, limit=20):
        """获取未学习的单词"""
        db = get_db()
        rows = db.execute('''
            SELECT * FROM words
            WHERE wordbook_id = ? AND status = 'new'
            ORDER BY id ASC
            LIMIT ?
        ''', (wordbook_id, limit)).fetchall()
        words = dicts_from_rows(rows)
        for w in words:
            try:
                w['examples'] = json.loads(w['examples'])
            except (json.JSONDecodeError, TypeError):
                w['examples'] = []
        return words

    @staticmethod
    def get_stats(wordbook_id=None):
        """获取全局统计"""
        db = get_db()
        if wordbook_id:
            row = db.execute('''
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN status='new' THEN 1 ELSE 0 END), 0) as new_count,
                    COALESCE(SUM(CASE WHEN status='learning' THEN 1 ELSE 0 END), 0) as learning_count,
                    COALESCE(SUM(CASE WHEN status='mastered' THEN 1 ELSE 0 END), 0) as mastered_count
                FROM words WHERE wordbook_id = ?
            ''', (wordbook_id,)).fetchone()
        else:
            row = db.execute('''
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN status='new' THEN 1 ELSE 0 END), 0) as new_count,
                    COALESCE(SUM(CASE WHEN status='learning' THEN 1 ELSE 0 END), 0) as learning_count,
                    COALESCE(SUM(CASE WHEN status='mastered' THEN 1 ELSE 0 END), 0) as mastered_count
                FROM words
            ''').fetchone()
        return dict(row)

    @staticmethod
    def get_today_review_count(wordbook_id=None):
        """获取今日待复习单词数"""
        db = get_db()
        today = datetime.now().strftime('%Y-%m-%d')
        if wordbook_id:
            row = db.execute(
                '''SELECT COUNT(*) as cnt FROM words
                   WHERE wordbook_id = ? AND status='learning' AND next_review_date <= ?''',
                (wordbook_id, today)
            ).fetchone()
        else:
            row = db.execute(
                '''SELECT COUNT(*) as cnt FROM words
                   WHERE status='learning' AND next_review_date <= ?''',
                (today,)
            ).fetchone()
        return row['cnt']
