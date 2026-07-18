"""题目数据操作"""
from database.db import get_db, dict_from_row, dicts_from_rows
from datetime import datetime


class ProblemModel:
    """题目 CRUD"""

    @staticmethod
    def create(book_id, problem_text, solution_text):
        """创建新题目"""
        db = get_db()
        cursor = db.execute(
            'INSERT INTO problems (book_id, problem_text, solution_text) VALUES (?, ?, ?)',
            (book_id, problem_text, solution_text)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(problem_id):
        """获取单个题目（含其所有关键节点）"""
        db = get_db()
        row = db.execute('SELECT * FROM problems WHERE id = ?', (problem_id,)).fetchone()
        problem = dict_from_row(row)
        if problem:
            nodes = dicts_from_rows(db.execute(
                'SELECT * FROM key_nodes WHERE problem_id = ? ORDER BY node_order ASC',
                (problem_id,)
            ).fetchall())
            problem['nodes'] = nodes
        return problem

    @staticmethod
    def get_by_book(book_id, page=1, per_page=50):
        """获取题本中的题目列表"""
        db = get_db()
        count_row = db.execute(
            'SELECT COUNT(*) as cnt FROM problems WHERE book_id = ?',
            (book_id,)
        ).fetchone()
        total = count_row['cnt']
        offset = (page - 1) * per_page
        rows = db.execute(
            'SELECT * FROM problems WHERE book_id = ? ORDER BY id ASC LIMIT ? OFFSET ?',
            (book_id, per_page, offset)
        ).fetchall()
        problems = dicts_from_rows(rows)
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            'problems': problems,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
        }

    @staticmethod
    def get_due_review_problems(book_id, limit=5):
        """获取包含到期节点的题目"""
        db = get_db()
        today = datetime.now().strftime('%Y-%m-%d')
        rows = db.execute('''
            SELECT DISTINCT p.* FROM problems p
            JOIN key_nodes kn ON kn.problem_id = p.id
            WHERE p.book_id = ? AND kn.status = 'learning' AND kn.next_review_date <= ?
            ORDER BY kn.next_review_date ASC
            LIMIT ?
        ''', (book_id, today, limit)).fetchall()
        return dicts_from_rows(rows)

    @staticmethod
    def get_new_problems(book_id, limit=20):
        """获取未学习的题目"""
        db = get_db()
        rows = db.execute(
            'SELECT * FROM problems WHERE book_id = ? AND status = \'new\' ORDER BY id ASC LIMIT ?',
            (book_id, limit)
        ).fetchall()
        return dicts_from_rows(rows)

    @staticmethod
    def get_due_nodes_for_problem(problem_id):
        """获取题目中到期的关键节点"""
        db = get_db()
        today = datetime.now().strftime('%Y-%m-%d')
        rows = db.execute('''
            SELECT * FROM key_nodes
            WHERE problem_id = ? AND status = 'learning' AND next_review_date <= ?
            ORDER BY node_order ASC
        ''', (problem_id, today)).fetchall()
        return dicts_from_rows(rows)

    @staticmethod
    def get_all_nodes_for_problem(problem_id):
        """获取题目的所有关键节点（新题模式）"""
        db = get_db()
        rows = db.execute(
            'SELECT * FROM key_nodes WHERE problem_id = ? ORDER BY node_order ASC',
            (problem_id,)
        ).fetchall()
        return dicts_from_rows(rows)

    @staticmethod
    def delete(problem_id):
        """删除题目（级联删除节点）"""
        db = get_db()
        db.execute('DELETE FROM problems WHERE id = ?', (problem_id,))
        db.commit()

    @staticmethod
    def sync_problem_status(problem_id):
        """同步题目状态：
        所有节点 mastered → problems.status = 'mastered'
        否则                → problems.status = 'learning'（从 new 转 learning）
        """
        db = get_db()
        remaining = db.execute(
            "SELECT COUNT(*) as cnt FROM key_nodes WHERE problem_id = ? AND status != 'mastered'",
            (problem_id,)
        ).fetchone()
        if remaining and remaining['cnt'] == 0:
            db.execute(
                "UPDATE problems SET status = 'mastered' WHERE id = ?",
                (problem_id,)
            )
            db.commit()
            return 'mastered'
        else:
            # 有未掌握的节点 → 至少是 learning
            db.execute(
                "UPDATE problems SET status = 'learning' WHERE id = ? AND status = 'new'",
                (problem_id,)
            )
            db.commit()
            return 'learning'
