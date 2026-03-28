# SQL fingerprint module
"""SQL指纹聚类模块"""

import re
import hashlib
from collections import defaultdict

class SQLFingerprint:
    """SQL指纹聚类工具"""
    
    def __init__(self):
        """初始化指纹工具"""
        pass
    
    def normalize_sql(self, sql):
        """SQL标准化"""
        # 1. 转为小写
        sql = sql.lower()
        
        # 2. 移除注释
        sql = re.sub(r'/*.*?*/', '', sql, flags=re.DOTALL)
        
        # 3. 替换数值常量为?
        sql = re.sub(r'\b\d+\b', '?', sql)
        
        # 4. 替换字符串常量为?
        sql = re.sub(r"'[^']*'", '?', sql)
        sql = re.sub(r'"[^" ]*"', '?', sql)
        
        # 5. 标准化空白
        sql = re.sub(r'\s+', ' ', sql).strip()
        
        # 6. 移除分号
        if sql.endswith(';'):
            sql = sql[:-1].strip()
        
        return sql
    
    def generate_fingerprint(self, sql):
        """生成SQL指纹"""
        normalized_sql = self.normalize_sql(sql)
        fingerprint = hashlib.md5(normalized_sql.encode()).hexdigest()
        return fingerprint, normalized_sql
    
    def cluster_queries(self, queries):
        """聚类SQL查询"""
        clusters = defaultdict(lambda: {
            'fingerprint': '',
            'template': '',
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'queries': []
        })
        
        for query in queries:
            sql = query.get('sql', '')
            query_time = query.get('query_time', 0)
            
            if sql:
                fingerprint, template = self.generate_fingerprint(sql)
                cluster = clusters[fingerprint]
                cluster['fingerprint'] = fingerprint
                cluster['template'] = template
                cluster['count'] += 1
                cluster['total_time'] += query_time
                cluster['avg_time'] = cluster['total_time'] / cluster['count']
                cluster['queries'].append(query)
        
        # 转换为列表并排序
        sorted_clusters = sorted(clusters.values(), key=lambda x: x['total_time'], reverse=True)
        return sorted_clusters
    
    def analyze_clusters(self, clusters):
        """分析聚类结果，生成优化建议"""
        suggestions = []
        
        for cluster in clusters:
            if cluster['count'] > 10 and cluster['avg_time'] > 1.0:
                suggestions.append(f"SQL模板 '{cluster['template']}' 执行了 {cluster['count']} 次，平均耗时 {cluster['avg_time']:.2f} 秒，建议优化")
        
        return suggestions
    
    def extract_patterns(self, sql):
        """提取SQL模式"""
        normalized = self.normalize_sql(sql)
        
        # 提取操作类型
        operation_match = re.match(r'(select|insert|update|delete|create|alter|drop)', normalized)
        operation = operation_match.group(1) if operation_match else 'unknown'
        
        # 提取表名
        tables = []
        if operation == 'select':
            # 简单提取FROM子句中的表名
            from_match = re.search(r'from\s+([\w\s,]+)(?:\s+where|$)', normalized)
            if from_match:
                table_str = from_match.group(1)
                tables = [t.strip() for t in table_str.split(',')]
        
        return {
            'operation': operation,
            'tables': tables,
            'template': normalized
        }
