"""导入处理服务

支持两种导入方式：
1. TXT 文件导入（每行一个单词，支持 单词|例句 格式）
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
    """解析 TXT 文件内容，返回单词列表（去重、保留字母）

    支持两种格式：
    - 纯单词行：succumb
    - 单词+例句：succumb|He finally succumbed to the temptation.

    Returns:
        list of dict: [{'word': 'succumb', 'input_example': 'He finally...'}, ...]
    """
    items = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # 检测 word|example 格式
        if '|' in line:
            parts = line.split('|', 1)
            word = parts[0].strip().lower()
            example = parts[1].strip()
            if word and word.isascii() and word.replace('-', '').isalpha():
                items.append({'word': word, 'input_example': example})
        else:
            if line.isascii() and line.replace('-', '').isalpha():
                items.append({'word': line.lower(), 'input_example': ''})
    # 去重但保持顺序（同单词保留第一个例句）
    seen = set()
    unique = []
    for item in items:
        if item['word'] not in seen:
            seen.add(item['word'])
            unique.append(item)
    return unique


def parse_manual(text):
    """解析手动输入的文本，返回单词列表

    支持两种格式（按换行分隔，一行一个单词或单词|例句）：
    - 纯单词：succumb
    - 单词+例句：succumb|He finally succumbed to the temptation.

    纯单词也支持逗号分隔：succumb, feasible, albeit
    （注意：例句中有逗号时请用换行分隔，避免误拆）

    Returns:
        list of dict: [{'word': 'succumb', 'input_example': 'He finally...'}, ...]
    """
    import re
    seen = set()
    unique = []

    # 先按换行拆分，每行独立处理
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if '|' in line:
            # 带例句格式：单词|例句（整行就是一个单词+例句，不再按逗号拆分）
            parts = line.split('|', 1)
            word = parts[0].strip().lower()
            example = parts[1].strip()
            if word and word.isascii() and word.replace('-', '').isalpha() and word not in seen:
                seen.add(word)
                unique.append({'word': word, 'input_example': example})
        else:
            # 纯单词行，按逗号拆分（兼容逗号分隔多个单词）
            tokens = re.split(r'[,，\s\n\r]+', line)
            for w in tokens:
                word = w.strip().lower()
                if word and word.isascii() and word.replace('-', '').isalpha() and word not in seen:
                    seen.add(word)
                    unique.append({'word': word, 'input_example': ''})
    return unique


def process_import(wordbook_id, word_items):
    """处理导入的单词列表

    Args:
        wordbook_id: 词本 ID
        word_items: list of dict，每个包含 'word' 和可选的 'input_example'
                    例如 [{'word': 'succumb', 'input_example': 'He finally...'}, ...]

    Returns:
        list of dict: 每个包含 word/pos/phonetic/definition/examples/input_example/source
    """
    from services.ai_service import batch_complete

    # 提取纯单词列表
    words = [item['word'] for item in word_items]

    # 1. 拆分已命中词典和未命中词汇
    lookup_results = {}  # word -> {pos, phonetic, definition}
    missing_words = []   # 未命中词典的单词列表

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
    for item in word_items:
        w = item['word']
        input_example = item.get('input_example', '')

        if w in lookup_results:
            info = lookup_results[w]
            source = 'dictionary'
        elif w in ai_results:
            info = ai_results[w]
            source = 'ai'
        else:
            info = {'pos': '', 'phonetic': '', 'definition': w, 'examples': []}
            source = 'ai'

        results.append({
            'word': w,
            'pos': info.get('pos', ''),
            'phonetic': info.get('phonetic', ''),
            'definition': info.get('definition', ''),
            'examples': info.get('examples', []),
            'input_example': input_example,
            'source': source,
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
            'input_example': r.get('input_example', ''),
        })

    if words_data:
        WordModel.batch_create(words_data)

    return len(words_data)
