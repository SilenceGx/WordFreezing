# WordFreezing — 个人背单词应用

> 通过 AI 造句评判 + 间隔重复，真正掌握单词的用法。

## 一、核心理念

区别于传统"看单词→记释义"的背词方式，本应用要求用户**为每个单词写一个句子**，由 AI 评判是否足够地道、符合 native speaker 语境。通过科学的间隔重复机制，确保用户**真正掌握**单词的用法，而非死记硬背释义。

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
- 每个词本有：名称、创建时间
- 词本内包含多个单词

### 3.2 单词 (Word)

每个单词包含以下字段：

| 字段 | 说明 | 来源 |
|---|---|---|
| word | 英文单词 | 用户提供（TXT 导入或手动输入） |
| pos | 词性 (n./v./adj./adv. 等) | 本地词典查询 / AI 补全 |
| phonetic | 音标 | 本地词典查询 / AI 补全 |
| definition | 释义 | 本地词典查询 / AI 补全 |
| examples | 例句列表（至少 2 条） | AI 预生成（一次性批量），固定不变 |
| status | 学习状态：`new` / `learning` / `mastered` | 系统根据学习行为自动更新，支持手动调整 |
| review_stage | 复习阶段：0=首次, 1=1天, 2=3天, 3=7天 | 系统自动跟踪 |
| last_review_date | 上次复习日期 | 系统自动记录 |
| next_review_date | 下次计划复习日期 | 系统自动计算 |
| correct_count | 累计通过次数（连续，失败归零） | 系统自动记录 |

### 3.3 学习状态变迁

```
new ──── 首次造句通过 ────→ mastered ✅（直接斩）
  │
  ├── 首次造句不通过 ──→ learning (stage 0) ──→ 立即重试(不看答案)
  │                                                ├─ 通过 → correct_count+1 → stage 1
  │                                                └─ 不通过 → correct_count=0 → 留 stage 0
  │
  └── 不认识 ──→ learning (stage 0) ──→ 先看释义例句 → 立即重试(不看答案)
                                           ├─ 通过 → correct_count+1 → stage 1
                                           └─ 不通过 → correct_count=0 → 留 stage 0

learning (stage 0) ── 1 天后到期 → 造句通过 ──→ learning (stage 1)
learning (stage 1) ── 3 天后到期 → 造句通过 ──→ learning (stage 2)
learning (stage 2) ── 7 天后到期 → 造句通过 ──→ mastered ✅（斩！）

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
  - 词本名称、总词数
  - 进度分布：`new` / `learning` / `mastered` 各数量
- "创建新词本"按钮
- "导入词本"按钮
- 全局统计概览：总词数、已斩词数

### 4.2 学习流程

#### 核心流程（每个单词）

1. **展示单词**：英文、词性、音标（释义和例句隐藏，不给提示）
2. **用户操作**：
   - 在输入框写一个句子（无字数限制），点击"提交"按钮
   - 或点击"✅ 已掌握"按钮（直接 mastery，跳过造句）
   - 或点击"❌ 不认识"按钮
3. **AI 评判**（提交后）：
   - 显示加载状态，防止重复提交
   - 深度求索 DeepSeek API（默认）/ 本地 Ollama（可选）
4. **评判结果**：
   - **通过** → 显示通过提示，执行"斩"动画效果，进入下一个词
   - **不通过** → 分两步：
     a. **学习页**：先展示单词释义（单词/音标/词性/中文释义），再展示评判反馈（仅问题描述，**不提供改正例句**），最后展示两个地道例句（优先来自《哈利波特》原著原文，标注 `📖 哈利波特`；查不到时 AI 生成，标注 `🤖 AI生成`）→ 底部出现"✍️ 再试一次"按钮
     b. **重试页**：点击"再试一次"后回到干净单词展示页（**与初始一样，仅单词/音标/词性，看不到释义和例句**），用户再写一个句子提交 → AI 评判
       - 通过 → `correct_count +1`，学习阶段推进（stage 0→1）
       - 不通过 → `correct_count = 0`，留在 stage 0
       显示结果后点击"继续"进入下个词
5. **"不认识"流程**：展示单词完整信息（释义/词性/音标）+ 两个例句（优先 HP 原文，标注来源）→ 底部出现"✍️ 再试一次"按钮 → 同上方重试页流程
6. **"斩"动画效果**：通过时的视觉反馈（类似百词斩的消除动效）

#### 先复习再学新词

- 用户进入词本时，优先展示**今日到期**的 learning 单词
- 复习完毕后，进入 new 单词的学习
- 用户可随时中断，进度自动保存

### 4.3 词本总览

- 表格展示词本中所有单词
- 列：单词、词性、释义、状态（new / learning / mastered）
- 支持搜索/过滤单词
- 每行可操作：
  - "斩"按钮（手动标记为 mastered）
  - "恢复"按钮（将 mastered 恢复为 new）
- 批量操作：勾选多个单词，批量标记 mastered 或恢复
- 分页支持（词多时）

### 4.4 词本管理

- 编辑词本名称
- 编辑单词：修改词性、音标、释义、例句
- 删除单词（从词本中移除）
- 批量删除

### 4.5 导入词本

#### 方式一：TXT 文件导入
- 用户上传 TXT 文件，每行一个单词
- 示例：
  ```
  abandon
  ability
  about
  ...
  ```

#### 方式二：手动逐词输入
- 在界面上逐个输入单词

#### 处理流程
1. 用户输入词本名称
2. 提供单词列表（文件或手工输入）
3. 系统处理：
   - 查询**本地词典数据库**（ECDICT 开源词库，MIT 许可）
     - 命中 → 自动提取词性、音标、释义（零 API 成本）
   - 未命中词汇 + 例句生成 → 调用 AI 一次性批量补全
4. 处理结果显示给用户确认
5. 确认后批量入库
6. 自动跳转到词本总览页面

### 4.6 导出词本

- 支持 **JSON 格式** 导出：保留完整单词信息
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
  - 导出完整数据备份
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

### 5.2 项目结构（初始设计）

```
WordFreezing/
├── app.py                 # Flask 主入口
├── requirements.txt       # Python 依赖
├── database/
│   ├── schema.sql         # 数据库建表语句
│   └── wordfreezing.db    # SQLite 数据文件（运行时生成）
├── dictionary/
│   ├── ecdict.db          # 开源词典数据（预置）
│   └── harry_index.db     # 哈利波特倒排索引（运行时生成）
├── scripts/
│   └── build_harry_index.py  # HP 索引预处理脚本
├── models/
│   ├── wordbook.py        # 词本数据操作
│   ├── word.py            # 单词数据操作
│   └── config.py          # 配置数据操作
├── services/
│   ├── ai_service.py      # AI 评判 + 补全（抽象 DeepSeek/Ollama）
│   ├── harry_sentence_service.py  # 哈利波特例句查询 + AI 精选
│   ├── import_service.py  # 导入处理逻辑
│   └── review_service.py  # 间隔重复算法
├── static/
│   ├── css/
│   ├── js/
│   └── img/
└── templates/
    ├── base.html
    ├── index.html         # 首页
    ├── wordbook.html      # 词本总览
    ├── learn.html         # 学习界面
    ├── import.html        # 导入词本
    ├── stats.html         # 统计页面
    └── settings.html      # 设置页面
```

### 5.3 AI 评判要点

1. **评判提示词**：AI 只判断 pass/fail + 问题描述（message），**不再提供改正例句**（suggestion 已废弃）。不通过时系统会额外展示《哈利波特》原文例句供用户自然体会语感
2. **例句生成提示词**：要求生成简单自然、8-15 词、日常表达的例句，句子结构不复杂。**优先从 HP 索引获取**，查不到时降级到 AI 生成

### 5.6 哈利波特原文例句集成

#### 5.6.1 倒排索引
- 离线预处理流程（`scripts/build_harry_index.py`）：
  1. 读取 `HarryEnglish/` 下 7 本英文原著 .txt
  2. 正则分句 + 缩写保护（Mr./Mrs./Dr./St. 等）
  3. simplemma 词形还原
  4. 写入 `dictionary/harry_index.db`（sentences + word_index 两表）
- 应用启动时自动检测，不存在则构建（约 20 秒）

#### 5.6.2 例句获取流程
```
需要例句 → 查 word_index（lemma 匹配）→ 候选句预过滤 → AI 精选 1-2 句
                                                     ↓ 查不到
                                             降级到 AI 生成
```

#### 5.6.3 来源标注
- HP 原文例句 → 标记 `📖 哈利波特`（代码前缀 `[HP]`）
- AI 生成例句 → 标记 `🤖 AI生成`（代码前缀 `[AI]`）
- 判官不通过时额外展示 `📖 哈利波特原文` 专用标签

### 5.4 重试机制

- 首次不通过或点"不认识"后，单词立即进入 `learning`（stage 0）
- 前端立即提供一次重试机会：回到空白单词展示页（**看不到释义/例句/反馈**），用户再写句子提交
- 重试走 `process_review` learning 路径：
  - 通过 → `correct_count +1`，stage 0→1，next_review = 3 天后
  - 不通过 → `correct_count = 0`，留在 stage 0，next_review = 1 天后
- 重试结果展示后用户点击"继续"进入下一个词

### 5.5 间隔重复算法逻辑（伪代码）
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
|  📖 CET-6 高频词   142词               |
|      new: 120  learning: 18  ✅: 4     |
|                                        |
|  📖 阅读生词       36词                |
|      new: 20  learning: 10  ✅: 6      |
|                                        |
|  [+ 创建新词本] [📥 导入词本]          |
|                                        |
|  📊 总览: 236 词 | ✅ 已斩 13 词       |
+----------------------------------------+
```

### 学习界面
```
+----------------------------------------+
|  ← CET-6高频词   进度 new: 84/120       |
|  ------------------------------------- |
|        +--------------+                |
|        | recommend    |                |
|        | /ˈrekəmend/  |                |
|        | v. 推荐      |                |
|        +--------------+                |
|                                        |
|  +----------------------------------+  |
|  | 用 "recommend" 造一个句子...      |  |
|  |                                  |  |
|  |                                  |  |
|  +----------------------------------+  |
|                                        |
|       [ 提交句子 ]   [ ✅ 已掌握 ]       |
+----------------------------------------+
```

### 评判不通过（先展示含义，再展示评价和例句，最后可重试）
```
+----------------------------------------+
|  ❌ 不够地道                            |
|  ------------------------------------- |
|  ┌─ recommend  /ˈrekəmend/  v. ──────┐ |
|  │  释义: 推荐、建议                  │ |
|  └────────────────────────────────────┘ |
|                                        |
|  "I recommend you to go" 中的          |
|  "recommend sb to do" 是中式用法，     |
|  更地道的说法是：                       |
|  "I recommend that you go..."         |
|                                        |
|  📖 例句学习                           |
|  1. I recommend that you see a doctor. |
|  2. She recommended this book to all   |
|     her students.                      |
|                                        |
|  ─────────────────────────────────     |
|         [ ✍️ 再试一次 ]                |
|    (点击后回到空白单词展示页再答一次)    |
+----------------------------------------+
```

### 词本总览
```
+----------------------------------------+
|  ← 首页   📖 CET-6 高频词              |
|  总计 142 词 | new 120 | lrn 18 | ✅ 4 |
|                                        |
|  [✏️ 编辑] [▶ 开始学习] [📥 导入追加]   |
|  ------------------------------------- |
|  搜索: [________________]              |
|                                        |
|  □ 单词     词性  状态     操作         |
|  □ abandon  v.    new      [✅斩]      |
|  □ ability  n.    ✅ mastered [↩恢复]  |
|  □ able     adj.  learning [✅斩]      |
|  □ about    prep. ✅ mastered [↩恢复]  |
|                                        |
|  已选 2 项   [批量斩] [批量恢复]        |
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
