# Lock analyzer module
"""锁等待分析模块"""

import re
from ..core import DatabaseConnection

class LockAnalyzer:
    """数据库锁等待分析工具"""
    
    def __init__(self, db_connection):
        """初始化锁分析工具"""
        self.db = db_connection
    
    def analyze_lock_waits(self):
        """分析当前锁等待"""
        # 查询锁等待信息
        query = """
        SELECT 
            r.trx_id AS waiting_trx_id,
            r.trx_mysql_thread_id AS waiting_thread,
            r.trx_query AS waiting_query,
            b.trx_id AS blocking_trx_id,
            b.trx_mysql_thread_id AS blocking_thread,
            b.trx_query AS blocking_query
        FROM 
            information_schema.innodb_lock_waits w
        INNER JOIN 
            information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
        INNER JOIN 
            information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
        """
        
        result = self.db.fetch_all(query)
        return result
    
    def detect_deadlocks(self):
        """检测死锁"""
        # 获取InnoDB状态
        query = "SHOW ENGINE INNODB STATUS"
        result = self.db.fetch_all(query)
        
        if not result:
            return []
        
        status = result[0]['Status']
        deadlocks = []
        
        # 解析死锁信息
        deadlock_pattern = re.compile(r'DEADLOCK DETECTED.*?\(1\) TRANSACTION:(.*?)\(2\) TRANSACTION:(.*?)WE ROLL BACK TRANSACTION \(1\)', re.DOTALL)
        matches = deadlock_pattern.findall(status)
        
        for match in matches:
            trx1 = match[0].strip()
            trx2 = match[1].strip()
            deadlocks.append({
                'transaction1': trx1,
                'transaction2': trx2
            })
        
        return deadlocks
    
    def get_lock_statistics(self):
        """获取锁统计信息"""
        # 查询锁信息
        query = """
        SELECT 
            lock_type,
            lock_table,
            lock_index,
            lock_mode,
            lock_status
        FROM 
            information_schema.innodb_locks
        """
        
        locks = self.db.fetch_all(query)
        
        # 统计锁类型
        lock_stats = {}
        for lock in locks:
            lock_type = lock['lock_type']
            if lock_type not in lock_stats:
                lock_stats[lock_type] = 0
            lock_stats[lock_type] += 1
        
        return {
            'locks': locks,
            'statistics': lock_stats
        }
    
    def analyze_blocking_chain(self):
        """分析阻塞链"""
        lock_waits = self.analyze_lock_waits()
        
        # 构建阻塞链
        blocking_chain = {}
        for wait in lock_waits:
            waiting_thread = wait['waiting_thread']
            blocking_thread = wait['blocking_thread']
            
            if blocking_thread not in blocking_chain:
                blocking_chain[blocking_thread] = []
            blocking_chain[blocking_thread].append({
                'waiting_thread': waiting_thread,
                'waiting_query': wait['waiting_query'],
                'blocking_query': wait['blocking_query']
            })
        
        return blocking_chain
    
    def get_long_running_transactions(self, threshold=60):
        """获取长时间运行的事务"""
        query = """
        SELECT 
            trx_id,
            trx_mysql_thread_id AS thread_id,
            trx_query,
            trx_started,
            TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS duration
        FROM 
            information_schema.innodb_trx
        WHERE 
            TIMESTAMPDIFF(SECOND, trx_started, NOW()) > %s
        ORDER BY 
            duration DESC
        """
        
        result = self.db.fetch_all(query, (threshold,))
        return result
