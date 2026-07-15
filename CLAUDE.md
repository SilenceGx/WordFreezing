# CLAUDE.md

## 项目概述

WordFreezing — 个人背单词应用。通过 AI 造句评判 + 间隔重复，真正掌握单词用法。
详情见 `PROJECT_SPEC.md`，开发日志见 `DEVELOPMENT_LOG.md`。

### 核心学习流程
1. 展示单词（英文+音标+词性，隐藏释义例句）
2. 用户造句提交，或点"不认识"
3. AI 评判：
   - **通过** → mastered（斩）
   - **不通过/不认识** → 先展示单词释义+评判反馈+例句学习 → 点击"✍️ 再试一次" → **回到空白单词展示页（看不到答案）** → 再造一句提交
     - 通过 → correct_count+1，学习阶段推进
     - 不通过 → correct_count=0，留在当前阶段
4. 结果展示后点"继续"进入下一个词

### 关键文件
- `app.py` — Flask 主入口（所有路由）
- `services/ai_service.py` — AI 评判 + 批量补全
- `services/review_service.py` — 间隔重复算法
- `templates/learn.html` — 学习页面（含完整 JS 流程）
- `static/css/style.css` — 全部样式

### 重点约束
- 学习时只展示单词、音标、词性，**不展示中文释义**
- AI 例句要简单、地道、8-15 词
- 不通过时反馈必须包含目标单词的正确用法示范
- 显示顺序：先单词含义 → 再评判意见 → 最后例句

## Agent Skills

### grill-me / grilling

当用户说 `/grill-me` 或 `/grilling`，或者使用任何"grill"相关触发词时，执行以下操作：

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.

If a question can be answered by exploring the codebase, explore the codebase instead.

详细的技能定义存放在 `.agents/skills/grill-me/SKILL.md` 和 `.agents/skills/grilling/SKILL.md` 中。
