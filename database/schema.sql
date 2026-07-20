-- WordFreezing 数据库 Schema

-- 词本表
CREATE TABLE IF NOT EXISTS wordbooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mode TEXT DEFAULT 'writing',       -- 学习模式: 'writing'（造句） / 'translation'（翻译）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 单词表
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wordbook_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    pos TEXT DEFAULT '',           -- 词性 (n./v./adj./adv. 等)
    phonetic TEXT DEFAULT '',      -- 音标
    definition TEXT DEFAULT '',    -- 释义
    examples TEXT DEFAULT '[]',    -- 例句列表，JSON 数组格式
    input_example TEXT DEFAULT '', -- 用户自输例句（翻译模式用，来自阅读原文）
    status TEXT DEFAULT 'new' CHECK(status IN ('new', 'learning', 'mastered')),
    review_stage INTEGER DEFAULT 0,  -- 复习阶段: 0=首次, 1=1天, 2=3天, 3=7天
    correct_count INTEGER DEFAULT 0, -- 累计通过次数
    last_review_date TEXT DEFAULT '', -- 上次复习日期 YYYY-MM-DD
    next_review_date TEXT DEFAULT '', -- 下次复习日期 YYYY-MM-DD
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wordbook_id) REFERENCES wordbooks(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_words_wordbook_id ON words(wordbook_id);
CREATE INDEX IF NOT EXISTS idx_words_status ON words(status);
CREATE INDEX IF NOT EXISTS idx_words_next_review ON words(next_review_date);

-- 配置表
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 默认配置
INSERT OR IGNORE INTO config (key, value) VALUES ('ai_provider', 'deepseek');
INSERT OR IGNORE INTO config (key, value) VALUES ('deepseek_api_key', '');
INSERT OR IGNORE INTO config (key, value) VALUES ('deepseek_model', 'deepseek-chat');
INSERT OR IGNORE INTO config (key, value) VALUES ('ollama_base_url', 'http://localhost:11434');
INSERT OR IGNORE INTO config (key, value) VALUES ('ollama_model', 'llama3');
INSERT OR IGNORE INTO config (key, value) VALUES ('deepseek_base_url', 'https://api.deepseek.com');

-- ==================== 数学模块 ====================

-- 题本表
CREATE TABLE IF NOT EXISTS problem_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 题目表
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES problem_books(id) ON DELETE CASCADE,
    problem_text TEXT NOT NULL,       -- LaTeX 题目
    solution_text TEXT NOT NULL,      -- LaTeX 完整解答
    status TEXT NOT NULL DEFAULT 'new'
        CHECK(status IN ('new','learning','mastered')),
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 关键节点表
CREATE TABLE IF NOT EXISTS key_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    node_order INTEGER NOT NULL,       -- 排序
    title TEXT NOT NULL,               -- 节点标题："分部积分法选择"
    description TEXT NOT NULL,         -- 方法描述
    formula TEXT DEFAULT '',           -- 关键公式（LaTeX），可选
    status TEXT NOT NULL DEFAULT 'new'
        CHECK(status IN ('new','learning','mastered')),
    review_stage INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    last_review_date TEXT,
    next_review_date TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_problems_book ON problems(book_id);
CREATE INDEX IF NOT EXISTS idx_key_nodes_problem ON key_nodes(problem_id);
CREATE INDEX IF NOT EXISTS idx_key_nodes_review ON key_nodes(next_review_date);

-- ==================== 作文模块 ====================

-- 作文本表
CREATE TABLE IF NOT EXISTS essay_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 作文表
CREATE TABLE IF NOT EXISTS essays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_book_id INTEGER NOT NULL REFERENCES essay_books(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    author TEXT DEFAULT '',
    content TEXT NOT NULL,
    summary TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_essays_book ON essays(essay_book_id);
