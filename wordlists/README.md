# 📚 词库目录

WordFreezing 可直接导入的现成词表。同源雅思核心词提供三种格式，按需取用。

## 文件一览

| 文件 | 格式 | 内容 | 最适合 |
|---|---|---|---|
| `ielts-core-3592.txt` | 每行一个单词 | 仅单词（小写） | 造句模式；文件最小，其余字段交给词典/AI 补全 |
| `ielts-core-3592-examples.txt` | `单词\|例句` | 单词 + 1 条地道例句 | 翻译模式开箱即用；例句现成，省 AI 生成调用 |
| `ielts-core-3592-full.json` | WordFreezing JSON 导出格式 | 全字段（词性/音标/释义/例句） | 数据迁移、二次处理；格式与「导出词本 → JSON」一致 |

## 快速开始（2 分钟）

1. **配置 AI**（如果还没做）：打开「设置」→ 选择 DeepSeek 或 Ollama → 填入 API Key → 保存
2. **导入词库**：打开「导入词本」→ 选择 TXT 文件上传（`ielts-core-3592.txt` 或 `ielts-core-3592-examples.txt`）→ 预览确认 → 完成
3. **开始学习**：词本详情页点「▶ 开始学习」

> 提示：想用翻译模式的话，先建一个「🌍 翻译模式」词本，再导入到这个词本。

## 格式说明

### 纯单词版

```
emperor
exact
traditional
```

导入后，ECDICT 词典存在时本地补全词性/音标/释义；未命中或没配词典时走 AI 批量补全。

### 带例句版

```
emperor|The emperor ruled the vast empire with an iron fist.
exact|Can you give me the exact time of the meeting?
traditional|They wore traditional costumes for the festival.
```

`单词|例句` 是 WordFreezing 的导入格式：单词在前、例句在后、竖线分隔。例句会在翻译模式直接使用，造句模式答错时作为学习材料展示。

### 完整 JSON 版

```json
{
  "wordbook": "雅思核心词",
  "exported_at": "2026-08-02",
  "words": [
    {
      "word": "emperor",
      "pos": "n.",
      "phonetic": "/ˈempərə/",
      "definition": "皇帝，君主",
      "examples": ["The emperor ruled the vast empire with an iron fist."]
    }
  ]
}
```

字段：`word` / `pos` / `phonetic` / `definition` / `examples`（列表）。与 WordFreezing 应用内「词本 → 导出 → JSON」的输出结构一致，可互通。

## 来源与版权

- **单词来源**：[fanhongtao/IELTS](https://github.com/fanhongtao/IELTS) — 新东方《雅思词汇词根+联想记忆法（乱序便携版）》逐词录入
- **清洗**：提取每行首个 token → 去 `*` 难度标记 → 保留连字符复合词（如 `easy-going`）→ 丢弃多词短语（如 `roll film`）→ 去重保持原序（3611 词条 → 3592 唯一词）
- **版权**：原仓库未声明许可证。本目录仅提取**单词词目**（不包含原文件的释义/音标/例句文本）；词性/音标/释义/例句为 **DeepSeek AI 生成**，非原书内容

## 常见问题

**Q: 为什么纯单词版导入后有些词没有释义？**
A: 导入本身只存单词。释义由导入流程补全：ECDICT 词典命中则本地补全，未命中走 AI 批量补全。配置 AI 后重新导入（或学习时触发补全）即可。

**Q: 完整 JSON 怎么导入？**
A: 目前 WordFreezing 的导入入口只支持 TXT（纯单词 / `单词|例句`）。JSON 与「导出词本 → JSON」格式一致，适合数据备份、迁移和二次处理，也便于未来扩展 JSON 导入。

**Q: 词汇量和雅思考试匹配吗？**
A: 本词表覆盖新东方雅思词汇乱序便携版全书，约 3592 个不重复词目，适合雅思 5.5-7.5 分段备考。

**Q: 能自行扩充吗？**
A: 可以。按 `单词` 或 `单词|例句` 格式追加行即可，导入时自动去重（同词保留第一个例句）。
