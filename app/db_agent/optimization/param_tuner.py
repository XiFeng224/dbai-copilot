# Parameter tuner module
"""参数调优模块"""

import psutil
from ..core import DatabaseConnection

class ParamTuner:
    """数据库参数调优工具"""
    
    def __init__(self, db_connection):
        """初始化参数调优工具"""
        self.db = db_connection
    
    def get_current_parameters(self):
        """获取当前参数配置"""
        query = "SHOW VARIABLES"
        result = self.db.fetch_all(query)
        
        params = {}
        for item in result:
            params[item['Variable_name']] = item['Value']
        
        return params
    
    def recommend_parameters(self):
        """推荐参数配置"""
        recommendations = []
        current_params = self.get_current_parameters()
        
        # 1. 内存相关参数
        memory = psutil.virtual_memory()
        total_memory = memory.total / (1024 * 1024 * 1024)  # GB
        
        # innodb_buffer_pool_size
        innodb_buffer_pool_size = current_params.get('innodb_buffer_pool_size', '0')
        recommended_pool_size = int(total_memory * 0.7)  # 建议设置为内存的70%
        
        recommendations.append({
            'parameter': 'innodb_buffer_pool_size',
            'current': innodb_buffer_pool_size,
            'recommended': f'{recommended_pool_size}G',
            'reason': '建议设置为服务器内存的70%，提高InnoDB缓存效率'
        })
        
        # 2. 连接相关参数
        max_connections = current_params.get('max_connections', '151')
        recommended_connections = min(int(total_memory * 100), 1000)  # 根据内存计算
        
        recommendations.append({
            'parameter': 'max_connections',
            'current': max_connections,
            'recommended': str(recommended_connections),
            'reason': '根据服务器内存调整最大连接数，避免内存不足'
        })
        
        # 3. 查询缓存参数（MySQL 5.7+ 已废弃）
        if 'query_cache_type' in current_params:
            recommendations.append({
                'parameter': 'query_cache_type',
                'current': current_params['query_cache_type'],
                'recommended': '0',
                'reason': '查询缓存在高并发场景下可能导致性能下降，建议禁用'
            })
        
        # 4. InnoDB相关参数
        innodb_log_file_size = current_params.get('innodb_log_file_size', '48M')
        recommended_log_size = '1G'
        
        recommendations.append({
            'parameter': 'innodb_log_file_size',
            'current': innodb_log_file_size,
            'recommended': recommended_log_size,
            'reason': '增大InnoDB日志文件大小，提高写入性能'
        })
        
        # 5. 临时表参数
        tmp_table_size = current_params.get('tmp_table_size', '16M')
        max_heap_table_size = current_params.get('max_heap_table_size', '16M')
        recommended_tmp_size = '64M'
        
        recommendations.append({
            'parameter': 'tmp_table_size',
            'current': tmp_table_size,
            'recommended': recommended_tmp_size,
            'reason': '增大临时表大小，减少磁盘临时表的使用'
        })
        
        recommendations.append({
            'parameter': 'max_heap_table_size',
            'current': max_heap_table_size,
            'recommended': recommended_tmp_size,
            'reason': '与tmp_table_size保持一致，避免内存临时表转换为磁盘临时表'
        })
        
        # 6. 网络相关参数
        net_read_timeout = current_params.get('net_read_timeout', '30')
        net_write_timeout = current_params.get('net_write_timeout', '60')
        
        recommendations.append({
            'parameter': 'net_read_timeout',
            'current': net_read_timeout,
            'recommended': '60',
            'reason': '适当增加网络读取超时时间，避免网络不稳定时的连接断开'
        })
        
        recommendations.append({
            'parameter': 'net_write_timeout',
            'current': net_write_timeout,
            'recommended': '120',
            'reason': '适当增加网络写入超时时间，避免大查询时的连接断开'
        })
        
        return recommendations
    
    def analyze_parameter_performance(self):
        """分析参数性能影响"""
        # 分析缓冲池使用情况
        query = "SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_%'"
        buffer_pool_stats = self.db.fetch_all(query)
        
        # 分析连接情况
        query = "SHOW GLOBAL STATUS LIKE 'Threads_%'"
        thread_stats = self.db.fetch_all(query)
        
        # 分析查询性能
        query = "SHOW GLOBAL STATUS LIKE 'Qcache_%'"
        query_cache_stats = self.db.fetch_all(query)
        
        return {
            'buffer_pool_stats': buffer_pool_stats,
            'thread_stats': thread_stats,
            'query_cache_stats': query_cache_stats
        }
