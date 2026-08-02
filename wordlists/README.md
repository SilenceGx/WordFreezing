# 词库目录

可直接导入 WordFreezing 的词表文件。同一份雅思核心词提供三种格式，按需取用：

| 文件 | 格式 | 内容 | 导入方式 |
|---|---|---|---|
| `ielts-core-3592.txt` | 每行一个单词 | 仅单词 | 导入页直接上传，词性/音标/释义/例句由 ECDICT 或 AI 补全 |
| `ielts-core-3592-examples.txt` | `单词\|例句` | 单词 + 1 条地道例句 | 导入页直接上传，翻译模式开箱即用，其余字段 AI 补全 |
| `ielts-core-3592-full.json` | WordFreezing JSON 导出格式 | 全字段（词性/音标/释义/例句） | 与「导出词本 → JSON」格式一致，可用于数据迁移/二次处理 |

## 来源

[fanhongtao/IELTS](https://github.com/fanhongtao/IELTS) — 新东方《雅思词汇词根+联想记忆法（乱序便携版）》逐词录入（该仓库未声明许可证，本目录仅提取单词词目，不含原文件释义等受版权保护的文本；释义/音标/例句为 DeepSeek AI 生成）。

## 清洗规则

- 提取每行首个 token 作为单词，去除末尾 `*` 难度标记
- 保留连字符复合词（如 `easy-going`, `well-being`）
- 丢弃多词短语（如 `roll film`，WordFreezing 按单词导入）
- 去重保持原序（3611 词条 → 3592 唯一词）

## 生成方式

1. 纯单词版：`parse_txt` 可解析，导入后走词典/AI 补全
2. 带例句版：`单词|例句` 格式，例句来自 AI 补全结果的第一条
3. 完整 JSON：与应用内「导出 → JSON」格式一致（`{wordbook, exported_at, words: []}`）
