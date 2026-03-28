# 数据库工厂模块
"""数据库工厂模块 - 支持多种数据库类型"""

import abc
import logging
from typing import Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConnection(abc.ABC):
    """数据库连接抽象基类"""
    
    @abc.abstractmethod
    def connect(self) -> bool:
        """连接数据库"""
        pass
    
    @abc.abstractmethod
    def disconnect(self):
        """断开数据库连接"""
        pass
    
    @abc.abstractmethod
    def fetch_all(self, query: str) -> Optional[list]:
        """执行查询并返回所有结果"""
        pass
    
    @abc.abstractmethod
    def execute(self, query: str) -> bool:
        """执行SQL语句"""
        pass
    
    @abc.abstractmethod
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        pass

class MySQLConnection(DatabaseConnection):
    """MySQL数据库连接"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect(self) -> bool:
        try:
            import mysql.connector
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            logger.info(f"成功连接到MySQL数据库: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"连接MySQL数据库失败: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("MySQL数据库连接已关闭")
    
    def fetch_all(self, query: str) -> Optional[list]:
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return None
    
    def execute(self, query: str) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"执行SQL失败: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        try:
            query = "SELECT VERSION() as version"
            result = self.fetch_all(query)
            return {
                'type': 'MySQL',
                'version': result[0]['version'] if result else 'Unknown',
                'host': self.host,
                'port': self.port,
                'database': self.database
            }
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {'type': 'MySQL', 'error': str(e)}

class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL数据库连接"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect(self) -> bool:
        try:
            import psycopg2
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            logger.info(f"成功连接到PostgreSQL数据库: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"连接PostgreSQL数据库失败: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL数据库连接已关闭")
    
    def fetch_all(self, query: str) -> Optional[list]:
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return None
    
    def execute(self, query: str) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"执行SQL失败: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        try:
            query = "SELECT version() as version"
            result = self.fetch_all(query)
            return {
                'type': 'PostgreSQL',
                'version': result[0]['version'] if result else 'Unknown',
                'host': self.host,
                'port': self.port,
                'database': self.database
            }
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {'type': 'PostgreSQL', 'error': str(e)}

class SQLServerConnection(DatabaseConnection):
    """SQL Server数据库连接"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect(self) -> bool:
        try:
            import pyodbc
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.host},{self.port};DATABASE={self.database};UID={self.user};PWD={self.password}"
            self.connection = pyodbc.connect(connection_string)
            logger.info(f"成功连接到SQL Server数据库: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"连接SQL Server数据库失败: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("SQL Server数据库连接已关闭")
    
    def fetch_all(self, query: str) -> Optional[list]:
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return None
    
    def execute(self, query: str) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"执行SQL失败: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        try:
            query = "SELECT @@VERSION as version"
            result = self.fetch_all(query)
            return {
                'type': 'SQL Server',
                'version': result[0]['version'] if result else 'Unknown',
                'host': self.host,
                'port': self.port,
                'database': self.database
            }
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {'type': 'SQL Server', 'error': str(e)}

class DatabaseFactory:
    """数据库工厂类"""
    
    @staticmethod
    def create_connection(db_type: str, host: str, port: int, user: str, password: str, database: str) -> DatabaseConnection:
        """创建数据库连接"""
        if db_type.lower() == 'mysql':
            return MySQLConnection(host, port, user, password, database)
        elif db_type.lower() == 'postgresql':
            return PostgreSQLConnection(host, port, user, password, database)
        elif db_type.lower() in ['sqlserver', 'mssql']:
            return SQLServerConnection(host, port, user, password, database)
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    @staticmethod
    def get_supported_databases() -> list:
        """获取支持的数据库类型列表"""
        return ['MySQL', 'PostgreSQL', 'SQL Server']
    
    @staticmethod
    def get_default_ports() -> Dict[str, int]:
        """获取默认端口号"""
        return {
            'MySQL': 3306,
            'PostgreSQL': 5432,
            'SQL Server': 1433
        }