import pymysql
from cryptography.fernet import Fernet
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 获取应用的基础目录
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保日志目录存在
def ensure_log_dir():
    log_dir = os.path.join(get_base_dir(), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

# 加载环境变量
base_dir = get_base_dir()
env_path = os.path.join(base_dir, '.env')
ensure_log_dir()
load_dotenv(env_path)

# 生成或加载加密密钥
if not os.getenv('ENCRYPTION_KEY'):
    key = Fernet.generate_key()
    with open(env_path, 'a') as f:
        f.write(f'ENCRYPTION_KEY={key.decode()}\n')
    os.environ['ENCRYPTION_KEY'] = key.decode()

key = os.getenv('ENCRYPTION_KEY').encode()
cipher_suite = Fernet(key)

class DatabaseService:
    """数据库服务类，提供数据库操作功能"""
    
    def __init__(self):
        self.connections = {}
        self.lock = threading.RLock()  # 线程锁，确保线程安全
    
    def encrypt_connection_string(self, connection_string):
        """加密连接字符串"""
        try:
            return cipher_suite.encrypt(connection_string.encode()).decode()
        except Exception as e:
            logger.error(f"加密连接字符串失败: {e}\n{traceback.format_exc()}")
            raise
    
    def decrypt_connection_string(self, encrypted_string):
        """解密连接字符串"""
        try:
            return cipher_suite.decrypt(encrypted_string.encode()).decode()
        except Exception as e:
            logger.error(f"解密连接字符串失败: {e}\n{traceback.format_exc()}")
            raise
    
    def test_connection(self, host, port, user, password, database):
        """测试数据库连接"""
        try:
            logger.info(f"开始测试数据库连接: {host}:{port}/{database}")
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            conn.close()
            logger.info(f"数据库连接测试成功: {host}:{port}/{database}")
            return True, "连接成功"
        except Exception as e:
            logger.error(f"测试数据库连接失败: {host}:{port}/{database}, 错误: {e}\n{traceback.format_exc()}")
            return False, str(e)
    
    def get_connection(self, host, port, user, password, database):
        """获取数据库连接"""
        try:
            logger.debug(f"获取数据库连接: {host}:{port}/{database}")
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            return conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {host}:{port}/{database}, 错误: {e}\n{traceback.format_exc()}")
            raise
    
    def execute_query(self, conn, query, params=None):
        """执行SQL查询"""
        try:
            logger.debug(f"执行SQL查询: {query[:100]}...")
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()
                conn.commit()
                
                # 转换Decimal类型为浮点数，以支持JSON序列化
                import decimal
                for row in result:
                    for key, value in row.items():
                        if isinstance(value, decimal.Decimal):
                            row[key] = float(value)
                
                logger.debug(f"SQL查询执行成功，返回 {len(result)} 条记录")
                return True, result
        except Exception as e:
            logger.error(f"执行SQL查询失败: {query[:100]}..., 错误: {e}\n{traceback.format_exc()}")
            conn.rollback()
            return False, str(e)
    
    def close_connection(self, conn):
        """关闭数据库连接"""
        if conn:
            try:
                conn.close()
                logger.debug("数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接失败: {e}\n{traceback.format_exc()}")
    
    def table_exists(self, conn, table_name):
        """检查表格是否存在"""
        try:
            logger.debug(f"检查表格是否存在: {table_name}")
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                result = cursor.fetchone()
                exists = result is not None
                logger.debug(f"表格 {table_name} 存在: {exists}")
                return exists
        except Exception as e:
            logger.error(f"检查表格是否存在失败: {table_name}, 错误: {e}\n{traceback.format_exc()}")
            return False
    
    def truncate_table(self, conn, table_name):
        """清空表格数据"""
        try:
            logger.info(f"清空表格数据: {table_name}")
            with conn.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                conn.commit()
                logger.info(f"表格 {table_name} 数据清空成功")
                return True
        except Exception as e:
            logger.error(f"清空表格数据失败: {table_name}, 错误: {e}\n{traceback.format_exc()}")
            conn.rollback()
            return False
    
    def rename_table(self, conn, old_table_name, new_table_name):
        """重命名表格"""
        try:
            logger.info(f"重命名表格: {old_table_name} → {new_table_name}")
            with conn.cursor() as cursor:
                cursor.execute(f"RENAME TABLE `{old_table_name}` TO `{new_table_name}`")
                conn.commit()
                logger.info(f"表格重命名成功: {old_table_name} → {new_table_name}")
                return True
        except Exception as e:
            logger.error(f"重命名表格失败: {old_table_name} → {new_table_name}, 错误: {e}\n{traceback.format_exc()}")
            conn.rollback()
            return False
    
    def multi_threaded_insert(self, host, port, user, password, database, insert_sql, values, batch_size=1000, max_workers=4):
        """多线程批量插入数据
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 数据库用户
            password: 数据库密码
            database: 数据库名称
            insert_sql: 插入SQL语句
            values: 插入数据列表
            batch_size: 批处理大小
            max_workers: 最大线程数
            
        Returns:
            成功插入的记录数
        """
        try:
            logger.info(f"开始多线程插入，数据量: {len(values)}, 批处理大小: {batch_size}, 线程数: {max_workers}")
            
            # 分批处理数据
            batches = []
            for i in range(0, len(values), batch_size):
                batches.append(values[i:i+batch_size])
            
            # 定义插入函数
            def insert_batch(batch):
                # 为每个线程创建独立的数据库连接
                thread_conn = self.get_connection(host, port, user, password, database)
                try:
                    with thread_conn.cursor() as cursor:
                        cursor.executemany(insert_sql, batch)
                        thread_conn.commit()
                    logger.debug(f"批量插入成功，批次大小: {len(batch)}")
                    return len(batch)
                except Exception as e:
                    logger.error(f"批量插入失败，错误: {e}\n{traceback.format_exc()}")
                    thread_conn.rollback()
                    raise
                finally:
                    self.close_connection(thread_conn)
            
            # 使用线程池执行插入
            total_inserted = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = executor.map(insert_batch, batches)
                total_inserted = sum(results)
            
            logger.info(f"多线程插入完成，成功插入: {total_inserted} 条记录")
            return total_inserted
        except Exception as e:
            logger.error(f"多线程插入失败: {e}\n{traceback.format_exc()}")
            raise

# 全局数据库服务实例
db_service = DatabaseService()
