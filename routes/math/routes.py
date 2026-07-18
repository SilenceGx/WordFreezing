"""数学模块路由 — 题本/题目/学习/创建向导"""

import json
from datetime import datetime
from flask import render_template, request, jsonify, session

from database.db import get_db, dicts_from_rows
from . import math_bp

# 临时存储追问会话（切换题目时清除）
discuss_sessions = {}
from routes.math.models.problem_book import ProblemBookModel
from routes.math.models.problem import ProblemModel
from routes.math.models.key_node import KeyNodeModel


# ========== 首页 ==========
@math_bp.route('/')
def index():
    """数学首页：题本列表"""
    books = ProblemBookModel.get_all()
    today_count = ProblemBookModel.get_today_review_count()
    stats = ProblemBookModel.get_stats()
    return render_template('math/index.html',
                          books=books,
                          today_count=today_count,
                          stats=stats)


# ========== 创建向导 ==========
@math_bp.route('/create', methods=['GET', 'POST'])
def create():
    """两步创建向导：
    GET  → 渲染创建页面
    POST → 提交完整数据（题目+解答+节点）
    """
    if request.method == 'GET':
        books = ProblemBookModel.get_all()
        return render_template('math/create.html', books=books)

    # POST：接收完整创建数据
    data = request.get_json()
    book_id = data.get('book_id')
    new_book_name = data.get('new_book_name', '').strip()
    problem_text = data.get('problem_text', '').strip()
    solution_text = data.get('solution_text', '').strip()
    nodes = data.get('nodes', [])

    if not problem_text or not solution_text:
        return jsonify({'success': False, 'message': '题目和解答不能为空'})

    # 创建新题本或使用已有
    if not book_id and new_book_name:
        book_id = ProblemBookModel.create(new_book_name)
    elif not book_id:
        return jsonify({'success': False, 'message': '请选择或创建题本'})

    if not nodes or len(nodes) < 1:
        return jsonify({'success': False, 'message': '请至少添加 1 个关键节点'})

    # 创建题目
    problem_id = ProblemModel.create(book_id, problem_text, solution_text)

    # 批量创建节点
    prepared_nodes = []
    for i, n in enumerate(nodes):
        prepared_nodes.append({
            'node_order': i + 1,
            'title': n.get('title', '').strip(),
            'description': n.get('description', '').strip(),
            'formula': n.get('formula', '').strip(),
        })
    KeyNodeModel.batch_create(problem_id, prepared_nodes)

    return jsonify({
        'success': True,
        'message': '创建成功',
        'problem_id': problem_id,
        'book_id': book_id,
    })


# ========== 开始学习 ==========
@math_bp.route('/learn/<int:book_id>')
def learn(book_id):
    """学习页面"""
    bk = ProblemBookModel.get_by_id(book_id)
    if not bk:
        return render_template('error.html', message='题本不存在'), 404
    return render_template('math/learn.html', book=bk)


# ========== 删除题目 ==========
@math_bp.route('/api/problem/<int:problem_id>/delete', methods=['POST'])
def api_delete_problem(problem_id):
    """删除题目"""
    ProblemModel.delete(problem_id)
    return jsonify({'success': True, 'message': '已删除'})


# ========== 创建题本 ==========
@math_bp.route('/api/books/create', methods=['POST'])
def api_create_book():
    """创建题本"""
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': '请输入题本名称'})
    book_id = ProblemBookModel.create(name)
    return jsonify({'success': True, 'message': '创建成功', 'id': book_id})


# ========== 统计 ==========
@math_bp.route('/stats')
def stats():
    """统计页面"""
    books = ProblemBookModel.get_all()
    global_stats = ProblemBookModel.get_stats()
    today_count = ProblemBookModel.get_today_review_count()
    return render_template('math/stats.html',
                          books=books,
                          global_stats=global_stats,
                          today_count=today_count)


# ========== 题本详情 ==========
@math_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    """题本详情：题目列表"""
    bk = ProblemBookModel.get_by_id(book_id)
    if not bk:
        return render_template('error.html', message='题本不存在'), 404

    page = request.args.get('page', 1, type=int)
    data = ProblemModel.get_by_book(book_id, page=page)
    return render_template('math/book.html', book=bk, data=data)


# ========== 学习 API ==========
@math_bp.route('/api/next/<int:book_id>')
def api_next_problem(book_id):
    """获取下一道题（先复习到期的，再学新题）"""
    bk = ProblemBookModel.get_by_id(book_id)
    if not bk:
        return jsonify({'error': '题本不存在'}), 404

    # 1. 先查出含有到期节点的题目
    due_problems = ProblemModel.get_due_review_problems(book_id, limit=1)
    if due_problems:
        p = due_problems[0]
        problem = ProblemModel.get_by_id(p['id'])
        # 只返回到期的节点
        due_nodes = ProblemModel.get_due_nodes_for_problem(p['id'])
        # 如果到期节点为空（所有都 mastered），跳到下一题
        if not due_nodes:
            return api_next_problem(book_id)
        return jsonify({
            'problem': problem,
            'mode': 'review',
            'nodes': due_nodes,
        })

    # 2. 再出新题
    new_problems = ProblemModel.get_new_problems(book_id, limit=1)
    if new_problems:
        p = new_problems[0]
        problem = ProblemModel.get_by_id(p['id'])
        all_nodes = ProblemModel.get_all_nodes_for_problem(p['id'])
        return jsonify({
            'problem': problem,
            'mode': 'new',
            'nodes': all_nodes,
        })

    # 3. 全部完成
    return jsonify({
        'done': True,
        'message': '🎉 所有题目已掌握！',
    })


@math_bp.route('/api/judge', methods=['POST'])
def api_judge():
    """提交完整解答 → AI 逐节点评判"""
    data = request.get_json()
    problem_id = data.get('problem_id')
    user_answer = data.get('user_answer', '').strip()

    if not problem_id or not user_answer:
        return jsonify({'success': False, 'message': '参数不完整'})

    problem = ProblemModel.get_by_id(problem_id)
    if not problem:
        return jsonify({'success': False, 'message': '题目不存在'})

    nodes = problem.get('nodes', [])
    if not nodes:
        return jsonify({'success': False, 'message': '该题目没有关键节点'})

    # 调用 AI 评判
    from services.ai_service import call_ai, extract_json

    node_list_text = '\n'.join(
        f'{n["id"]}. [{n["title"]}] {n["description"]}'
        + (f' 关键公式: {n["formula"]}' if n.get('formula') else '')
        for n in nodes
    )

    system_prompt = f"""你是一位数学导师。以下是题目及其预设的关键节点。

## 题目
{problem['problem_text']}

## 关键节点（共 {len(nodes)} 个）
{node_list_text}

## 用户提交的完整解答
{user_answer}

---
请逐条判断用户是否**踩中**了每个关键节点。

"踩中"意味着用户的解答中正确体现了该节点的核心思路或步骤。
注意：用户可能用了不同的解法，只要该节点对应的关键思路/公式在解答中被正确使用就视为踩中。

返回 JSON:
{{
  "node_results": [
    {{
      "node_id": 1,
      "hit": true,
      "feedback": "简短评价（true则肯定，false则说明遗漏了什么）"
    }}
  ],
  "overall": "整体评价，1-2句话"
}}
"""

    result = call_ai(
        messages=[{'role': 'user', 'content': '请对照关键节点评判用户的解答。'}],
        system_prompt=system_prompt,
        temperature=0.3,
        max_tokens=2000,
    )

    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']})

    parsed = extract_json(result['content'])
    if not parsed or 'node_results' not in parsed:
        return jsonify({'success': False, 'error': 'AI 响应解析失败'})

    # 将 AI 返回的 node_id 映射回实际节点的信息
    node_map = {n['id']: n for n in nodes}
    for nr in parsed['node_results']:
        node_info = node_map.get(nr['node_id'])
        if node_info:
            nr['title'] = node_info['title']
            nr['description'] = node_info['description']
            nr['formula'] = node_info.get('formula', '')

    # 处理复习结果
    review_results = []
    for nr in parsed['node_results']:
        rr = KeyNodeModel.process_review(nr['node_id'], nr['hit'])
        review_results.append({**nr, 'review': rr})

    return jsonify({
        'success': True,
        'node_results': review_results,
        'overall': parsed.get('overall', ''),
    })


# ========== 追问讨论 ==========
discuss_sessions = {}  # key: problem_id, value: [messages]


@math_bp.route('/api/discuss', methods=['POST'])
def api_discuss():
    """追问讨论（多轮对话）"""
    data = request.get_json()
    problem_id = data.get('problem_id')
    user_message = data.get('message', '').strip()

    if not problem_id or not user_message:
        return jsonify({'success': False, 'message': '参数不完整'})

    problem = ProblemModel.get_by_id(problem_id)
    if not problem:
        return jsonify({'success': False, 'message': '题目不存在'})

    nodes = problem.get('nodes', [])

    # 提取 or 初始化会话
    if problem_id not in discuss_sessions:
        node_list_text = '\n'.join(
            f'- {n["title"]}: {n["description"]}' +
            (f' (公式: {n["formula"]})' if n.get('formula') else '')
            for n in nodes
        )
        discuss_sessions[problem_id] = [
            {
                'role': 'system',
                'content': f"""你是数学导师。以下题目和关键节点是你和用户讨论的背景。

## 题目
{problem['problem_text']}

## 关键节点
{node_list_text}

---
用户刚才做了这道题，现在有一些追问。请以导师身份耐心解答：
- 解释思路时逐层深入
- 可以用 LaTeX 公式（$$...$$）辅助说明
- 鼓励思考，但不直接越俎代庖
- 如果问题跑偏，温和引导回本题"""
            }
        ]

    discuss_sessions[problem_id].append({'role': 'user', 'content': user_message})

    from services.ai_service import call_ai
    result = call_ai(
        messages=discuss_sessions[problem_id][1:],  # 不含 system
        system_prompt=discuss_sessions[problem_id][0]['content'],
        temperature=0.5,
        max_tokens=2000,
    )

    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']})

    reply = result['content']
    discuss_sessions[problem_id].append({'role': 'assistant', 'content': reply})

    return jsonify({'success': True, 'reply': reply})


@math_bp.route('/api/discuss/clear', methods=['POST'])
def api_discuss_clear():
    """清除追问会话（切换题目时调用）"""
    data = request.get_json()
    problem_id = data.get('problem_id')
    if problem_id in discuss_sessions:
        del discuss_sessions[problem_id]
    return jsonify({'success': True})
