"""间隔重复算法服务

状态变迁：
  new ──── 首次造句通过 ────→ mastered（直接斩）
    │
    └── 首次造句不通过 ──→ learning (review_stage=0, 1天后复习)

  learning (stage 0) ── 1天后造句通过 ──→ learning (stage 1)
  learning (stage 1) ── 3天后造句通过 ──→ learning (stage 2)
  learning (stage 2) ── 7天后造句通过 ──→ mastered

  任何 stage 失败 ──→ 退回 learning (stage 0)
  同一天重复通过只计一次有效
"""

from datetime import datetime, timedelta
from models.word import WordModel


def _today_str():
    return datetime.now().strftime('%Y-%m-%d')


def _calc_next_review(stage):
    """根据复习阶段计算下次复习日期"""
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


def process_review(word_id, passed):
    """处理一个单词的复习结果

    Args:
        word_id: 单词 ID
        passed: 是否通过评判

    Returns:
        dict: 包含状态变更信息
    """
    word = WordModel.get_by_id(word_id)
    if not word:
        return {'error': '单词不存在'}

    today = _today_str()
    status = word['status']
    stage = word['review_stage']

    if status == 'new':
        if passed:
            # new → mastered（直接斩）
            WordModel.update(word_id,
                           status='mastered',
                           review_stage=0,
                           correct_count=1,
                           last_review_date=today,
                           next_review_date='')
            return {'status': 'mastered', 'action': '斩！首战告捷 🎉', 'stage': 0}
        else:
            # new → learning (stage 0)
            next_date = _calc_next_review(0)
            WordModel.update(word_id,
                           status='learning',
                           review_stage=0,
                           correct_count=0,
                           last_review_date=today,
                           next_review_date=next_date)
            return {'status': 'learning', 'action': '进入复习队列', 'stage': 0, 'next_review': next_date}

    elif status == 'learning':
        if not passed:
            # 失败 → 退回 stage 0
            next_date = _calc_next_review(0)
            WordModel.update(word_id,
                           review_stage=0,
                           correct_count=0,
                           last_review_date=today,
                           next_review_date=next_date)
            return {'status': 'learning', 'action': '退回起点，继续复习', 'stage': 0, 'next_review': next_date}

        # 通过
        # 检查同一天是否已经通过（防重复）
        if word['last_review_date'] == today and word['correct_count'] > 0:
            return {'status': 'learning', 'action': '今日已通过，明天继续', 'stage': stage,
                    'next_review': word['next_review_date'], 'skipped': True}

        if stage == 0:
            next_date = _calc_next_review(1)
            WordModel.update(word_id,
                           review_stage=1,
                           correct_count=word['correct_count'] + 1,
                           last_review_date=today,
                           next_review_date=next_date)
            return {'status': 'learning', 'action': '通过还需巩固 💪', 'stage': 1, 'next_review': next_date}

        elif stage == 1:
            next_date = _calc_next_review(2)
            WordModel.update(word_id,
                           review_stage=2,
                           correct_count=word['correct_count'] + 1,
                           last_review_date=today,
                           next_review_date=next_date)
            return {'status': 'learning', 'action': '通过还需巩固 💪', 'stage': 2, 'next_review': next_date}

        elif stage == 2:
            # stage 2 通过 → mastered
            WordModel.update(word_id,
                           status='mastered',
                           review_stage=3,
                           correct_count=word['correct_count'] + 1,
                           last_review_date=today,
                           next_review_date='')
            return {'status': 'mastered', 'action': '斩！彻底掌握 🎉', 'stage': 3}

    elif status == 'mastered':
        return {'status': 'mastered', 'action': '已掌握', 'stage': 3}

    return {'status': status, 'action': '未知状态', 'stage': stage}


def mark_mastered(word_id):
    """手动标记为已掌握（跳过造句流程）"""
    today = _today_str()
    WordModel.update(word_id,
                   status='mastered',
                   review_stage=3,
                   correct_count=1,
                   last_review_date=today,
                   next_review_date='')
    return {'status': 'mastered', 'action': '已标记为掌握 ✅'}


def reset_word(word_id):
    """将单词恢复为 new 状态"""
    WordModel.update(word_id,
                   status='new',
                   review_stage=0,
                   correct_count=0,
                   last_review_date='',
                   next_review_date='')
    return {'status': 'new', 'action': '已恢复为新词'}
