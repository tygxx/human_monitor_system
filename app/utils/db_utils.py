import mysql.connector
from mysql.connector import pooling
from typing import Dict, Any, Optional
import numpy as np
from app.utils.logger import logger
from app.config.settings import DB_CONFIG

class DatabasePool:
    _instance = None
    _pool = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if DatabasePool._pool is None:
            try:
                DatabasePool._pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
                logger.info("数据库连接池初始化成功")
            except Exception as e:
                logger.error(f"数据库连接池初始化失败: {str(e)}")
                raise

    def get_connection(self):
        return self._pool.get_connection()

def with_db_connection(func):
    """数据库连接装饰器"""
    def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = DatabasePool.get_instance().get_connection()
            return func(*args, conn=conn, **kwargs)
        except Exception as e:
            logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    return wrapper 