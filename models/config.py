"""配置数据操作"""

from database.db import get_db, dict_from_row


class ConfigModel:
    """配置读写"""

    @staticmethod
    def get(key, default=''):
        """获取配置值"""
        db = get_db()
        row = db.execute('SELECT value FROM config WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else default

    @staticmethod
    def set(key, value):
        """设置配置值"""
        db = get_db()
        db.execute(
            'INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)',
            (key, value)
        )
        db.commit()

    @staticmethod
    def get_all():
        """获取所有配置"""
        db = get_db()
        rows = db.execute('SELECT * FROM config').fetchall()
        return {row['key']: row['value'] for row in rows}

    @staticmethod
    def update_batch(configs):
        """批量更新配置
        configs: dict of key-value pairs
        """
        db = get_db()
        for key, value in configs.items():
            db.execute(
                'INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)',
                (key, value)
            )
        db.commit()
