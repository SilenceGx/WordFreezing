"""WordFreezing — Flask 主应用入口

用法:
    conda activate wordfreezing
    python app.py
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file

from database.db import init_db, get_db, close_db, dict_from_row, dicts_from_rows
from models.wordbook import WordbookModel
from models.word import WordModel
from models.config import ConfigModel
from services.ai_service import judge_sentence, judge_translation, batch_complete, test_connection, generate_examples
from services.import_service import parse_txt, parse_manual, process_import, confirm_import
from services.review_service import process_review, mark_mastered, reset_word


def create_app():
    """Flask 应用工厂"""
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # 初始化数据库
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'wordfreezing.db')
    if not os.path.exists(db_path):
        print(f"[初始化] 首次运行，创建数据库: {db_path}")
        init_db()
        print("[初始化] 数据库初始化完成")
    else:
        # 验证数据库是否有效（有表结构），避免空/损坏文件导致表不存在
        import sqlite3
        try:
            _check = sqlite3.connect(db_path)
            _tables = _check.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='wordbooks'"
            ).fetchall()
            _check.close()
            if not _tables:
                print(f"[初始化] 数据库文件存在但缺少表，重新初始化...")
                os.remove(db_path)
                init_db()
                print("[初始化] 数据库重新初始化完成")
        except Exception as _e:
            print(f"[初始化] 数据库检查失败，重新初始化: {_e}")
            try:
                os.remove(db_path)
            except Exception:
                pass
            init_db()
            print("[初始化] 数据库重新初始化完成")

    # 注册 teardown
    app.teardown_appcontext(close_db)

    # ========== 首页 ==========
    @app.route('/')
    def index():
        """仪表盘"""
        wordbooks = WordbookModel.get_all()
        stats = WordModel.get_stats()
        today_count = WordModel.get_today_review_count()
        return render_template('index.html',
                             wordbooks=wordbooks,
                             stats=stats,
                             today_count=today_count)

    # ========== 词本操作 ==========
    @app.route('/wordbook/create', methods=['POST'])
    def wordbook_create():
        """创建词本"""
        name = request.form.get('name', '').strip()
        mode = request.form.get('mode', 'writing')
        if not name:
            return jsonify({'success': False, 'message': '请输入词本名称'})
        if mode not in ('writing', 'translation'):
            mode = 'writing'
        wordbook_id = WordbookModel.create(name, mode=mode)
        return jsonify({'success': True, 'message': '创建成功', 'id': wordbook_id})

    @app.route('/wordbook/<int:wordbook_id>')
    def wordbook_detail(wordbook_id):
        """词本总览"""
        wb = WordbookModel.get_by_id(wordbook_id)
        if not wb:
            return render_template('error.html', message='词本不存在'), 404

        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)
        data = WordModel.get_by_wordbook(wordbook_id, search=search, status=status, page=page)
        return render_template('wordbook.html', wordbook=wb, data=data,
                             search=search, filter_status=status)

    @app.route('/wordbook/<int:wordbook_id>/edit', methods=['POST'])
    def wordbook_edit(wordbook_id):
        """编辑词本名称"""
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'message': '请输入词本名称'})
        WordbookModel.update_name(wordbook_id, name)
        return jsonify({'success': True, 'message': '更新成功'})

    @app.route('/wordbook/<int:wordbook_id>/delete', methods=['POST'])
    def wordbook_delete(wordbook_id):
        """删除词本"""
        WordbookModel.delete(wordbook_id)
        return jsonify({'success': True, 'message': '已删除'})

    # ========== 单词操作 ==========
    @app.route('/word/<int:word_id>/update', methods=['POST'])
    def word_update(word_id):
        """更新单词信息"""
        data = request.form.to_dict()
        word = WordModel.get_by_id(word_id)
        if not word:
            return jsonify({'success': False, 'message': '单词不存在'})

        allowed_fields = {'word', 'pos', 'phonetic', 'definition', 'examples'}
        updates = {}
        for key in allowed_fields:
            if key in data:
                updates[key] = data[key]

        if 'examples' in updates:
            try:
                examples = json.loads(updates['examples'])
                if isinstance(examples, list):
                    updates['examples'] = examples
            except (json.JSONDecodeError, TypeError):
                pass

        WordModel.update(word_id, **updates)
        return jsonify({'success': True, 'message': '更新成功'})

    @app.route('/word/<int:word_id>/delete', methods=['POST'])
    def word_delete(word_id):
        """删除单词"""
        WordModel.delete(word_id)
        return jsonify({'success': True, 'message': '已删除'})

    @app.route('/wordbook/<int:wordbook_id>/words/batch', methods=['POST'])
    def words_batch(wordbook_id):
        """批量操作"""
        action = request.form.get('action', '')
        word_ids = request.form.getlist('word_ids[]')
        word_ids = [int(x) for x in word_ids if x.isdigit()]

        if not word_ids:
            return jsonify({'success': False, 'message': '请选择单词'})

        if action == 'mastered':
            WordModel.batch_update_status(word_ids, 'mastered')
            return jsonify({'success': True, 'message': f'已斩 {len(word_ids)} 个单词'})
        elif action == 'reset':
            WordModel.batch_update_status(word_ids, 'new')
            return jsonify({'success': True, 'message': f'已恢复 {len(word_ids)} 个单词'})
        elif action == 'delete':
            WordModel.batch_delete(word_ids)
            return jsonify({'success': True, 'message': f'已删除 {len(word_ids)} 个单词'})

        return jsonify({'success': False, 'message': '未知操作'})

    # ========== 学习流程 ==========
    @app.route('/learn/<int:wordbook_id>')
    def learn(wordbook_id):
        """学习页面"""
        wb = WordbookModel.get_by_id(wordbook_id)
        if not wb:
            return render_template('error.html', message='词本不存在'), 404
        return render_template('learn.html', wordbook=wb, wordbook_mode=wb.get('mode', 'writing'))

    @app.route('/api/learn/next/<int:wordbook_id>')
    def learn_next_word(wordbook_id):
        """获取下一个要学习的单词（先复习再新词）"""
        # 获取词本模式
        wb = WordbookModel.get_by_id(wordbook_id)
        wb_mode = wb.get('mode', 'writing') if wb else 'writing'

        # 1. 先查出今日到期复习
        due = WordModel.get_due_reviews(wordbook_id, limit=1)
        if due:
            w = due[0]
            return jsonify({'word': w, 'mode': 'review', 'wordbook_mode': wb_mode})

        # 2. 再取出新词
        new_words = WordModel.get_new_words(wordbook_id, limit=1)
        if new_words:
            w = new_words[0]
            return jsonify({'word': w, 'mode': 'new', 'wordbook_mode': wb_mode})

        # 3. 全部学完
        # 检查是否有 learning 但非今日到期的词
        db = get_db()
        row = db.execute(
            '''SELECT COUNT(*) as cnt FROM words
               WHERE wordbook_id=? AND status='learning' AND next_review_date > ?''',
            (wordbook_id, datetime.now().strftime('%Y-%m-%d'))
        ).fetchone()
        pending = row['cnt'] if row else 0

        if pending > 0:
            return jsonify({'done': True, 'wordbook_mode': wb_mode,
                          'message': f'今日学习完成！还有 {pending} 个单词待复习（尚未到期）。'})
        else:
            return jsonify({'done': True, 'wordbook_mode': wb_mode,
                          'message': '🎉 所有单词已掌握或已学完！'})

    @app.route('/api/learn/submit', methods=['POST'])
    def learn_submit():
        """提交造句评判"""
        data = request.get_json()
        word_id = data.get('word_id')
        sentence = data.get('sentence', '').strip()

        word = WordModel.get_by_id(word_id)
        if not word:
            return jsonify({'success': False, 'message': '单词不存在'})

        # 调用 AI 评判
        result = judge_sentence(word['word'], sentence)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']})

        passed = result.get('result') == 'pass'

        # 更新学习状态
        review_result = process_review(word_id, passed)

        response = {
            'success': True,
            'passed': passed,
            'judge': result,
            'review': review_result,
            'word': word,
        }

        return jsonify(response)

    @app.route('/api/learn/submit-translation', methods=['POST'])
    def learn_submit_translation():
        """提交翻译评判（翻译模式专用）"""
        data = request.get_json()
        word_id = data.get('word_id')
        translation = data.get('translation', '').strip()

        word = WordModel.get_by_id(word_id)
        if not word:
            return jsonify({'success': False, 'message': '单词不存在'})

        example = word.get('input_example', '')
        if not example:
            return jsonify({'success': False, 'error': '该单词没有原文例句，无法使用翻译模式'})

        # 调用 AI 翻译评判
        result = judge_translation(word['word'], example, translation)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']})

        passed = result.get('result') == 'pass'

        # 更新学习状态
        review_result = process_review(word_id, passed)

        response = {
            'success': True,
            'passed': passed,
            'judge': result,
            'review': review_result,
            'word': word,
        }

        return jsonify(response)

    @app.route('/api/learn/skip', methods=['POST'])
    def learn_skip():
        """跳过当前单词（标记为已掌握）"""
        data = request.get_json()
        word_id = data.get('word_id')
        result = mark_mastered(word_id)
        return jsonify({'success': True, 'result': result})

    @app.route('/api/learn/dont-know', methods=['POST'])
    def learn_dont_know():
        """不认识当前单词 — 按未通过处理，展示例句"""
        data = request.get_json()
        word_id = data.get('word_id')

        word = WordModel.get_by_id(word_id)
        if not word:
            return jsonify({'success': False, 'message': '单词不存在'})

        # 按"未通过"处理复习（退回 stage 0，重新进入复习队列）
        review_result = process_review(word_id, passed=False)

        # 如果没有例句，用 AI 生成
        need_save = False
        examples = word.get('examples', [])

        if not examples:
            ai_examples = generate_examples(word['word'])
            if ai_examples:
                examples = ai_examples
                need_save = True

        if need_save:
            WordModel.update(word_id, examples=examples)
            word['examples'] = examples

        return jsonify({
            'success': True,
            'review': review_result,
            'word': word,
        })

    @app.route('/api/learn/reset', methods=['POST'])
    def learn_reset():
        """将单词恢复为 new 状态"""
        data = request.get_json()
        word_id = data.get('word_id')
        from services.review_service import reset_word as do_reset
        result = do_reset(word_id)
        return jsonify({'success': True, 'result': result})

    # ========== 导入词本 ==========
    @app.route('/import')
    def import_page():
        """导入页面"""
        wordbooks = WordbookModel.get_all()
        return render_template('import.html', wordbooks=wordbooks)

    @app.route('/import/preview', methods=['POST'])
    def import_preview():
        """导入预览（解析文件或文本，展示待确认结果）"""
        method = request.form.get('method', 'manual')  # 'file' or 'manual'
        wordbook_id = request.form.get('wordbook_id', type=int)
        new_wordbook_name = request.form.get('new_wordbook_name', '').strip()

        # 解析单词列表
        if method == 'file':
            file = request.files.get('file')
            if not file:
                return jsonify({'success': False, 'message': '请上传文件'})
            try:
                content = file.read().decode('utf-8')
            except UnicodeDecodeError:
                content = file.read().decode('gbk', errors='ignore')
            words = parse_txt(content)
        else:
            text = request.form.get('words_text', '').strip()
            if not text:
                return jsonify({'success': False, 'message': '请输入单词'})
            words = parse_manual(text)

        if not words:
            return jsonify({'success': False, 'message': '未识别到有效单词'})

        # 如果选择新词本，先创建
        if wordbook_id == 0 and new_wordbook_name:
            mode = request.form.get('mode', 'writing')
            wordbook_id = WordbookModel.create(new_wordbook_name, mode=mode)

        if not wordbook_id:
            return jsonify({'success': False, 'message': '请选择或创建词本'})

        # 处理导入
        results = process_import(wordbook_id, words)

        return jsonify({
            'success': True,
            'wordbook_id': wordbook_id,
            'total': len(results),
            'results': results,
        })

    @app.route('/import/confirm', methods=['POST'])
    def import_confirm():
        """确认导入"""
        data = request.get_json()
        wordbook_id = data.get('wordbook_id')
        results = data.get('results', [])

        count = confirm_import(wordbook_id, results)
        return jsonify({
            'success': True,
            'message': f'成功导入 {count} 个单词',
            'count': count,
        })

    # ========== 导出词本 ==========
    @app.route('/wordbook/<int:wordbook_id>/export/<fmt>')
    def wordbook_export(wordbook_id, fmt):
        """导出词本（JSON/CSV）"""
        wb = WordbookModel.get_by_id(wordbook_id)
        if not wb:
            return jsonify({'error': '词本不存在'}), 404

        data = WordModel.get_by_wordbook(wordbook_id, per_page=99999)
        words = data['words']

        if fmt == 'json':
            export = {
                'wordbook': wb['name'],
                'exported_at': datetime.now().isoformat(),
                'words': words,
            }
            filename = f"{wb['name']}.json"
            resp = jsonify(export)
            resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return resp

        elif fmt == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['单词', '词性', '音标', '释义', '状态', '例句'])
            for w in words:
                examples = '; '.join(w.get('examples', [])) if isinstance(w.get('examples'), list) else ''
                writer.writerow([w['word'], w['pos'], w['phonetic'], w['definition'],
                               w['status'], examples])
            csv_content = output.getvalue()
            output.close()

            filename = f"{wb['name']}.csv"
            from flask import Response
            resp = Response(csv_content, mimetype='text/csv')
            resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return resp

        return jsonify({'error': '不支持的格式'}), 400

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

        backup = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'wordbooks': wordbooks,
            'words': words,
            'configs': configs,
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
            db.execute('DELETE FROM words')
            db.execute('DELETE FROM wordbooks')
            db.execute('DELETE FROM config')

            # 导入词本
            for wb in data.get('wordbooks', []):
                db.execute('INSERT INTO wordbooks (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)',
                         (wb['id'], wb['name'], wb.get('created_at', datetime.now().isoformat()),
                          wb.get('updated_at', datetime.now().isoformat())))

            # 导入单词
            for w in data.get('words', []):
                db.execute(
                    '''INSERT INTO words (id, wordbook_id, word, pos, phonetic, definition, examples, status,
                       review_stage, correct_count, last_review_date, next_review_date, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (w['id'], w['wordbook_id'], w['word'], w.get('pos', ''), w.get('phonetic', ''),
                     w.get('definition', ''), w.get('examples', '[]'), w.get('status', 'new'),
                     w.get('review_stage', 0), w.get('correct_count', 0),
                     w.get('last_review_date', ''), w.get('next_review_date', ''), w.get('created_at', ''))
                )

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
