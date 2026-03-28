# Metrics collector module
"""性能指标采集模块"""

import time
import psutil
import subprocess
import platform
import logging
from collections import deque
from ..core import DatabaseConnection

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetricsCollector:
    """数据库性能指标采集器"""
    
    def __init__(self, db_connection):
        """初始化采集器"""
        self.db = db_connection
        self.previous_status = {}
        self.previous_time = time.time()
        self.metrics_history = deque(maxlen=60)  # 保存最近60个指标数据点
        self.anomaly_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 90.0,
            'qps': 1000.0,
            'slow_queries': 10
        }
    
    def collect(self):
        """采集性能指标"""
        try:
            metrics = {}
            
            # 采集数据库状态
            status = self._collect_status()
            if status:
                metrics.update(self._calculate_metrics(status))
            
            # 采集系统指标
            metrics.update(self._collect_system_metrics())
            
            # 采集连接数
            metrics['connections'] = self._collect_connections()
            
            # 采集慢查询数
            metrics['slow_queries'] = self._collect_slow_queries()
            
            # 采集InnoDB指标
            metrics.update(self._collect_innodb_metrics())
            
            # 采集临时表使用情况
            metrics.update(self._collect_temp_table_metrics())
            
            # 采集复制状态（如果有）
            metrics['replication'] = self._collect_replication_status()
            
            # 记录采集时间
            metrics['timestamp'] = time.time()
            
            # 保存到历史记录
            self.metrics_history.append(metrics)
            
            # 检测异常
            metrics['anomalies'] = self._detect_anomalies(metrics)
            
            return metrics
        except Exception as e:
            logger.error(f"采集指标时出错: {e}")
            return {}
    
    def _collect_status(self):
        """采集数据库状态"""
        try:
            query = "SHOW GLOBAL STATUS"
            result = self.db.fetch_all(query)
            if result:
                return {item['Variable_name']: item['Value'] for item in result}
            return {}
        except Exception as e:
            logger.error(f"采集数据库状态时出错: {e}")
            return {}
    
    def _calculate_metrics(self, status):
        """计算性能指标"""
        metrics = {}
        current_time = time.time()
        time_diff = current_time - self.previous_time
        
        # 计算QPS
        if 'Questions' in status and 'Uptime' in status:
            questions = int(status['Questions'])
            uptime = int(status['Uptime'])
            if uptime > 0:
                metrics['qps'] = questions / uptime
        
        # 计算TPS
        if 'Com_commit' in status and 'Com_rollback' in status:
            commit = int(status['Com_commit'])
            rollback = int(status['Com_rollback'])
            if time_diff > 0:
                if 'Com_commit' in self.previous_status and 'Com_rollback' in self.previous_status:
                    tps = (commit - self.previous_status['Com_commit'] + rollback - self.previous_status['Com_rollback']) / time_diff
                    metrics['tps'] = tps
        
        # 计算InnoDB缓冲池命中率
        if 'Innodb_buffer_pool_read_requests' in status and 'Innodb_buffer_pool_reads' in status:
            hits = int(status['Innodb_buffer_pool_read_requests'])
            reads = int(status['Innodb_buffer_pool_reads'])
            if hits > 0:
                hit_rate = (hits - reads) / hits * 100
                metrics['innodb_buffer_pool_hit_rate'] = hit_rate
        
        # 计算查询缓存命中率
        if 'Qcache_hits' in status and 'Qcache_inserts' in status:
            hits = int(status['Qcache_hits'])
            inserts = int(status['Qcache_inserts'])
            total = hits + inserts
            if total > 0:
                hit_rate = hits / total * 100
                metrics['query_cache_hit_rate'] = hit_rate
        
        # 更新历史状态
        self.previous_status = status
        self.previous_time = current_time
        
        return metrics
    
    def _collect_system_metrics(self):
        """采集系统指标"""
        metrics = {}
        
        # CPU使用率
        metrics['cpu_usage'] = psutil.cpu_percent(interval=0.1)
        
        # 内存使用
        memory = psutil.virtual_memory()
        metrics['memory_usage'] = memory.percent
        metrics['memory_used_mb'] = memory.used / 1024 / 1024
        metrics['memory_total_mb'] = memory.total / 1024 / 1024
        
        # 磁盘使用
        disk = psutil.disk_usage('/')
        metrics['disk_usage'] = disk.percent
        metrics['disk_used_gb'] = disk.used / 1024 / 1024 / 1024
        metrics['disk_total_gb'] = disk.total / 1024 / 1024 / 1024
        
        # 磁盘IO
        if platform.system() == 'Windows':
            # Windows系统使用wmic命令
            try:
                output = subprocess.check_output(['wmic', 'diskdrive', 'get', 'Name,Size,FreeSpace'], universal_newlines=True)
                metrics['disk_info'] = output
            except Exception as e:
                logger.warning(f"采集磁盘信息时出错: {e}")
        else:
            # Linux系统使用iostat
            try:
                output = subprocess.check_output(['iostat', '-x', '1', '1'], universal_newlines=True)
                metrics['disk_io'] = output
            except Exception as e:
                logger.warning(f"采集磁盘IO时出错: {e}")
        
        # 网络流量
        try:
            net_io = psutil.net_io_counters()
            metrics['network_sent_mb'] = net_io.bytes_sent / 1024 / 1024
            metrics['network_recv_mb'] = net_io.bytes_recv / 1024 / 1024
        except Exception as e:
            logger.warning(f"采集网络流量时出错: {e}")
        
        return metrics
    
    def _collect_connections(self):
        """采集连接数"""
        try:
            # 当前连接数
            query = "SHOW GLOBAL STATUS LIKE 'Threads_connected'"
            current = self.db.fetch_all(query)
            
            # 最大连接数
            query = "SHOW VARIABLES LIKE 'max_connections'"
            max_conn = self.db.fetch_all(query)
            
            # 活跃连接数
            query = "SHOW GLOBAL STATUS LIKE 'Threads_running'"
            running = self.db.fetch_all(query)
            
            return {
                'current': int(current[0]['Value']) if current else 0,
                'max': int(max_conn[0]['Value']) if max_conn else 151,
                'running': int(running[0]['Value']) if running else 0
            }
        except Exception as e:
            logger.error(f"采集连接数时出错: {e}")
            return {'current': 0, 'max': 151, 'running': 0}
    
    def _collect_slow_queries(self):
        """采集慢查询数"""
        try:
            query = "SHOW GLOBAL STATUS LIKE 'Slow_queries'"
            result = self.db.fetch_all(query)
            if result:
                return int(result[0]['Value'])
            return 0
        except Exception as e:
            logger.error(f"采集慢查询数时出错: {e}")
            return 0
    
    def _collect_innodb_metrics(self):
        """采集InnoDB指标"""
        metrics = {}
        try:
            # InnoDB缓冲池使用情况
            query = "SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_pages_%'"
            result = self.db.fetch_all(query)
            if result:
                pool_stats = {item['Variable_name']: int(item['Value']) for item in result}
                total_pages = pool_stats.get('Innodb_buffer_pool_pages_total', 0)
                free_pages = pool_stats.get('Innodb_buffer_pool_pages_free', 0)
                if total_pages > 0:
                    metrics['innodb_buffer_pool_usage'] = (total_pages - free_pages) / total_pages * 100
            
            # InnoDB行操作
            query = "SHOW GLOBAL STATUS LIKE 'Innodb_rows_%'"
            result = self.db.fetch_all(query)
            if result:
                row_stats = {item['Variable_name']: int(item['Value']) for item in result}
                metrics['innodb_rows_read'] = row_stats.get('Innodb_rows_read', 0)
                metrics['innodb_rows_inserted'] = row_stats.get('Innodb_rows_inserted', 0)
                metrics['innodb_rows_updated'] = row_stats.get('Innodb_rows_updated', 0)
                metrics['innodb_rows_deleted'] = row_stats.get('Innodb_rows_deleted', 0)
        except Exception as e:
            logger.error(f"采集InnoDB指标时出错: {e}")
        return metrics
    
    def _collect_temp_table_metrics(self):
        """采集临时表使用情况"""
        metrics = {}
        try:
            query = "SHOW GLOBAL STATUS LIKE 'Created_tmp_%'"
            result = self.db.fetch_all(query)
            if result:
                temp_stats = {item['Variable_name']: int(item['Value']) for item in result}
                metrics['created_tmp_tables'] = temp_stats.get('Created_tmp_tables', 0)
                metrics['created_tmp_disk_tables'] = temp_stats.get('Created_tmp_disk_tables', 0)
                # 计算临时表磁盘使用率
                total = temp_stats.get('Created_tmp_tables', 1)
                disk = temp_stats.get('Created_tmp_disk_tables', 0)
                metrics['tmp_disk_table_ratio'] = disk / total * 100
        except Exception as e:
            logger.error(f"采集临时表指标时出错: {e}")
        return metrics
    
    def _collect_replication_status(self):
        """采集复制状态"""
        try:
            query = "SHOW SLAVE STATUS"
            result = self.db.fetch_all(query)
            if result:
                slave_status = result[0]
                return {
                    'io_running': slave_status.get('Slave_IO_Running', 'No'),
                    'sql_running': slave_status.get('Slave_SQL_Running', 'No'),
                    'seconds_behind_master': int(slave_status.get('Seconds_Behind_Master', 0))
                }
            return {'io_running': 'N/A', 'sql_running': 'N/A', 'seconds_behind_master': 0}
        except Exception as e:
            logger.error(f"采集复制状态时出错: {e}")
            return {'io_running': 'Error', 'sql_running': 'Error', 'seconds_behind_master': 0}
    
    def _detect_anomalies(self, metrics):
        """检测异常"""
        anomalies = []
        
        # 检查CPU使用率
        if metrics.get('cpu_usage', 0) > self.anomaly_thresholds['cpu_usage']:
            anomalies.append({
                'metric': 'cpu_usage',
                'value': metrics['cpu_usage'],
                'threshold': self.anomaly_thresholds['cpu_usage'],
                'message': f'CPU使用率过高: {metrics["cpu_usage"]:.2f}%'
            })
        
        # 检查内存使用率
        if metrics.get('memory_usage', 0) > self.anomaly_thresholds['memory_usage']:
            anomalies.append({
                'metric': 'memory_usage',
                'value': metrics['memory_usage'],
                'threshold': self.anomaly_thresholds['memory_usage'],
                'message': f'内存使用率过高: {metrics["memory_usage"]:.2f}%'
            })
        
        # 检查QPS
        if metrics.get('qps', 0) > self.anomaly_thresholds['qps']:
            anomalies.append({
                'metric': 'qps',
                'value': metrics['qps'],
                'threshold': self.anomaly_thresholds['qps'],
                'message': f'QPS过高: {metrics["qps"]:.2f}'
            })
        
        # 检查慢查询数
        if metrics.get('slow_queries', 0) > self.anomaly_thresholds['slow_queries']:
            anomalies.append({
                'metric': 'slow_queries',
                'value': metrics['slow_queries'],
                'threshold': self.anomaly_thresholds['slow_queries'],
                'message': f'慢查询数过多: {metrics["slow_queries"]}'
            })
        
        # 检查连接数
        connections = metrics.get('connections', {})
        current = connections.get('current', 0)
        max_conn = connections.get('max', 151)
        if current > max_conn * 0.8:
            anomalies.append({
                'metric': 'connections',
                'value': current,
                'threshold': max_conn * 0.8,
                'message': f'连接数接近上限: {current}/{max_conn}'
            })
        
        # 检查复制延迟
        replication = metrics.get('replication', {})
        if replication.get('seconds_behind_master', 0) > 30:
            anomalies.append({
                'metric': 'replication_delay',
                'value': replication['seconds_behind_master'],
                'threshold': 30,
                'message': f'复制延迟过大: {replication["seconds_behind_master"]}秒'
            })
        
        return anomalies
    
    def get_history(self):
        """获取历史指标数据"""
        return list(self.metrics_history)
    
    def get_metric_trend(self, metric_name, window=30):
        """获取指定指标的趋势"""
        trend = []
        for metrics in list(self.metrics_history)[-window:]:
            if metric_name in metrics:
                trend.append({
                    'timestamp': metrics.get('timestamp', 0),
                    'value': metrics[metric_name]
                })
        return trend
    
    def set_anomaly_thresholds(self, thresholds):
        """设置异常检测阈值"""
        self.anomaly_thresholds.update(thresholds)
        return "异常检测阈值已更新"

