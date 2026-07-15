# 开发日志

## 2026-07-15 — 翻译模式 + Git 版本管理

### 版本管理
- [x] 初始化 Git 仓库
- [x] 回滚哈利波特原文例句集成（删除 `harry_sentence_service.py`、`build_harry_index.py`、`simplemma` 依赖）
- [x] 提交 v1.0 基线（纯 AI 造句评判模式）
- [x] 创建 `feat/translation-mode` 分支开始新功能开发
- [x] 启动时自动验证数据库完整性，空/损坏文件自动重建

### 翻译模式核心功能
- [x] 词本创建时选择模式：✍️ 造句模式 / 🌍 翻译模式（`wordbooks.mode` 字段）
- [x] 翻译模式学习流程：展示单词+原文例句 → 用户写中文翻译 → AI 评判
- [x] `judge_translation()` + `TRANSLATION_JUDGE_PROMPT` — 评判中文翻译是否准确
- [x] 翻译评判始终给出 `correct_translation` 参考翻译
- [x] 单词表新增 `input_example` 字段（用户自输例句）
- [x] 翻译模式单词无例句时自动用 AI 例句补上
- [x] 前端学习页双模式自适应

### 导入改进
- [x] TXT 导入支持 `单词|原文例句` 格式
- [x] 手动输入支持 `单词|原文例句` 格式（按换行解析，例句含逗号不乱拆）
- [x] 预览页每行新增可编辑的"原文例句"输入框
- [x] 导入页不再询问模式，以词本现有模式为准

### 界面优化
- [x] 词本详情页显示模式标签（🌍 翻译模式 / ✍️ 造句模式）
- [x] 首页词本卡片翻译模式显示小图标
- [x] 词本列表新增"原文例句"列
- [x] 词本详情页加删除词本按钮

### 已修复
- [x] `confirm_import()` 漏传 `input_example` 字段 → 例句无法入库
- [x] 备份恢复时 INSERT 漏了 `mode` 和 `input_example` → 恢复后变造句模式
- [x] 翻译模式无例句时静默降级为造句 → 改为自动用 AI 例句补上
- [x] 手动解析器按逗号拆分先于 `|` → 例句含逗号时误拆
- [x] `get_db()` 增加 `_ensure_tables()` 保障数据库始终有表
- [x] 批量操作无 `.catch()` 错误处理
- [x] `batchAction()` 每次调用追加 action input 导致重复

---

## 2026-07-02 — 学习流程重构：例句简化 + 不认识/不通过后立即重试机制 ✅

### 修改一：例句生成简化
- [x] `EXAMPLE_GENERATE_PROMPT` 要求生成简单自然、8-15 词、日常表达的例句
- [x] 强调句子结构不要太复杂，易于理解和模仿

### 修改二：不认识/不通过后立即重试
- [x] **新流程**：首次造句不通过或点击"不认识" → 展示学习材料（释义+反馈+例句）→ 点击"✍️ 再试一次" → **回到空白单词展示页（仅单词/音标/词性，看不到答案）** → 再写句子提交
- [x] 重试提交时，后端走 `process_review` 的 learning 路径：通过则 `correct_count+1`（stage 推进），不通过则 `correct_count=0`（留在 stage 0）
- [x] 重试模式下隐藏"已掌握"和"不认识"按钮，强制用户答题
- [x] 将评判初始内容（`judgeInitialContent`）和重试结果（`retryResult`）分离为独立容器，避免内容重叠显示

### 修改三：评判反馈必含目标单词
- [x] `JUDGE_SYSTEM_PROMPT` 新增要求：不通过时，`message` 中必须包含目标单词的正确用法示范

### 修改四：不通过时先展示单词含义
- [x] 评判不通过时，显示顺序改为：**单词释义 → 评判意见 → 例句**，帮助用户先理解单词含义再看反馈

### 已修复
- [x] `isLoading` 在 `showJudgeResult` 后未重置 → 重试时提交按钮被拦截
- [x] 重试结果页面同时显示旧评判内容和重试结果 → 改用容器级切换

---

## 2026-07-02 — 项目初始化 + 核心框架搭建 ✅

### 环境搭建
- [x] 创建 conda 虚拟环境 `wordfreezing`（Python 3.11）
- [x] 安装 Flask、Flask-CORS、Requests、Gunicorn
- [x] 编写 requirements.txt

### 数据库层
- [x] `database/schema.sql` — 词本(wordbooks)、单词(words)、配置(config) 三表
  - 单词表包含：词性/音标/释义/例句、学习状态/复习阶段/间隔日期/正确计数
  - 状态约束：`new` / `learning` / `mastered`
- [x] `database/db.py` — SQLite 连接管理（Flask g 上下文 + WAL 模式 + 外键）

### Models 层
- [x] `models/wordbook.py` — 词本 CRUD + 统计查询（各状态数量、进度条数据）
- [x] `models/word.py` — 单词 CRUD + 批量操作 + 搜索/分页 + 到期复习查询 + 统计
- [x] `models/config.py` — 配置 KV 读写 + 批量更新

### Services 层
- [x] `services/ai_service.py` — AI 服务（抽象 DeepSeek / Ollama）
  - `judge_sentence()` — 评判用户造句是否地道
  - `judge_translation()` — 评判中文翻译是否准确
  - `batch_complete()` — 批量补全单词信息（词性/音标/释义/例句）
  - `test_connection()` — 连接测试
- [x] `services/import_service.py` — 导入处理
  - TXT 解析（支持 `单词|例句` 格式）+ 手动输入解析
  - 自动检测 `ecdict.db` / `stardict.db` / `dictionary.db`，适配表名和列
  - ECDICT POS 格式清洗（`n:4/v:96` → `v.`）
  - 未命中词汇批量 AI 补全
  - 确认导入（批量写入，含 `input_example`）
- [x] `services/review_service.py` — 间隔重复算法
  - 状态变迁：new → mastered（直接斩）/ learning(stage 0-2) → mastered
  - 失败回退到 stage 0
  - 同一天重复通过防抖

### Flask 应用 (app.py)
- [x] 首页仪表盘：词本卡片列表 + 待复习提示 + 全局统计
- [x] 词本 CRUD：创建（含模式选择）、编辑名称、删除
- [x] 词本总览：分页表格、搜索、状态筛选、批量操作（斩/恢复/删除）+ 原文例句列
- [x] 学习流程：先复习再新词 → 造句/翻译 → AI 评判 → 状态更新 → 斩动画
- [x] 跳过学习（标记已掌握）
- [x] 导入：TXT 文件 / 手动输入 → 预览（例句可编辑）→ 确认入库
- [x] 导出：JSON / CSV 格式
- [x] 统计页面：全局统计 + 各词本进度条
- [x] 设置页面：AI 引擎切换（DeepSeek/Ollama）、连接测试
- [x] 数据管理：完整备份导出/导入恢复（含 mode 和 input_example）

### 模板 (Jinja2)
- [x] `base.html` — 导航栏 + 布局
- [x] `index.html` — 仪表盘 + 创建词本弹窗（含模式选择）
- [x] `wordbook.html` — 词本总览 + 表格 + 批量操作 + 分页 + 导出下拉 + 删除词本
- [x] `learn.html` — 卡片式学习界面 + 双模式自适应 + 斩动画
- [x] `import.html` — Tab 切换（文件/手动）+ 预览表格（例句可编辑）
- [x] `stats.html` — 统计卡片 + 词本进度列表
- [x] `settings.html` — 配置表单 + 连接测试 + 备份恢复
- [x] `error.html` — 错误页

### 静态资源
- [x] `static/css/style.css` — 完整样式（卡片、进度条、按钮、弹窗、表格、模式标签）

### 已修复
- [x] TypeError: 当词本无单词时 SQLite SUM() 返回 NULL → 加 `COALESCE` + 模板 `| int` 保护
- [x] 模板中 `wb.new_count / total` 分母为零或值为 None → 加 `| int` 和 `or 1` 双重保护

## 2026-07-02 — 本地词典集成 ✅

- [x] 用户下载 `stardict.db`（812MB，ECDICT 同源）放入 `dictionary/` 目录
- [x] 词典自动检测：支持 `ecdict.db` / `stardict.db` / `dictionary.db`
- [x] 自动探测表名（ecdict / stardict / dict）和列结构
- [x] 中文释义优先使用 `translation` 列
- [x] ECDICT POS 格式清洗（`n:4/v:96` → `v.`）
- [x] 词典未命中时自动降级到 AI 补全

### 验证
- `abandon` → pos=v. phonetic=ә'bændәn ✅
- `ability` → pos=n. ✅
- `xylophone` → pos=n. ✅
- `zzzzzzz` → 未命中，正常降级 ✅

## 2026-07-02 — UI/UX 修复 + 模型选择优化 ✅

### 学习页面释义隐藏
- [x] 学习时只展示单词、音标、词性，**不展示中文释义**
- [x] 释义和例句仅在 AI 评判"不通过"后才展示供学习

### 设置页模型选择
- [x] DeepSeek 模型从 `<select>` 下拉改为 `<input>` 自由输入 + `<datalist>` 建议
- [x] 支持 `deepseek-chat`、`deepseek-reasoner`、`deepseek-flash` 及未来任意模型
- [x] 与 Ollama 模型输入风格统一

### AI Token 估算
- [x] 每次造句评判约 **300-400 tokens**
- [x] 每次翻译评判约 **300-400 tokens**
- [x] DeepSeek-V3 月费约 **¥0.5-1.0**（假设每天 50 词）
- [x] 批量补全约 **50-100 tokens/词**

### 已修复
- [x] TypeError: 当词本无单词时 SQLite SUM() 返回 NULL → 加 `COALESCE` + 模板 `| int` 保护
- [x] 模板中 `wb.new_count / total` 分母为零或值为 None → 加 `| int` 和 `or 1` 双重保护
- [x] 学习页释义泄露（`word.definition` 混入 `wordPos`）→ 只显示词性
- [x] 设置页模型选择器不支持 Flash → 改为自由输入

---

### 待办
- [ ] 添加单元测试
- [ ] Docker 部署配置
- [ ] 学习页预加载下一个单词（性能优化）
- [ ] 本地词典查询 L0 缓存
