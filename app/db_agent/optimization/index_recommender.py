# Index recommender module
"""索引推荐模块"""

import re
from ..core import DatabaseConnection

class IndexRecommender:
    """索引推荐引擎"""
    
    def __init__(self, db_connection):
        """初始化索引推荐引擎"""
        self.db = db_connection
    
    def recommend_indexes(self, sql):
        """推荐索引"""
        # 解析SQL
        parsed = self._parse_sql(sql)
        if not parsed:
            return []
        
        recommendations = []
        
        # 分析WHERE子句
        if parsed.get('where'):
            where_columns = self._extract_where_columns(parsed['where'])
            for table, columns in where_columns.items():
                if columns:
                    # 推荐联合索引
                    if len(columns) > 1:
                        index_name = f"idx_{table}_{'_'.join(columns)}"
                        recommendations.append({
                            'type': 'index',
                            'table': table,
                            'columns': columns,
                            'index_name': index_name,
                            'reason': f"WHERE子句中使用了多个列: {', '.join(columns)}"
                        })
                    # 推荐单列索引
                    for column in columns:
                        index_name = f"idx_{table}_{column}"
                        recommendations.append({
                            'type': 'index',
                            'table': table,
                            'columns': [column],
                            'index_name': index_name,
                            'reason': f"WHERE子句中使用了列: {column}"
                        })
        
        # 分析ORDER BY子句
        if parsed.get('order_by'):
            order_columns = self._extract_order_columns(parsed['order_by'])
            for table, columns in order_columns.items():
                if columns:
                    index_name = f"idx_{table}_order_{'_'.join(columns)}"
                    recommendations.append({
                        'type': 'index',
                        'table': table,
                        'columns': columns,
                        'index_name': index_name,
                        'reason': f"ORDER BY子句中使用了列: {', '.join(columns)}"
                    })
        
        # 分析JOIN子句
        if parsed.get('join'):
            join_columns = self._extract_join_columns(parsed['join'])
            for table, columns in join_columns.items():
                if columns:
                    for column in columns:
                        index_name = f"idx_{table}_{column}"
                        recommendations.append({
                            'type': 'index',
                            'table': table,
                            'columns': [column],
                            'index_name': index_name,
                            'reason': f"JOIN子句中使用了列: {column}"
                        })
        
        return recommendations
    
    def _parse_sql(self, sql):
        """解析SQL语句"""
        sql = sql.lower()
        parsed = {}
        
        # 提取FROM子句中的表名
        from_match = re.search(r'from\s+([\w\s,]+)(?:\s+(where|join|order|group|limit))?', sql)
        if from_match:
            table_str = from_match.group(1)
            tables = [t.strip().split()[0] for t in table_str.split(',')]
            parsed['tables'] = tables
        
        # 提取WHERE子句
        where_match = re.search(r'where\s+(.+?)(?:\s+(join|order|group|limit))?', sql)
        if where_match:
            parsed['where'] = where_match.group(1)
        
        # 提取ORDER BY子句
        order_match = re.search(r'order\s+by\s+(.+?)(?:\s+(limit|group))?', sql)
        if order_match:
            parsed['order_by'] = order_match.group(1)
        
        # 提取JOIN子句
        join_match = re.findall(r'(inner|left|right|outer)?\s*join\s+([\w]+)\s+on\s+(.+?)(?:\s+(join|where|order|group|limit))?', sql)
        if join_match:
            parsed['join'] = join_match
        
        return parsed
    
    def _extract_where_columns(self, where_clause):
        """提取WHERE子句中的列"""
        columns = {}
        # 简单提取列名
        matches = re.findall(r'(\w+)\s*[=<>!]', where_clause)
        for match in matches:
            # 假设列名格式为 table.column 或 column
            parts = match.split('.')
            if len(parts) == 2:
                table = parts[0]
                column = parts[1]
            else:
                table = 'unknown'
                column = parts[0]
            
            if table not in columns:
                columns[table] = []
            if column not in columns[table]:
                columns[table].append(column)
        
        return columns
    
    def _extract_order_columns(self, order_clause):
        """提取ORDER BY子句中的列"""
        columns = {}
        # 简单提取列名
        matches = re.findall(r'(\w+)(?:\s+(asc|desc))?', order_clause)
        for match in matches:
            column = match[0]
            # 假设列名格式为 table.column 或 column
            parts = column.split('.')
            if len(parts) == 2:
                table = parts[0]
                column = parts[1]
            else:
                table = 'unknown'
                column = parts[0]
            
            if table not in columns:
                columns[table] = []
            if column not in columns[table]:
                columns[table].append(column)
        
        return columns
    
    def _extract_join_columns(self, join_clauses):
        """提取JOIN子句中的列"""
        columns = {}
        for join in join_clauses:
            table = join[1]
            on_clause = join[2]
            # 提取ON子句中的列
            matches = re.findall(r'(\w+\.\w+)\s*=\s*(\w+\.\w+)', on_clause)
            for match in matches:
                # 提取右侧表的列
                right_col = match[1]
                parts = right_col.split('.')
                if len(parts) == 2:
                    join_table = parts[0]
                    column = parts[1]
                    if join_table == table:
                        if table not in columns:
                            columns[table] = []
                        if column not in columns[table]:
                            columns[table].append(column)
        
        return columns
    
    def analyze_table_indexes(self, table_name):
        """分析表的现有索引"""
        query = """
        SHOW INDEX FROM {}
        """.format(table_name)
        
        result = self.db.fetch_all(query)
        indexes = {}
        
        for item in result:
            index_name = item['Key_name']
            if index_name not in indexes:
                indexes[index_name] = {
                    'columns': [],
                    'non_unique': item['Non_unique'],
                    'index_type': item['Index_type']
                }
            indexes[index_name]['columns'].append(item['Column_name'])
        
        return indexes
