"""导入处理服务

支持两种导入方式：
1. TXT 文件导入（每行一个单词）
2. 手动输入（逐词输入）

处理流程：
1. 提取单词列表
2. 查询本地词典 ECDICT/StarDict（如果存在）
3. 未命中词汇批量 AI 补全
4. 返回结果供用户确认
"""

import os
import json
from models.word import WordModel

# 词典路径检测（支持 ecdict.db 或 stardict.db）
DICT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'dictionary')
DICT_PATH_CANDIDATES = [
    os.path.join(DICT_DIR, 'ecdict.db'),
    os.path.join(DICT_DIR, 'stardict.db'),
    os.path.join(DICT_DIR, 'dictionary.db'),
]

# 自动检测存在的词典文件
DICT_PATH = None
DICT_TABLE = None
for _p in DICT_PATH_CANDIDATES:
    if os.path.exists(_p):
        DICT_PATH = _p
        break

if DICT_PATH:
    # 检测表名
    import sqlite3 as _sqlite3
    try:
        _conn = _sqlite3.connect(DICT_PATH)
        _tables = _conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        _conn.close()
        for _t in _tables:
            _tn = _t[0].lower()
            if _tn in ('ecdict', 'stardict', 'dict'):
                DICT_TABLE = _t[0]
                break
        if DICT_TABLE is None:
            DICT_TABLE = _tables[0][0] if _tables else None
    except Exception:
        DICT_TABLE = 'ecdict'


ECDICT_POS_MAP = {
    'n': 'n.', 'v': 'v.', 'vi': 'vi.', 'vt': 'vt.', 'a': 'adj.',
    'ad': 'adv.', 'art': 'art.', 'aux': 'aux.', 'c': 'conj.',
    'conj': 'conj.', 'det': 'det.', 'i': 'vi.', 'interj': 'interj.',
    'num': 'num.', 'p': 'prep.', 'prep': 'prep.', 'pron': 'pron.',
    'r': 'vt.', 'pl': 'pl.',
}


def _clean_pos(raw_pos):
    """清洗 ECDICT pos 格式为可读词性

    输入: 'n:4/v:96' 或 'n:100' 或 ''
    输出: 'v.' 或 'n.' 或 ''
    """
    if not raw_pos or not raw_pos.strip():
        return ''
    # 解析 "n:4/v:96" → 取比例最高的词性
    parts = raw_pos.split('/')
    best_tag = None
    best_pct = -1
    for part in parts:
        if ':' in part:
            tag, pct_str = part.split(':', 1)
            try:
                pct = int(pct_str)
            except ValueError:
                pct = 0
            if pct > best_pct:
                best_pct = pct
                best_tag = tag.strip()
        else:
            tag = part.strip()
            if tag and best_tag is None:
                best_tag = tag
    if best_tag:
        cleaned = ECDICT_POS_MAP.get(best_tag.lower())
        if cleaned:
            return cleaned
        # 未知标签，加'.'后缀
        tag = best_tag.strip().lower()
        return tag if tag.endswith('.') else tag + '.'
    return ''


def _lookup_dict(word):
    """在本地词典中查询单词（有则返回词性/音标/释义，无则返回 None）

    返回格式：{word, pos, phonetic, definition}
    definition 优先取中文翻译(translation)，无则用英文释义(definition)
    """
    if not DICT_PATH or not DICT_TABLE:
        return None

    import sqlite3
    try:
        db = sqlite3.connect(DICT_PATH)
        db.row_factory = sqlite3.Row
        # 探测有哪些列
        col_info = db.execute(f'PRAGMA table_info({DICT_TABLE})').fetchall()
        cols = [c['name'] for c in col_info]

        if 'translation' in cols:
            # ECDICT/StarDict 格式：有 translation 列（中文释义）
            row = db.execute(
                f'SELECT word, pos, phonetic, translation, definition FROM {DICT_TABLE} WHERE word = ?',
                (word.lower(),)
            ).fetchone()
            db.close()
            if row:
                return {
                    'word': row['word'],
                    'pos': _clean_pos(row['pos']),
                    'phonetic': row['phonetic'] or '',
                    'definition': row['translation'] or row['definition'] or word,
                }
        else:
            # 通用格式
            select_cols = [c for c in ('word', 'pos', 'phonetic', 'definition', 'translation')
                          if c in cols]
            row = db.execute(
                f'SELECT {",".join(select_cols)} FROM {DICT_TABLE} WHERE word = ?',
                (word.lower(),)
            ).fetchone()
            db.close()
            if row:
                result = dict(row)
                # 中文翻译优先
                if 'translation' in result and result['translation']:
                    result['definition'] = result['translation']
                result['pos'] = _clean_pos(result.get('pos', ''))
                result.setdefault('phonetic', '')
                result.setdefault('definition', word)
                return result
        db.close()
        return None
    except Exception as e:
        print(f'[词典查询失败] {word}: {e}')
        return None


def parse_txt(content):
    """解析 TXT 文件内容，返回单词列表（去重、保留字母）"""
    words = []
    for line in content.splitlines():
        line = line.strip()
        if line and line.isascii() and line.replace('-', '').isalpha():
            words.append(line.lower())
    # 去重但保持顺序
    seen = set()
    unique = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def parse_manual(text):
    """解析手动输入的文本，返回单词列表"""
    # 支持逗号、空格、换行分隔
    import re
    words = re.split(r'[,，\s\n\r]+', text.strip())
    words = [w.strip().lower() for w in words if w.strip().isascii() and w.strip().replace('-', '').isalpha()]
    seen = set()
    unique = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def process_import(wordbook_id, words):
    """处理导入的单词列表

    Args:
        wordbook_id: 词本 ID
        words: list of str，单词列表

    Returns:
        dict: {imported_count, failed_count, details: [...]}
    """
    from services.ai_service import batch_complete

    # 1. 拆分已命中词典和未命中词汇
    lookup_results = {}  # word -> {pos, phonetic, definition}
    missing_words = []   # 未命中词典的单词列表
    dict_available = DICT_PATH is not None

    for w in words:
        entry = _lookup_dict(w)
        if entry:
            lookup_results[w] = {
                'pos': entry.get('pos', ''),
                'phonetic': entry.get('phonetic', ''),
                'definition': entry.get('definition', ''),
            }
        else:
            missing_words.append(w)

    # 2. 未命中的调用 AI 补全
    ai_results = {}
    if missing_words:
        try:
            completions = batch_complete(missing_words)
            for item in completions:
                if isinstance(item, dict) and 'word' in item and 'error' not in item:
                    ai_results[item['word']] = item
        except Exception:
            pass

        # 即使 AI 失败也为缺失词提供占位
        for w in missing_words:
            if w not in ai_results:
                ai_results[w] = {
                    'pos': '',
                    'phonetic': '',
                    'definition': w,
                    'examples': [],
                }

    # 3. 组装结果
    results = []
    for w in words:
        if w in lookup_results:
            info = lookup_results[w]
        elif w in ai_results:
            info = ai_results[w]
        else:
            info = {'pos': '', 'phonetic': '', 'definition': w, 'examples': []}

        results.append({
            'word': w,
            'pos': info.get('pos', ''),
            'phonetic': info.get('phonetic', ''),
            'definition': info.get('definition', ''),
            'examples': info.get('examples', []),
            'source': 'dictionary' if w in lookup_results else 'ai',
        })

    return results


def confirm_import(wordbook_id, results):
    """确认导入，批量写入数据库

    Args:
        wordbook_id: 词本 ID
        results: process_import 返回的结果列表

    Returns:
        int: 成功导入数量
    """
    words_data = []
    for r in results:
        words_data.append({
            'wordbook_id': wordbook_id,
            'word': r['word'],
            'pos': r.get('pos', ''),
            'phonetic': r.get('phonetic', ''),
            'definition': r.get('definition', ''),
            'examples': r.get('examples', []),
        })

    if words_data:
        WordModel.batch_create(words_data)

    return len(words_data)
