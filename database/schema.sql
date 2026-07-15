-- WordFreezing 数据库 Schema

-- 词本表
CREATE TABLE IF NOT EXISTS wordbooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
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
