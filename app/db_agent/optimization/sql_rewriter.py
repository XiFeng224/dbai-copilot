# SQL rewriter module
"""SQL改写模块"""

import re
from ..core import DatabaseConnection

class SQLRewriter:
    """SQL改写引擎"""
    
    def __init__(self, db_connection):
        """初始化SQL改写引擎"""
        self.db = db_connection
    
    def rewrite_sql(self, sql):
        """改写SQL语句"""
        suggestions = []
        rewritten_sql = sql
        
        # 1. 优化SELECT *
        if 'SELECT *' in rewritten_sql:
            table_name = self._extract_table_name(rewritten_sql)
            if table_name:
                columns = self._get_table_columns(table_name)
                if columns:
                    column_list = ', '.join(columns)
                    rewritten_sql = rewritten_sql.replace('SELECT *', f'SELECT {column_list}')
                    suggestions.append({
                        'type': 'select_star',
                        'original': 'SELECT *',
                        'suggested': f'SELECT {column_list}',
                        'reason': '避免选择不必要的列，减少数据传输和处理开销'
                    })
        
        # 2. 优化子查询
        if 'SELECT' in rewritten_sql and 'FROM (' in rewritten_sql:
            # 简单检测子查询
            suggestions.append({
                'type': 'subquery',
                'original': '子查询',
                'suggested': '考虑使用JOIN替代子查询',
                'reason': '子查询可能导致性能问题，JOIN通常更高效'
            })
        
        # 3. 优化LIMIT语句
        if 'LIMIT' not in rewritten_sql and 'SELECT' in rewritten_sql:
            suggestions.append({
                'type': 'limit',
                'original': '无LIMIT语句',
                'suggested': '添加LIMIT语句',
                'reason': '限制结果集大小，提高查询性能'
            })
        
        # 4. 优化WHERE子句
        where_clause = self._extract_where_clause(rewritten_sql)
        if where_clause:
            # 检测函数在WHERE子句中的使用
            if re.search(r'\w+\s*\([^\)]*\)', where_clause):
                suggestions.append({
                    'type': 'where_function',
                    'original': 'WHERE子句中使用函数',
                    'suggested': '避免在WHERE子句中使用函数',
                    'reason': '函数会导致索引失效，降低查询性能'
                })
        
        # 5. 优化ORDER BY
        order_clause = self._extract_order_clause(rewritten_sql)
        if order_clause:
            # 检测ORDER BY与LIMIT的组合
            if 'LIMIT' in rewritten_sql:
                suggestions.append({
                    'type': 'order_limit',
                    'original': 'ORDER BY与LIMIT组合',
                    'suggested': '确保ORDER BY列有索引',
                    'reason': 'ORDER BY与LIMIT组合时，合适的索引可以显著提高性能'
                })
        
        return {
            'original_sql': sql,
            'rewritten_sql': rewritten_sql,
            'suggestions': suggestions
        }
    
    def _extract_table_name(self, sql):
        """提取表名"""
        match = re.search(r'FROM\s+([\w]+)(?:\s|$)', sql, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _get_table_columns(self, table_name):
        """获取表的列名"""
        query = f"SHOW COLUMNS FROM {table_name}"
        result = self.db.fetch_all(query)
        if result:
            return [item['Field'] for item in result]
        return []
    
    def _extract_where_clause(self, sql):
        """提取WHERE子句"""
        match = re.search(r'WHERE\s+(.+?)(?:\s+(ORDER|GROUP|LIMIT))?', sql, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        return None
    
    def _extract_order_clause(self, sql):
        """提取ORDER BY子句"""
        match = re.search(r'ORDER\s+BY\s+(.+?)(?:\s+LIMIT)?', sql, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        return None
    
    def analyze_sql_performance(self, sql):
        """分析SQL性能"""
        # 执行EXPLAIN分析
        explain_sql = f"EXPLAIN {sql}"
        result = self.db.fetch_all(explain_sql)
        
        performance_issues = []
        
        for row in result:
            if row.get('type') == 'ALL':
                performance_issues.append('全表扫描')
            if row.get('Extra') and 'Using filesort' in row['Extra']:
                performance_issues.append('文件排序')
            if row.get('Extra') and 'Using temporary' in row['Extra']:
                performance_issues.append('临时表')
            if row.get('key') is None:
                performance_issues.append('未使用索引')
        
        return performance_issues
