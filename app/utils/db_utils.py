import functools
import mysql.connector
from mysql.connector import pooling
from typing import Dict, Any, Optional, List
import numpy as np
from app.utils.logger import logger
from app.config.settings import DB_CONFIG

# 创建数据库连接池
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name=DB_CONFIG['pool_name'],
        pool_size=DB_CONFIG['pool_size'],
        **{k: v for k, v in DB_CONFIG.items() if k not in ['pool_name', 'pool_size']}
    )
    logger.info("数据库连接池初始化成功")
except Exception as e:
    logger.error(f"数据库连接池初始化失败: {str(e)}")
    raise

def with_db_connection(func):
    """数据库连接装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = connection_pool.get_connection()
            return func(*args, **kwargs, conn=conn)
        except Exception as e:
            logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"关闭数据库连接失败: {str(e)}")
    return wrapper

def execute_query(sql: str, params: tuple = None) -> List[Dict]:
    """执行查询"""
    @with_db_connection
    def _execute(conn=None):
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    return _execute()

def execute_update(sql: str, params: tuple = None) -> int:
    """执行更新"""
    @with_db_connection
    def _execute(conn=None):
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    return _execute() 