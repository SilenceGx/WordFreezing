# WordFreezing — 个人背单词应用

> 通过 AI 评判 + 间隔重复，真正掌握单词的用法。支持造句模式和翻译模式双模式。

## 一、核心理念

区别于传统"看单词→记释义"的背词方式，本应用提供两种学习模式：

- **✍️ 造句模式**：要求用户用目标单词写一个英文句子，AI 评判是否地道
- **🌍 翻译模式**：展示原文例句，用户写中文翻译，AI 评判核心意思是否准确

通过科学的间隔重复机制，确保用户**真正掌握**单词的用法，而非死记硬背释义。

## 二、产品定位

| 维度 | 决策 |
|---|---|
| 目标用户 | 个人使用，项目可分享给他人本地部署 |
| 网络要求 | 纯本地应用，调用 AI API 时需要网络 |
| 平台 | Web 应用 |
| 技术栈 | Python + SQLite 轻后端 (Flask) + Jinja2 模板 + 原生 JS |

## 三、数据模型

### 3.1 词本 (Wordbook)

- 用户创建/导入的词本集合
- 每个词本有：名称、创建时间、**学习模式**（造句/翻译）
- 词本内包含多个单词
- 词本模式决定其内所有单词的学习方式

### 3.2 单词 (Word)

每个单词包含以下字段：

| 字段 | 说明 | 来源 |
|---|---|---|
| word | 英文单词 | 用户提供（TXT 导入或手动输入） |
| pos | 词性 (n./v./adj./adv. 等) | 本地词典查询 / AI 补全 |
| phonetic | 音标 | 本地词典查询 / AI 补全 |
| definition | 释义 | 本地词典查询 / AI 补全 |
| examples | 例句列表（至少 2 条） | AI 预生成（一次性批量），固定不变 |
| input_example | 用户自输原文例句（翻译模式用） | TXT 导入 `单词\|例句` 或预览页手动输入 |
| status | 学习状态：`new` / `learning` / `mastered` | 系统根据学习行为自动更新，支持手动调整 |
| review_stage | 复习阶段：0=首次, 1=1天, 2=3天, 3=7天 | 系统自动跟踪 |
| last_review_date | 上次复习日期 | 系统自动记录 |
| next_review_date | 下次计划复习日期 | 系统自动计算 |
| correct_count | 累计通过次数（连续，失败归零） | 系统自动记录 |

### 3.3 学习状态变迁

状态变迁适用于两种模式（写作模式的"造句通过"对应翻译模式的"翻译通过"）：

```
new ──── 首次通过 ────→ mastered ✅（直接斩）
  │
  ├── 首次不通过 ──→ learning (stage 0) ──→ 立即重试(不看答案)
  │                                              ├─ 通过 → correct_count+1 → stage 1
  │                                              └─ 不通过 → correct_count=0 → 留 stage 0
  │
  └── 不认识 ──→ learning (stage 0) ──→ 先看释义例句 → 立即重试(不看答案)
                                           ├─ 通过 → correct_count+1 → stage 1
                                           └─ 不通过 → correct_count=0 → 留 stage 0

learning (stage 0) ── 1 天后到期 → 通过 ──→ learning (stage 1)
learning (stage 1) ── 3 天后到期 → 通过 ──→ learning (stage 2)
learning (stage 2) ── 7 天后到期 → 通过 ──→ mastered ✅（斩！）

任何 stage 失败 ──→ 退回到 learning (stage 0)
同一天重复通过只计一次有效
```

### 3.4 间隔周期

| 阶段 | 距下次复习 |
|---|---|
| review_stage=0（首次失败） | 1 天 |
| review_stage=1（第二次通过） | 3 天 |
| review_stage=2（第三次通过） | 7 天 → mastered |

## 四、功能需求

### 4.1 首页/仪表盘

- 展示今日待复习单词数量，引导用户**先复习再学新词**
- 词本卡片列表，每个词本显示：
  - 词本名称、总词数、学习模式
  - 进度分布：`new` / `learning` / `mastered` 各数量
- "创建新词本"按钮（可选择造句/翻译模式）
- "导入词本"按钮
- 全局统计概览：总词数、已斩词数

### 4.2 学习流程

#### 造句模式流程

1. **展示单词**：英文、词性、音标（释义和例句隐藏，不给提示）
2. **用户操作**：
   - 在输入框写一个英文句子，点击"提交句子"
   - 或点击"✅ 已掌握"按钮（直接 mastery，跳过造句）
   - 或点击"❌ 不认识"按钮
3. **AI 评判**（提交后）：判断句子是否语法正确、用词地道
4. **评判结果**：
   - **通过** → 斩动画 → 下一个词
   - **不通过** → 展示单词释义 + 评判反馈 + 例句学习 → "✍️ 再试一次"
5. **重试**：回到空白单词展示页（看不到答案），再写句子提交

#### 翻译模式流程

1. **展示单词**：英文、词性、音标、**原文例句**（释义隐藏）
2. **用户操作**：
   - 在输入框写中文翻译，点击"提交翻译"
   - 或点击"✅ 已掌握"（直接 mastery）
   - 或点击"❌ 不认识"
3. **AI 评判**：判断中文翻译是否准确传达原句核心意思，**始终给出参考翻译**
4. **评判结果**：
   - **通过** → 斩动画 → 下一个词
   - **不通过** → 展示单词释义 + 评判反馈 + 参考翻译 + 例句学习 → "✍️ 再试一次"
5. **重试**：回到空白展示页（看不到答案），重新写翻译提交

#### 通用规则

- 先复习今日到期单词，再学新词
- 用户可随时中断，进度自动保存
- 翻译模式单词若无 `input_example`，自动用 AI 生成的首条例句补上
- 两种模式的"斩"动画和状态变迁逻辑完全一致

### 4.3 词本总览

- 表格展示词本中所有单词
- 列：单词、词性、释义、原文例句、状态（new / learning / mastered）
- 支持搜索/过滤单词
- 每行可操作：
  - "斩"按钮（手动标记为 mastered）
  - "恢复"按钮（将 mastered 恢复为 new）
- 批量操作：勾选多个单词，批量标记 mastered 或恢复
- 分页支持（词多时）

### 4.4 词本管理

- 编辑词本名称
- 删除词本（级联删除所有单词）
- 删除单词（从词本中移除）
- 批量删除

### 4.5 导入词本

#### 方式一：TXT 文件导入
- 用户上传 TXT 文件，支持两种格式：
  ```
  # 纯单词
  abandon
  ability

  # 单词|原文例句（翻译模式用）
  succumb|He finally succumbed to the temptation.
  feasible|Is it feasible to finish this by Friday?
  ```

#### 方式二：手动逐词输入
- 在界面上逐个输入单词，支持两种格式：
  ```
  # 纯单词（逗号或换行分隔）
  succumb, feasible, albeit

  # 单词|例句（每行一个，例句中的逗号不会误拆）
  ritual|It has become a grimly reliable annual ritual.
  pensioner|Should a car-driving pensioner have to subsidise...
  ```

#### 处理流程
1. 用户输入词本名称或选择已有词本
2. 提供单词列表（文件或手工输入）
3. 系统处理：
   - 查询**本地词典数据库**（ECDICT 开源词库，MIT 许可）
     - 命中 → 自动提取词性、音标、释义（零 API 成本）
   - 未命中词汇 + 例句生成 → 调用 AI 一次性批量补全
4. 预览页展示处理结果，**"原文例句"列可编辑**
5. 确认后批量入库（含 `input_example` 字段）
6. 自动跳转到词本总览页面

#### 模式说明
- 导入到已有词本 → 使用该词本的模式
- 导入时创建新词本 → 默认造句模式（如需翻译模式，先在首页创建翻译模式词本）

### 4.6 导出词本

- 支持 **JSON 格式** 导出：保留完整单词信息（含 `input_example`）
- 支持 **CSV 格式** 导出：可在 Excel 等工具中查看

### 4.7 统计与进度追踪

- 学习总览统计：
  - 今日学习单词数
  - 累计已斩单词数
  - 累计学习天数
  - 各词本进度分布
- 可选的图表展示

### 4.8 设置

- **AI 引擎配置**：
  - DeepSeek API（默认）：API Key、模型自由输入（支持 deepseek-chat / deepseek-reasoner / deepseek-flash 等）、连接测试
  - 本地 Ollama（可选）：服务地址、模型选择
  - 配置信息存储在 SQLite 配置表中
- **数据管理**：
  - 导出完整数据备份（含 `mode` 和 `input_example`）
  - 导入数据备份

## 五、技术方案

### 5.1 技术栈

| 层级 | 技术 |
|---|---|
| 后端框架 | Flask（Python） |
| 数据库 | SQLite |
| 前端渲染 | Jinja2 模板 |
| 前端交互 | 原生 HTML + CSS + JavaScript |
| AI 接口 | DeepSeek API（OpenAI 兼容格式） |
| 本地 AI 备选 | Ollama API（与 DeepSeek 相同接口规范） |

### 5.2 项目结构

```
WordFreezing/
├── app.py                 # Flask 主入口
├── requirements.txt       # Python 依赖
├── database/
│   ├── schema.sql         # 数据库建表语句
│   └── wordfreezing.db    # SQLite 数据文件（运行时生成）
├── dictionary/
│   └── ecdict.db          # 开源词典数据（可选预置）
├── models/
│   ├── wordbook.py        # 词本数据操作
│   ├── word.py            # 单词数据操作
│   └── config.py          # 配置数据操作
├── services/
│   ├── ai_service.py      # AI 评判 + 补全（造句评判 + 翻译评判）
│   ├── import_service.py  # 导入处理逻辑
│   └── review_service.py  # 间隔重复算法
├── static/
│   ├── css/
│   └── js/
└── templates/
    ├── base.html
    ├── index.html         # 首页
    ├── wordbook.html      # 词本总览
    ├── learn.html         # 学习界面（双模式自适应）
    ├── import.html        # 导入词本
    ├── stats.html         # 统计页面
    └── settings.html      # 设置页面
```

### 5.3 AI 评判

#### 造句评判
- `judge_sentence(word, sentence)` — 判断用户写的英文句子是否语法正确、用词地道
- 返回 `pass` / `fail` + 问题描述

#### 翻译评判
- `judge_translation(word, example_sentence, user_translation)` — 判断中文翻译是否准确传达原句核心意思
- 宽松标准：意译可接受，不需要字字对应
- 严格拒绝：中英混杂、意思完全相反
- 始终返回 `correct_translation` 参考翻译

#### 通用
- JSON 解析失败时容错返回 pass
- 评判提示词避免给出完整例句（集中注意力在学习）
- 例句生成要求简单自然、8-15 词、日常表达

### 5.4 重试机制

- 首次不通过或点"不认识"后，单词立即进入 `learning`（stage 0）
- 前端立即提供一次重试机会：回到空白单词展示页（**看不到释义/例句/反馈**），用户重新作答
- 重试走 `process_review` learning 路径：
  - 通过 → `correct_count +1`，stage 0→1，next_review = 3 天后
  - 不通过 → `correct_count = 0`，留在 stage 0，next_review = 1 天后
- 重试结果展示后用户点击"继续"进入下一个词

### 5.5 间隔重复算法逻辑（伪代码）

```
if word.status == 'new':
    if ai_judge_pass(word):
        word.status = 'mastered'
        word.correct_count = 1
        return '斩！'
    else:
        word.status = 'learning'
        word.review_stage = 0
        word.next_review_date = today + 1 day
        word.correct_count = 0
        return '进入复习队列'

if word.status == 'learning':
    if not ai_judge_pass(word):
        word.review_stage = 0
        word.next_review_date = today + 1 day
        word.correct_count = 0
        return '继续复习'
    else:
        if word.review_stage == 0:
            word.review_stage = 1
            word.next_review_date = today + 3 days
            word.correct_count = 1
            return '通过！还需巩固'
        elif word.review_stage == 1:
            word.review_stage = 2
            word.next_review_date = today + 7 days
            word.correct_count = 2
            return '通过！还需巩固'
        elif word.review_stage == 2:
            word.status = 'mastered'
            word.correct_count = 3
            return '斩！'
```

## 六、用户界面示意

### 首页
```
+----------------------------------------+
|  WordFreezing                          |
|  ------------------------------------- |
|                                        |
|  [今日待复习: 5 个单词]                 |
|  先复习 → 再学新词                      |
|                                        |
|  📖 CET-6 高频词 🌍    142词           |
|      new: 120  learning: 18  ✅: 4     |
|                                        |
|  📖 阅读生词           36词            |
|      new: 20  learning: 10  ✅: 6      |
|                                        |
|  [+ 创建新词本] [📥 导入词本]          |
|                                        |
|  📊 总览: 236 词 | ✅ 已斩 13 词       |
+----------------------------------------+
```

### 造句模式学习
```
+----------------------------------------+
|  ← CET-6高频词   进度 new: 84/120       |
|  ------------------------------------- |
|        +--------------+                |
|        | recommend    |                |
|        | /ˈrekəmend/  |                |
|        | v.           |                |
|        +--------------+                |
|                                        |
|  +----------------------------------+  |
|  | 用 "recommend" 造一个句子...      |  |
|  |                                  |  |
|  +----------------------------------+  |
|                                        |
|       [ 提交句子 ]   [ ✅ 已掌握 ]       |
+----------------------------------------+
```

### 翻译模式学习
```
+----------------------------------------+
|  ← 阅读生词     🌍 翻译模式             |
|  ------------------------------------- |
|        +--------------+                |
|        | succumb      |                |
|        | /səˈkʌm/     |                |
|        | v.           |                |
|        +--------------+                |
|                                        |
|  📖 原文例句                           |
|  "He finally succumbed to the          |
|   temptation and ate the whole cake."  |
|                                        |
|  +----------------------------------+  |
|  | 请输入中文翻译...                  |  |
|  +----------------------------------+  |
|                                        |
|      [ 提交翻译 ]   [ ✅ 已掌握 ]       |
+----------------------------------------+
```

### 评判不通过（翻译模式）
```
+----------------------------------------+
|  ❌ 翻译不够准确                        |
|  ------------------------------------- |
|  ┌─ succumb  /səˈkʌm/  v. ───────────┐ |
|  │  释义: 屈服、屈从                   │ |
|  └────────────────────────────────────┘ |
|                                        |
|  📖 原文例句                           |
|  "He finally succumbed to..."          |
|                                        |
|  你的翻译"他抵抗住了诱惑"意思相反，    |
|  "succumb" 是屈服、让步的意思。        |
|                                        |
|  ✅ 参考翻译:                          |
|  他最终屈服于诱惑，吃掉了整个蛋糕。     |
|                                        |
|  ─────────────────────────────────     |
|         [ ✍️ 再试一次 ]                |
|    (点击后回到空白页再答一次)           |
+----------------------------------------+
```

### 词本总览
```
+----------------------------------------+
|  ← 首页   📖 CET-6 高频词  ✍️ 造句模式 |
|  总计 142 词 | new 120 | lrn 18 | ✅ 4 |
|                                        |
|  [✏️ 编辑] [▶ 开始学习] [📥 导入追加]  |
|                         [🗑️ 删除词本]  |
|  ------------------------------------- |
|  搜索: [________________]              |
|                                        |
|  □ 单词     词性  释义        原文例句   状态  操作 |
|  □ abandon  v.    放弃        -        🆕   [✅斩] |
|  □ succumb  v.    屈服        He fina… 📝   [✅斩] |
|  □ ability  n.    能力        -        ✅   [↩恢复]|
|                                        |
|  已选 2 项   [批量斩] [批量恢复] [批量删除]|
+----------------------------------------+
```

## 七、非功能需求

1. **AI Token 控制**
   - 批量补全时一次性处理，避免逐词调用
   - 通过时不给额外反馈，节约 token
   - 用户可配置 API 模型以控制成本

2. **数据安全**
   - 所有数据存储在本地 SQLite
   - API Key 存储在数据库中，不外泄
   - .gitignore 忽略 .db 文件和 .env

3. **分享友好**
   - 项目结构简洁，依赖清晰
   - 接收方只需 `pip install -r requirements.txt && python app.py`
   - 词本通过 JSON/CSV 导出分享，各自独立学习

4. **性能**
   - 本地词典查询 L0 缓存
   - 学习页面预加载下一个单词
   - 数据库自动迁移兼容旧表结构

---

## 八、MathPin — 数学关键节点学习模块

> 基于同一项目扩展的数学模块。通过 AI 评判 + 间隔重复，针对大学数学题逐个关键节点突破。

### 8.1 核心理念

区别于"看答案觉得自己会了"的传统错题本，MathPin 要求用户**写出完整推导**，AI 对照预设的**关键节点清单**逐条评判踩中与否。每个节点独立的间隔重复，复习时只考薄弱节点。

### 8.2 产品定位

| 维度 | 决策 |
|---|---|
| 目标用户 | 个人（大学数学：高数/线代/概率） |
| 学习流程 | 完整解答 → AI 逐节点评判 → 查看遗漏节点 → 追问讨论 |
| 技术栈 | 与英语模块同栈（Flask + SQLite + Jinja2 + KaTeX） |
| 代码组织 | Flask Blueprint `routes/math/`，前缀 `/math` |

### 8.3 数据模型

#### 题本 (ProblemBook)

- 用户创建的题本集合
- 每个题本有：名称、创建时间
- 题本内包含多个题目

#### 题目 (Problem)

| 字段 | 说明 |
|---|---|
| book_id | 所属题本 |
| problem_text | LaTeX 题目 |
| solution_text | LaTeX 完整解答 |
| status | `new` / `learning` / `mastered` |

#### 关键节点 (KeyNode) — 核心学习单元

| 字段 | 说明 |
|---|---|
| problem_id | 所属题目 |
| node_order | 排序（1-5） |
| title | 标题（如"确定使用分部积分法"） |
| description | 方法描述 |
| formula | 关键公式（LaTeX，可选） |
| status | `new` / `learning` / `mastered` |
| review_stage | 复习阶段 0-2 → mastered |
| correct_count | 累计通过次数 |
| next_review_date | 下次复习日期 |

### 8.4 学习流程

```
题本首页 → 创建向导 → 学习页 → AI评判 → 追问讨论 → 间隔重复
                                      ↓
                                下一题 / 到期复习
```

#### 创建向导（两步）

1. **题目信息**：选择/创建题本，输入 LaTeX 题目和解答，KaTeX 实时预览
2. **标注节点**：在解答上标记 3-5 个关键节点（标题 + 方法描述 + 关键公式）

#### 学习流程

1. **展示题目**（🈚解答 🈚提示，左对齐，Times New Roman 字体）
2. **用户写完整解答**（支持 LaTeX，保留换行）
3. **AI 对照节点清单评判**（逐条返回踩中/遗漏 + 反馈）
4. **展示结果**：踩中 X/Y 个节点，遗漏节点直接展示答案内容
5. **追问讨论**：用户可以自由提问，AI 以导师身份解答
6. **切换题目**：清除追问会话，进入下一题

#### 不会处理

点击「❌ 不会」→ 不调 AI 评判，所有节点直接标记 miss → 展示全部节点内容

### 8.5 间隔重复

与英语模块完全一致的算法：

```
new → 首次踩中 → mastered（直接斩）
new → 首次遗漏 → learning(stage 0, 1天后)

learning(stage 0) → 踩中 → stage 1 (3天后)
learning(stage 1) → 踩中 → stage 2 (7天后)
learning(stage 2) → 踩中 → mastered ✅

任何 stage 遗漏 → 退回 stage 0
```

复习调度：题目到期时只展示**到期的节点**，已掌握的节点不重复出现。

### 8.6 功能清单

| 功能 | 路由 | 说明 |
|------|------|------|
| 数学首页 | `GET /math/` | 题本卡片列表 + 待复习数 |
| 创建题本 | `POST /math/api/books/create` | 弹窗创建 |
| 两步创建向导 | `GET/POST /math/create` | 题目+解答→节点标注 |
| 题本详情 | `GET /math/book/<id>` | 题目列表 |
| 学习页 | `GET /math/learn/<id>` | 学习界面 |
| 下一题 | `GET /math/api/next/<id>` | 先复习到期再出新题 |
| AI 评判 | `POST /math/api/judge` | 提交解答→逐节点评判 |
| 不会 | `POST /math/api/dont-know` | 全部标记 miss |
| 追问讨论 | `POST /math/api/discuss` | 多轮对话 |
| 清除会话 | `POST /math/api/discuss/clear` | 切换题目时调用 |
| 统计 | `GET /math/stats` | 全局统计 + 题本进度 |
| 删除题目 | `POST /math/api/problem/<id>/delete` | |

### 8.7 技术方案

#### AI 评判

使用 `services/ai_service.py` 的 `call_ai()` / `extract_json()` 函数。评判提示词：

- 发送题目 + 序号编号的节点清单 + 用户解答
- AI 返回 `{node_results: [{node_id, hit, feedback}], overall}`
- 后端通过序号位置反查出真实 DB ID，附上节点信息返回前端

#### LaTeX 渲染

- 引入 KaTeX CDN（`katex.min.js` + `katex.min.css`）
- 学习页使用 KaTeX 实时渲染题目和解答
- 创建向导使用 KaTeX 实时预览
- 追问讨论中 AI 回复含 LaTeX 时自动渲染

#### 追问会话

- 服务端字典存储：`discuss_sessions[problem_id] = [messages]`
- 切换题目时清除（前端调用 `/math/api/discuss/clear`）
- 每个会话包含 system prompt，带题目和节点背景

### 8.8 项目结构（数学部分）

```
routes/math/
├── __init__.py              # Blueprint 定义（前缀 /math）
├── routes.py                # 所有数学路由
└── models/
    ├── problem_book.py      # 题本 CRUD + 统计
    ├── problem.py           # 题目 CRUD + 复习查询 + 状态同步
    └── key_node.py          # 节点 CRUD + 间隔重复算法

templates/math/
├── index.html               # 题本首页（含创建题本弹窗）
├── create.html              # 两步创建向导
├── book.html                # 题本详情
├── learn.html               # 学习页面
└── stats.html               # 统计页面

static/
├── css/math.css             # 数学样式（Times New Roman、试卷排版）
└── js/math/learn.js         # 学习页 JS
```

### 8.9 待办/可优化

- [ ] 拍照上传题目（OCR → LaTeX）
- [ ] 预设节点模板库（常见题型自动推荐关键节点）
- [ ] 学习页预加载下一题
- [ ] 追问会话持久化（重启后保留历史）
- [ ] 题目难度标签
- [ ] 数学统计图表
