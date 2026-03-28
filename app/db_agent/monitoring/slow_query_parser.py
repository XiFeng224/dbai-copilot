# Slow query parser module
"""慢查询解析模块"""

import re
import os
from datetime import datetime

class SlowQueryParser:
    """慢查询日志解析器"""
    
    def __init__(self):
        """初始化解析器"""
        # 慢查询日志格式正则表达式
        self.pattern = re.compile(
            r'# Time: (.*?)\n'
            r'# User@Host:.*?\n'
            r'# Query_time: ([\d.]+)\s+Lock_time: ([\d.]+)\s+Rows_sent: (\d+)\s+Rows_examined: (\d+)\n'
            r'(SELECT.*?);',
            re.DOTALL
        )
    
    def parse_log(self, log_file):
        """解析慢查询日志"""
        if not os.path.exists(log_file):
            return []
        
        queries = []
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            matches = self.pattern.findall(content)
            
            for match in matches:
                time_str, query_time, lock_time, rows_sent, rows_examined, sql = match
                
                # 解析时间
                try:
                    timestamp = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                except:
                    timestamp = datetime.now()
                
                query = {
                    'timestamp': timestamp,
                    'query_time': float(query_time),
                    'lock_time': float(lock_time),
                    'rows_sent': int(rows_sent),
                    'rows_examined': int(rows_examined),
                    'sql': sql.strip()
                }
                queries.append(query)
        
        return queries
    
    def parse_from_db(self, db_connection):
        """从数据库中获取慢查询"""
        # 检查慢查询是否启用
        query = "SHOW VARIABLES LIKE 'slow_query_log'"
        result = db_connection.fetch_all(query)
        if not result or result[0]['Value'] != 'ON':
            return []
        
        # 获取慢查询日志文件路径
        query = "SHOW VARIABLES LIKE 'slow_query_log_file'"
        result = db_connection.fetch_all(query)
        if not result:
            return []
        
        log_file = result[0]['Value']
        return self.parse_log(log_file)
    
    def get_top_slow_queries(self, queries, top_n=10):
        """获取Top N慢查询"""
        sorted_queries = sorted(queries, key=lambda x: x['query_time'], reverse=True)
        return sorted_queries[:top_n]
    
    def aggregate_by_sql_pattern(self, queries):
        """按SQL模式聚合慢查询"""
        patterns = {}
        
        for query in queries:
            # 标准化SQL
            normalized_sql = self._normalize_sql(query['sql'])
            
            if normalized_sql not in patterns:
                patterns[normalized_sql] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'sample_sql': query['sql'],
                    'queries': []
                }
            
            patterns[normalized_sql]['count'] += 1
            patterns[normalized_sql]['total_time'] += query['query_time']
            patterns[normalized_sql]['avg_time'] = patterns[normalized_sql]['total_time'] / patterns[normalized_sql]['count']
            patterns[normalized_sql]['queries'].append(query)
        
        # 按平均执行时间排序
        sorted_patterns = sorted(patterns.values(), key=lambda x: x['avg_time'], reverse=True)
        return sorted_patterns
    
    def _normalize_sql(self, sql):
        """标准化SQL，去除常量值"""
        # 转为小写
        sql = sql.lower()
        
        # 移除注释
        sql = re.sub(r'/*.*?*/', '', sql)
        
        # 替换数值常量为?
        sql = re.sub(r'\b\d+\b', '?', sql)
        
        # 替换字符串常量为?
        sql = re.sub(r"'[^']*'", '?', sql)
        
        # 标准化空白
        sql = re.sub(r'\s+', ' ', sql).strip()
        
        return sql
