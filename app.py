"""WordFreezing — Flask 主应用入口

用法:
    conda activate wordfreezing
    python app.py
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file

from database.db import init_db, get_db, close_db, dict_from_row, dicts_from_rows
from models.wordbook import WordbookModel
from models.word import WordModel
from models.config import ConfigModel
from services.ai_service import test_connection
from routes.english import english_bp
from routes.math import math_bp
from routes.essay import essay_bp
from routes.essay.models.essay_book import EssayBookModel


def create_app():
    """Flask 应用工厂"""
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # 初始化数据库（CREATE TABLE IF NOT EXISTS，重复执行安全）
    init_db()

    # 注册蓝屏
    app.teardown_appcontext(close_db)

    # ===== 注册蓝图 =====
    app.register_blueprint(english_bp)
    app.register_blueprint(math_bp)
    app.register_blueprint(essay_bp)

    # ========== 首页 ==========
    @app.route('/')
    def index():
        """仪表盘"""
        wordbooks = WordbookModel.get_all()
        stats = WordModel.get_stats()
        today_count = WordModel.get_today_review_count()
        essay_books = EssayBookModel.get_all()
        return render_template('index.html',
                              wordbooks=wordbooks,
                              stats=stats,
                              today_count=today_count,
                              essay_books=essay_books)

    # ========== 统计页面 ==========
    @app.route('/stats')
    def stats():
        """统计页面"""
        wordbooks = WordbookModel.get_all()
        global_stats = WordModel.get_stats()

        # 计算学习天数
        db = get_db()
        days_row = db.execute(
            '''SELECT COUNT(DISTINCT last_review_date) as days FROM words
               WHERE last_review_date != '' AND status != 'new' '''
        ).fetchone()
        total_days = days_row['days'] if days_row else 0

        return render_template('stats.html',
                              wordbooks=wordbooks,
                              global_stats=global_stats,
                              total_days=total_days)

    # ========== 设置页面 ==========
    @app.route('/settings')
    def settings():
        """设置页面"""
        config = ConfigModel.get_all()
        return render_template('settings.html', config=config)

    @app.route('/settings/save', methods=['POST'])
    def settings_save():
        """保存配置"""
        data = request.form.to_dict()
        ConfigModel.update_batch(data)
        return jsonify({'success': True, 'message': '配置已保存'})

    @app.route('/settings/test-connection', methods=['POST'])
    def settings_test_connection():
        """测试 AI 连接"""
        result = test_connection()
        return jsonify(result)

    # ========== 数据管理 ==========
    @app.route('/settings/backup', methods=['POST'])
    def settings_backup():
        """导出完整数据备份"""
        db = get_db()
        wordbooks = dicts_from_rows(db.execute('SELECT * FROM wordbooks').fetchall())
        words = dicts_from_rows(db.execute('SELECT * FROM words').fetchall())
        configs = dicts_from_rows(db.execute('SELECT * FROM config').fetchall())

        essay_books = dicts_from_rows(db.execute('SELECT * FROM essay_books').fetchall())
        essays = dicts_from_rows(db.execute('SELECT * FROM essays').fetchall())

        backup = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'wordbooks': wordbooks,
            'words': words,
            'configs': configs,
            'essay_books': essay_books,
            'essays': essays,
        }
        filename = f"wordfreezing_backup_{datetime.now().strftime('%Y%m%d')}.json"
        resp = jsonify(backup)
        resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    @app.route('/settings/restore', methods=['POST'])
    def settings_restore():
        """导入数据备份"""
        file = request.files.get('backup_file')
        if not file:
            return jsonify({'success': False, 'message': '请上传备份文件'})

        try:
            data = json.loads(file.read().decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return jsonify({'success': False, 'message': '备份文件格式错误'})

        db = get_db()
        try:
            # 清空现有数据
            db.execute('DELETE FROM essays')
            db.execute('DELETE FROM essay_books')
            db.execute('DELETE FROM words')
            db.execute('DELETE FROM wordbooks')
            db.execute('DELETE FROM config')

            # 导入词本
            for wb in data.get('wordbooks', []):
                db.execute('INSERT INTO wordbooks (id, name, mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                          (wb['id'], wb['name'], wb.get('mode', 'writing'),
                           wb.get('created_at', datetime.now().isoformat()),
                           wb.get('updated_at', datetime.now().isoformat())))

            # 导入单词
            for w in data.get('words', []):
                db.execute(
                    '''INSERT INTO words (id, wordbook_id, word, pos, phonetic, definition, examples, input_example, status,
                       review_stage, correct_count, last_review_date, next_review_date, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (w['id'], w['wordbook_id'], w['word'], w.get('pos', ''), w.get('phonetic', ''),
                     w.get('definition', ''), w.get('examples', '[]'), w.get('input_example', ''),
                     w.get('status', 'new'),
                     w.get('review_stage', 0), w.get('correct_count', 0),
                     w.get('last_review_date', ''), w.get('next_review_date', ''), w.get('created_at', ''))
                )

            # 导入作文本
            for eb in data.get('essay_books', []):
                db.execute(
                    'INSERT INTO essay_books (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)',
                    (eb['id'], eb['name'],
                     eb.get('created_at', datetime.now().isoformat()),
                     eb.get('updated_at', datetime.now().isoformat())))

            # 导入作文
            for e in data.get('essays', []):
                db.execute(
                    'INSERT INTO essays (id, essay_book_id, title, author, content, summary, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (e['id'], e['essay_book_id'], e['title'], e.get('author', ''),
                     e['content'], e.get('summary', ''), e.get('created_at', '')))

            # 导入配置
            for c in data.get('configs', []):
                db.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)',
                          (c['key'], c['value']))

            db.commit()
            return jsonify({'success': True, 'message': '数据恢复成功'})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'message': f'恢复失败: {str(e)}'})

    return app


if __name__ == '__main__':
    app = create_app()

    print("=" * 50)
    print("  WordFreezing 启动!")
    print("  访问地址: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
