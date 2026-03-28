# Explain visualizer module
"""执行计划可视化模块"""

import json
import logging
from ..core import DatabaseConnection

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExplainVisualizer:
    """SQL执行计划可视化工具"""
    
    def __init__(self, db_connection):
        """初始化可视化工具"""
        self.db = db_connection
    
    def visualize_explain(self, sql):
        """可视化执行计划"""
        try:
            # 获取JSON格式的执行计划
            explain_sql = f"EXPLAIN FORMAT=JSON {sql}"
            result = self.db.fetch_all(explain_sql)
            
            if not result:
                return {'nodes': [], 'edges': []}
            
            plan_json = result[0]['EXPLAIN']
            plan = json.loads(plan_json)
            
            # 解析执行计划
            nodes = []
            edges = []
            
            def parse_node(node, parent_id=None):
                """递归解析执行计划节点"""
                node_id = len(nodes)
                
                # 提取节点信息
                table = node.get('table', 'operation')
                access_type = node.get('access_type', 'unknown')
                rows = node.get('rows', 0)
                filtered = node.get('filtered', 100)
                cost = node.get('cost_info', {}).get('total_cost', 0)
                key = node.get('key', '无')
                key_len = node.get('key_len', 0)
                ref = node.get('ref', '无')
                
                # 识别问题
                is_bad = access_type in ['ALL', 'index']
                issues = []
                if access_type == 'ALL':
                    issues.append('全表扫描')
                if node.get('using_filesort', False):
                    issues.append('文件排序')
                if node.get('using_temporary', False):
                    issues.append('临时表')
                if node.get('using_index', False):
                    issues.append('使用索引')
                if node.get('using_where', False):
                    issues.append('使用WHERE过滤')
                if node.get('using_join_buffer', False):
                    issues.append('使用连接缓冲区')
                
                # 计算节点重要性
                importance = 1.0
                if access_type == 'ALL':
                    importance = 5.0
                elif access_type == 'index':
                    importance = 3.0
                elif access_type == 'range':
                    importance = 2.0
                
                # 创建节点
                nodes.append({
                    'id': node_id,
                    'name': table,
                    'type': access_type,
                    'rows': rows,
                    'filtered': filtered,
                    'cost': cost,
                    'key': key,
                    'key_len': key_len,
                    'ref': ref,
                    'is_bad': is_bad,
                    'issues': issues,
                    'extra': node.get('extra', ''),
                    'importance': importance
                })
                
                # 创建边
                if parent_id is not None:
                    edges.append({
                        'source': parent_id,
                        'target': node_id
                    })
                
                # 处理子节点
                if 'children' in node:
                    for child in node['children']:
                        parse_node(child, node_id)
            
            # 开始解析
            parse_node(plan['query_block'])
            
            return {'nodes': nodes, 'edges': edges}
        except Exception as e:
            logger.error(f"可视化执行计划时出错: {e}")
            return {'nodes': [], 'edges': []}
    
    def get_execution_plan_text(self, sql):
        """获取文本格式的执行计划"""
        try:
            explain_sql = f"EXPLAIN {sql}"
            result = self.db.fetch_all(explain_sql)
            return result
        except Exception as e:
            logger.error(f"获取执行计划时出错: {e}")
            return []
    
    def analyze_plan(self, plan_data):
        """分析执行计划，生成优化建议"""
        try:
            suggestions = []
            tables_scanned = set()
            
            # 分析每个节点
            for node in plan_data['nodes']:
                table = node['name']
                tables_scanned.add(table)
                
                if node['is_bad']:
                    if node['type'] == 'ALL':
                        suggestions.append(f"表 {table} 执行了全表扫描，建议添加合适的索引")
                    elif node['type'] == 'index':
                        suggestions.append(f"表 {table} 执行了索引扫描，可能需要优化索引")
                
                if '文件排序' in node['issues']:
                    suggestions.append(f"查询使用了文件排序，建议优化 ORDER BY 子句或添加合适的索引")
                
                if '临时表' in node['issues']:
                    suggestions.append(f"查询使用了临时表，建议优化 GROUP BY 或 DISTINCT 子句")
                
                if '使用连接缓冲区' in node['issues']:
                    suggestions.append(f"查询使用了连接缓冲区，可能需要优化连接条件或添加索引")
            
            # 分析整体执行计划
            total_cost = sum(node['cost'] for node in plan_data['nodes'])
            if total_cost > 1000:
                suggestions.append(f"查询总代价较高 ({total_cost:.2f})，建议优化查询结构")
            
            # 分析表扫描情况
            if len(tables_scanned) > 3:
                suggestions.append(f"查询涉及 {len(tables_scanned)} 个表，可能需要考虑拆分查询")
            
            # 去重建议
            return list(set(suggestions))
        except Exception as e:
            logger.error(f"分析执行计划时出错: {e}")
            return []
    
    def get_index_suggestions(self, sql):
        """根据SQL语句和执行计划，推荐索引"""
        try:
            # 首先获取执行计划
            plan_data = self.visualize_explain(sql)
            
            # 分析执行计划，提取可能需要索引的列
            index_candidates = {}
            
            for node in plan_data['nodes']:
                if node['is_bad'] or '文件排序' in node['issues'] or '临时表' in node['issues']:
                    table = node['name']
                    if table not in index_candidates:
                        index_candidates[table] = set()
                    
                    # 提取WHERE条件中的列
                    # 这里简化处理，实际应该解析SQL语句
                    # 这里只是示例，实际实现需要更复杂的SQL解析
                    index_candidates[table].add('id')
            
            # 生成索引建议
            suggestions = []
            for table, columns in index_candidates.items():
                if columns:
                    columns_str = ', '.join(columns)
                    suggestions.append(f"建议在表 {table} 上创建索引: ({columns_str})")
            
            return suggestions
        except Exception as e:
            logger.error(f"获取索引建议时出错: {e}")
            return []
    
    def compare_plans(self, sql1, sql2):
        """比较两个SQL语句的执行计划"""
        try:
            plan1 = self.visualize_explain(sql1)
            plan2 = self.visualize_explain(sql2)
            
            # 计算两个计划的总代价
            cost1 = sum(node['cost'] for node in plan1['nodes'])
            cost2 = sum(node['cost'] for node in plan2['nodes'])
            
            # 分析改进
            improvements = []
            if cost2 < cost1:
                improvements.append(f"SQL2的执行代价更低 ({cost2:.2f} vs {cost1:.2f})")
            else:
                improvements.append(f"SQL1的执行代价更低 ({cost1:.2f} vs {cost2:.2f})")
            
            # 分析扫描类型
            scan_types1 = [node['type'] for node in plan1['nodes']]
            scan_types2 = [node['type'] for node in plan2['nodes']]
            
            full_scan1 = scan_types1.count('ALL')
            full_scan2 = scan_types2.count('ALL')
            
            if full_scan2 < full_scan1:
                improvements.append(f"SQL2减少了全表扫描 ({full_scan2} vs {full_scan1})")
            
            # 分析文件排序和临时表
            issues1 = []
            for node in plan1['nodes']:
                issues1.extend(node['issues'])
            
            issues2 = []
            for node in plan2['nodes']:
                issues2.extend(node['issues'])
            
            filesort1 = issues1.count('文件排序')
            filesort2 = issues2.count('文件排序')
            
            if filesort2 < filesort1:
                improvements.append(f"SQL2减少了文件排序 ({filesort2} vs {filesort1})")
            
            temptable1 = issues1.count('临时表')
            temptable2 = issues2.count('临时表')
            
            if temptable2 < temptable1:
                improvements.append(f"SQL2减少了临时表使用 ({temptable2} vs {temptable1})")
            
            return {
                'cost1': cost1,
                'cost2': cost2,
                'improvements': improvements
            }
        except Exception as e:
            logger.error(f"比较执行计划时出错: {e}")
            return {'cost1': 0, 'cost2': 0, 'improvements': []}

