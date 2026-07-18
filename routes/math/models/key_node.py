"""关键节点数据操作 + 间隔重复"""
from database.db import get_db, dict_from_row, dicts_from_rows
from datetime import datetime, timedelta


class KeyNodeModel:
    """关键节点 CRUD + 复习调度"""

    @staticmethod
    def create(problem_id, node_order, title, description, formula=''):
        """创建关键节点"""
        db = get_db()
        cursor = db.execute(
            '''INSERT INTO key_nodes (problem_id, node_order, title, description, formula)
               VALUES (?, ?, ?, ?, ?)''',
            (problem_id, node_order, title, description, formula)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def batch_create(problem_id, nodes):
        """批量创建关键节点
        nodes: [{'node_order': 1, 'title': '...', 'description': '...', 'formula': '...'}, ...]
        """
        db = get_db()
        for n in nodes:
            db.execute(
                '''INSERT INTO key_nodes (problem_id, node_order, title, description, formula)
                   VALUES (?, ?, ?, ?, ?)''',
                (problem_id, n['node_order'], n['title'], n['description'], n.get('formula', ''))
            )
        db.commit()

    @staticmethod
    def get_by_id(node_id):
        """获取单个节点"""
        db = get_db()
        row = db.execute('SELECT * FROM key_nodes WHERE id = ?', (node_id,)).fetchone()
        return dict_from_row(row)

    @staticmethod
    def get_by_problem(problem_id):
        """获取题目的所有节点"""
        db = get_db()
        rows = db.execute(
            'SELECT * FROM key_nodes WHERE problem_id = ? ORDER BY node_order ASC',
            (problem_id,)
        ).fetchall()
        return dicts_from_rows(rows)

    # ===== 间隔重复算法（与英语模块一致） =====
    @staticmethod
    def _today_str():
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def _calc_next_review(stage):
        today = datetime.now()
        if stage == 0:
            next_date = today + timedelta(days=1)
        elif stage == 1:
            next_date = today + timedelta(days=3)
        elif stage == 2:
            next_date = today + timedelta(days=7)
        else:
            next_date = today + timedelta(days=7)
        return next_date.strftime('%Y-%m-%d')

    @staticmethod
    def process_review(node_id, hit):
        """处理单个节点的复习结果
        逻辑与 process_review 保持一致：
          new → hit → mastered
          new → miss → learning(stage0, 1天)
          learning → hit → stage+1
          learning → miss → stage0
          stage2 hit → mastered
        """
        node = KeyNodeModel.get_by_id(node_id)
        if not node:
            return {'error': '节点不存在'}

        today = KeyNodeModel._today_str()
        status = node['status']
        stage = node['review_stage']

        if status == 'new':
            if hit:
                # new → mastered
                db = get_db()
                db.execute(
                    '''UPDATE key_nodes SET status='mastered', review_stage=0,
                       correct_count=1, last_review_date=?, next_review_date='' WHERE id=?''',
                    (today, node_id)
                )
                db.commit()
                from routes.math.models.problem import ProblemModel
                ProblemModel.sync_problem_status(node['problem_id'])
                return {'status': 'mastered', 'action': '✅ 首战告捷！', 'stage': 0}
            else:
                # new → learning(stage0)
                next_date = KeyNodeModel._calc_next_review(0)
                db = get_db()
                db.execute(
                    '''UPDATE key_nodes SET status='learning', review_stage=0,
                       correct_count=0, last_review_date=?, next_review_date=? WHERE id=?''',
                    (today, next_date, node_id)
                )
                db.commit()
                from routes.math.models.problem import ProblemModel
                ProblemModel.sync_problem_status(node['problem_id'])
                return {'status': 'learning', 'action': '进入复习队列', 'stage': 0, 'next_review': next_date}

        elif status == 'learning':
            if not hit:
                next_date = KeyNodeModel._calc_next_review(0)
                db = get_db()
                db.execute(
                    '''UPDATE key_nodes SET review_stage=0, correct_count=0,
                       last_review_date=?, next_review_date=? WHERE id=?''',
                    (today, next_date, node_id)
                )
                db.commit()
                return {'status': 'learning', 'action': '退回起点，继续复习', 'stage': 0, 'next_review': next_date}

            # 通过
            # 同一天防重复
            if node['last_review_date'] == today and node['correct_count'] > 0:
                return {'status': 'learning', 'action': '今日已通过', 'stage': stage,
                        'next_review': node.get('next_review_date', ''), 'skipped': True}

            db = get_db()
            if stage == 0:
                next_date = KeyNodeModel._calc_next_review(1)
                db.execute(
                    '''UPDATE key_nodes SET review_stage=1, correct_count=correct_count+1,
                       last_review_date=?, next_review_date=? WHERE id=?''',
                    (today, next_date, node_id)
                )
                db.commit()
                return {'status': 'learning', 'action': '通过还需巩固 💪', 'stage': 1, 'next_review': next_date}
            elif stage == 1:
                next_date = KeyNodeModel._calc_next_review(2)
                db.execute(
                    '''UPDATE key_nodes SET review_stage=2, correct_count=correct_count+1,
                       last_review_date=?, next_review_date=? WHERE id=?''',
                    (today, next_date, node_id)
                )
                db.commit()
                return {'status': 'learning', 'action': '通过还需巩固 💪', 'stage': 2, 'next_review': next_date}
            elif stage == 2:
                db.execute(
                    '''UPDATE key_nodes SET status='mastered', review_stage=3, correct_count=correct_count+1,
                       last_review_date=?, next_review_date='' WHERE id=?''',
                    (today, node_id)
                )
                db.commit()
                # 检查题目是否全部 mastered
                from routes.math.models.problem import ProblemModel
                ProblemModel.sync_problem_status(node['problem_id'])
                return {'status': 'mastered', 'action': '🎉 彻底掌握！', 'stage': 3}

        elif status == 'mastered':
            return {'status': 'mastered', 'action': '已掌握', 'stage': 3}

        return {'status': status, 'action': '未知状态', 'stage': stage}

    @staticmethod
    def batch_review(problem_id, node_hits):
        """批量处理题目的节点评判结果
        node_hits: [{node_id: int, hit: bool}, ...]
        返回: [{node_id, result}, ...]
        """
        results = []
        for item in node_hits:
            result = KeyNodeModel.process_review(item['node_id'], item['hit'])
            results.append({**result, 'node_id': item['node_id']})
        return results
