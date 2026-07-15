"""AI 服务 - 句子评判 + 翻译评判 + 批量补全（抽象 DeepSeek/Ollama）

提供三个核心功能：
1. judge_sentence(word, sentence) — 评判用户造句是否地道
2. judge_translation(word, example_sentence, user_translation) — 评判中文翻译是否准确
3. batch_complete(words) — 批量补全单词信息（词性、音标、释义、例句）
"""

import requests
import json
import re
from models.config import ConfigModel

# 判断提示词模板
JUDGE_SYSTEM_PROMPT = """你是一位专业的英语老师。你会收到一个"单词"和用户用这个词造的"句子"。

请评判这个句子是否：
1. 语法正确 ✅
2. 用词地道自然（符合 native speaker 习惯）✅
3. 句子完整，意思清晰 ✅

如果完全正确且地道 → 返回 {"result": "pass", "message": "很好！句子自然地道。"}
如果有问题 → 返回 {"result": "fail", "message": "具体问题描述（指出哪里不对，但不需给出改正例句）"}

注意：
- "recommend sb to do" 是中式英语，应判 fail
- 过于简单（如 "It is a book"）如果正确也可通过，但提示可写更丰富
- 只要句子在语法和用词上正确且不chinglish，就判 pass
- message 只需描述问题，**不要给出改正后的例句**（系统会另外展示地道例句供学习）
- 返回格式必须是严格的 JSON，不要有多余内容
"""

BATCH_COMPLETE_SYSTEM_PROMPT = """你是一位英语词典编纂专家。请为以下英文单词补充词性、音标、中文释义和地道例句。

返回严格的 JSON 数组格式，每个元素包含：
{
  "word": "原词",
  "pos": "词性（如 v./n./adj./adv./prep./pron./conj. 等）",
  "phonetic": "音标（用英式 IPA，如 /ˈeksəmpəl/）",
  "definition": "中文释义（简洁准确）",
  "examples": ["例句1", "例句2"]
}

要求：
- 每个单词至少 2 个例句
- 例句要地道、实用，符合现代英语用法
- 返回格式必须是严格 JSON 数组，不要有多余文字
"""

EXAMPLE_GENERATE_PROMPT = """你是一位英语老师。请为以下单词生成 2 个简单、地道、实用的例句。

返回严格的 JSON 格式：
{
  "examples": ["例句1", "例句2"]
}

要求：
- 例句要简单自然，使用日常生活中的常见表达，控制在 8-15 个单词
- 句子结构不要太复杂，易于理解和模仿
- 要体现该单词最典型、最地道的用法
- 返回格式必须是严格 JSON，不要有多余文字
"""


def _get_ai_config():
    """获取 AI 配置"""
    provider = ConfigModel.get('ai_provider', 'deepseek')

    if provider == 'deepseek':
        return {
            'provider': 'deepseek',
            'api_key': ConfigModel.get('deepseek_api_key', ''),
            'base_url': ConfigModel.get('deepseek_base_url', 'https://api.deepseek.com'),
            'model': ConfigModel.get('deepseek_model', 'deepseek-chat'),
        }
    else:  # ollama
        return {
            'provider': 'ollama',
            'base_url': ConfigModel.get('ollama_base_url', 'http://localhost:11434'),
            'model': ConfigModel.get('ollama_model', 'llama3'),
        }


def _call_ai(messages, system_prompt, temperature=0.3, max_tokens=2000):
    """调用 AI 接口（支持 DeepSeek 和 Ollama）"""
    config = _get_ai_config()

    if config['provider'] == 'deepseek':
        api_key = config['api_key']
        if not api_key:
            return {'error': '请先在设置中配置 DeepSeek API Key'}
        try:
            resp = requests.post(
                f"{config['base_url'].rstrip('/')}/v1/chat/completions",
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': config['model'],
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        *messages,
                    ],
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            return {'content': content}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            # 400 错误通常是模型名不合法
            if '400' in error_msg:
                return {'error': f'API 请求失败 (400): 模型名 "{config.get("model", "")}" 可能无效，请检查设置中的模型名称'}
            return {'error': f'API 请求失败: {error_msg}'}
        except (KeyError, json.JSONDecodeError) as e:
            return {'error': f'API 响应解析失败: {str(e)}'}

    else:  # Ollama
        try:
            resp = requests.post(
                f"{config['base_url'].rstrip('/')}/v1/chat/completions",
                json={
                    'model': config['model'],
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        *messages,
                    ],
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'stream': False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            return {'content': content}
        except requests.exceptions.RequestException as e:
            return {'error': f'Ollama 请求失败: {str(e)}'}
        except (KeyError, json.JSONDecodeError) as e:
            return {'error': f'Ollama 响应解析失败: {str(e)}'}


def _extract_json(text):
    """从 AI 回复中提取 JSON"""
    # 尝试直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从 ```json ... ``` 块中提取
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    return None


def judge_sentence(word, sentence):
    """评判用户造句

    返回:
        {"result": "pass", "message": "..."}
    或
        {"result": "fail", "message": "...", "suggestion": "..."}
    或
        {"error": "..."}
    """
    if not sentence or not sentence.strip():
        return {'result': 'fail', 'message': '请输入句子'}

    result = _call_ai(
        messages=[{'role': 'user', 'content': f'单词: {word}\n用户句子: {sentence}'}],
        system_prompt=JUDGE_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=500,
    )

    if 'error' in result:
        return result

    parsed = _extract_json(result['content'])
    if parsed and 'result' in parsed:
        return parsed

    # 解析失败，返回默认通过（容错）
    return {'result': 'pass', 'message': '句子已提交'}


# 翻译评判提示词
TRANSLATION_JUDGE_PROMPT = """你是一位双语老师。你会收到一个"英文单词"、一个包含该词的"英文原句"以及用户对该句的"中文翻译"。

请评判中文翻译是否准确传达了原句的核心意思，**并始终给出一个准确、自然的标准翻译**。

评分标准：
1. ✅ 核心意思正确 — 语义方向正确，没有关键信息遗漏或反转
2. ✅ 意译可接受 — 不需要字字对应，调整语序、用同义词都可以
3. ❌ 中英混杂 — 不要出现 "他 succumbed 了" 这种混合表达
4. ❌ 意思完全相反 — "他抵抗住了诱惑" vs "他屈服于诱惑"

返回严格的 JSON 格式，始终包含 correct_translation 字段：
{
  "result": "pass" 或 "fail",
  "message": "对用户翻译的简短评价（指出问题或肯定）",
  "correct_translation": "一个准确、自然的标准中文翻译"
}

注意：
- message 需说明问题所在以及正确的理解方向（通过时也给出简短肯定）
- correct_translation 无论通过与否都要提供，作为学习参考
- 返回格式必须是严格的 JSON，不要有多余内容
"""


def judge_translation(word, example_sentence, user_translation):
    """评判用户的中文翻译是否准确

    Args:
        word: str，目标单词
        example_sentence: str，包含该词的英文原句
        user_translation: str，用户写的中文翻译

    Returns:
        dict: {'result': 'pass'/'fail', 'message': str}
              或 {'error': str}
    """
    prompt = (
        f"单词: {word}\n"
        f"英文原句: {example_sentence}\n"
        f"用户的中文翻译: {user_translation}\n\n"
        f"请判断用户的翻译是否准确传达了原句的核心意思。"
    )

    result = _call_ai(
        messages=[{'role': 'user', 'content': prompt}],
        system_prompt=TRANSLATION_JUDGE_PROMPT,
        temperature=0.3,
        max_tokens=300,
    )

    if 'error' in result:
        return result

    parsed = _extract_json(result['content'])
    if parsed and 'result' in parsed:
        return parsed

    # 解析失败，返回默认通过（容错）
    return {'result': 'pass', 'message': '翻译已提交'}


def generate_examples(word):
    """为单个单词生成例句

    调用 AI 生成 2 个地道例句。

    Args:
        word: str，单词

    Returns:
        list of str，例句列表，失败时返回空列表
    """
    result = _call_ai(
        messages=[{'role': 'user', 'content': f'单词: {word}\n请为这个单词生成 2 个地道例句。'}],
        system_prompt=EXAMPLE_GENERATE_PROMPT,
        temperature=0.5,
        max_tokens=500,
    )

    if 'error' in result:
        return []

    parsed = _extract_json(result['content'])
    if isinstance(parsed, dict) and 'examples' in parsed and isinstance(parsed['examples'], list):
        return parsed['examples']

    return []


def batch_complete(words):
    """批量补全单词信息

    Args:
        words: list of str，单词列表

    Returns:
        list of dict，每个包含 word/pos/phonetic/definition/examples
    """
    if not words:
        return []

    result = _call_ai(
        messages=[{'role': 'user', 'content': f'请补全以下单词的信息：\n' + '\n'.join(f'- {w}' for w in words)}],
        system_prompt=BATCH_COMPLETE_SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=4000,
    )

    if 'error' in result:
        return [{'error': result['error']}]

    parsed = _extract_json(result['content'])
    if isinstance(parsed, list):
        return parsed

    # 解析失败，为每个单词返回基础信息
    return [{'word': w, 'pos': '', 'phonetic': '', 'definition': w, 'examples': []} for w in words]


def test_connection():
    """测试 AI 连接"""
    config = _get_ai_config()

    if config['provider'] == 'deepseek':
        api_key = config.get('api_key', '')
        if not api_key:
            return {'success': False, 'message': 'API Key 未配置'}
        try:
            resp = requests.get(
                f"{config['base_url'].rstrip('/')}/v1/models",
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=30,
            )
            if resp.status_code == 200:
                return {'success': True, 'message': 'DeepSeek 连接成功'}
            else:
                return {'success': False, 'message': f'连接失败 (HTTP {resp.status_code})'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}
    else:
        try:
            resp = requests.get(
                f"{config['base_url'].rstrip('/')}/api/tags",
                timeout=30,
            )
            if resp.status_code == 200:
                return {'success': True, 'message': 'Ollama 连接成功'}
            else:
                return {'success': False, 'message': f'连接失败 (HTTP {resp.status_code})'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}
