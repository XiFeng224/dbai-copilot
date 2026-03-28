# Core database connection module
"""核心数据库连接模块"""

import mysql.connector
from mysql.connector import Error
from .database_factory import DatabaseFactory

class DatabaseConnection:
    """数据库连接管理类"""
    
    def __init__(self, host='localhost', port=3306, user='root', password='', database=''):
        """初始化数据库连接"""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except Error as e:
            print(f"数据库连接失败: {e}")
            return False
    
    def execute(self, query, params=None):
        """执行SQL查询"""
        try:
            if not self.connection or not self.cursor:
                self.connect()
            self.cursor.execute(query, params)
            return self.cursor
        except Error as e:
            print(f"SQL执行失败: {e}")
            return None
    
    def fetch_all(self, query, params=None):
        """获取所有查询结果"""
        cursor = self.execute(query, params)
        if cursor:
            return cursor.fetchall()
        return []
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
