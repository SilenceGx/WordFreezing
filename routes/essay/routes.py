"""作文模块路由 — 作文本/作文/阅读"""

from flask import render_template, request, jsonify, redirect, url_for

from . import essay_bp
from routes.essay.models.essay_book import EssayBookModel
from routes.essay.models.essay import EssayModel


# ========== 作文本详情 ==========
@essay_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    """作文本详情：作文列表"""
    bk = EssayBookModel.get_by_id(book_id)
    if not bk:
        return render_template('error.html', message='作文本不存在'), 404

    essays = EssayModel.get_by_book(book_id)
    return render_template('essay/book.html',
                          book=bk,
                          essays=essays)


# ========== 新建作文 ==========
@essay_bp.route('/create/<int:book_id>', methods=['GET'])
def create_page(book_id):
    """新建作文页面"""
    bk = EssayBookModel.get_by_id(book_id)
    if not bk:
        return render_template('error.html', message='作文本不存在'), 404
    return render_template('essay/create.html', book=bk)


@essay_bp.route('/api/essays/create', methods=['POST'])
def api_create_essay():
    """创建作文 API"""
    data = request.get_json()
    book_id = data.get('book_id')
    title = data.get('title', '').strip()
    author = data.get('author', '').strip()
    content = data.get('content', '').strip()
    summary = data.get('summary', '').strip()

    if not book_id:
        return jsonify({'success': False, 'message': '参数不完整'})
    if not title:
        return jsonify({'success': False, 'message': '请输入作文标题'})
    if not content:
        return jsonify({'success': False, 'message': '请输入作文内容'})

    essay_id = EssayModel.create(book_id, title, content, author, summary)
    return jsonify({
        'success': True,
        'message': '作文已创建',
        'essay_id': essay_id,
        'book_id': book_id,
    })


# ========== 阅读 ==========
@essay_bp.route('/read/<int:essay_id>')
def read(essay_id):
    """阅读作文"""
    essay = EssayModel.get_by_id(essay_id)
    if not essay:
        return render_template('error.html', message='作文不存在'), 404
    return render_template('essay/read.html', essay=essay)


# ========== 编辑 ==========
@essay_bp.route('/edit/<int:essay_id>', methods=['GET'])
def edit_page(essay_id):
    """编辑作文页面"""
    essay = EssayModel.get_by_id(essay_id)
    if not essay:
        return render_template('error.html', message='作文不存在'), 404
    return render_template('essay/create.html', essay=essay, book=essay)


@essay_bp.route('/api/essays/update', methods=['POST'])
def api_update_essay():
    """更新作文 API"""
    data = request.get_json()
    essay_id = data.get('essay_id')
    title = data.get('title', '').strip()
    author = data.get('author', '').strip()
    content = data.get('content', '').strip()
    summary = data.get('summary', '').strip()

    if not essay_id:
        return jsonify({'success': False, 'message': '参数不完整'})
    if not title:
        return jsonify({'success': False, 'message': '请输入作文标题'})
    if not content:
        return jsonify({'success': False, 'message': '请输入作文内容'})

    EssayModel.update(essay_id, title, author, content, summary)
    return jsonify({'success': True, 'message': '作文已更新'})


# ========== 创建/编辑作文本 ==========
@essay_bp.route('/api/books/create', methods=['POST'])
def api_create_book():
    """创建作文本"""
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': '请输入作文本名称'})
    book_id = EssayBookModel.create(name)
    return jsonify({'success': True, 'message': '创建成功', 'id': book_id})


@essay_bp.route('/api/books/update', methods=['POST'])
def api_update_book():
    """更新作文本名称"""
    data = request.get_json()
    book_id = data.get('book_id')
    name = data.get('name', '').strip()
    if not book_id or not name:
        return jsonify({'success': False, 'message': '参数不完整'})
    EssayBookModel.update_name(book_id, name)
    return jsonify({'success': True, 'message': '已更新'})


@essay_bp.route('/api/books/<int:book_id>/delete', methods=['POST'])
def api_delete_book(book_id):
    """删除作文本"""
    EssayBookModel.delete(book_id)
    return jsonify({'success': True, 'message': '已删除'})


# ========== 删除作文 ==========
@essay_bp.route('/api/essays/<int:essay_id>/delete', methods=['POST'])
def api_delete_essay(essay_id):
    """删除作文"""
    EssayModel.delete(essay_id)
    return jsonify({'success': True, 'message': '已删除'})
