import pymysql
from cryptography.fernet import Fernet
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# 获取应用的基础目录
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
base_dir = get_base_dir()
env_path = os.path.join(base_dir, '.env')
load_dotenv(env_path)

# 生成或加载加密密钥
if not os.getenv('ENCRYPTION_KEY'):
    key = Fernet.generate_key()
    with open(env_path, 'a') as f:
        f.write(f'ENCRYPTION_KEY={key.decode()}\n')
    os.environ['ENCRYPTION_KEY'] = key.decode()

key = os.getenv('ENCRYPTION_KEY').encode()
cipher_suite = Fernet(key)

class DatabaseManager:
    def __init__(self):
        self.connections = {}
    
    def encrypt_connection_string(self, connection_string):
        """加密连接字符串"""
        return cipher_suite.encrypt(connection_string.encode()).decode()
    
    def decrypt_connection_string(self, encrypted_string):
        """解密连接字符串"""
        return cipher_suite.decrypt(encrypted_string.encode()).decode()
    
    def test_connection(self, host, port, user, password, database):
        """测试数据库连接"""
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            conn.close()
            return True, "连接成功"
        except Exception as e:
            return False, str(e)
    
    def get_connection(self, host, port, user, password, database):
        """获取数据库连接"""
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    
    def execute_query(self, conn, query, params=None):
        """执行SQL查询"""
        try:
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
                
                return True, result
        except Exception as e:
            conn.rollback()
            return False, str(e)
    
    def close_connection(self, conn):
        """关闭数据库连接"""
        if conn:
            conn.close()
    
    def table_exists(self, conn, table_name):
        """检查表格是否存在"""
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            return False
    
    def truncate_table(self, conn, table_name):
        """清空表格数据"""
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            return False
    
    def rename_table(self, conn, old_table_name, new_table_name):
        """重命名表格"""
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"RENAME TABLE `{old_table_name}` TO `{new_table_name}`")
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            return False
    
    def multi_threaded_insert(self, *args, **kwargs):
        """多线程批量插入数据
        支持两种调用方式：
        1. multi_threaded_insert(conn, insert_sql, values, batch_size=1000, max_workers=4)
        2. multi_threaded_insert(host, port, user, password, database, insert_sql, values, batch_size=1000, max_workers=4)
        """
        try:
            # 解析参数
            if len(args) >= 3:
                if hasattr(args[0], 'cursor'):  # 第一种调用方式：conn, insert_sql, values
                    conn = args[0]
                    insert_sql = args[1]
                    values = args[2]
                    batch_size = args[3] if len(args) > 3 else 1000
                    max_workers = args[4] if len(args) > 4 else 4
                    
                    # 从连接中提取连接信息（这种方式可能不可靠，建议使用第二种调用方式）
                    host = conn.host
                    port = conn.port
                    user = conn.user
                    password = conn.password
                    database = conn.db
                else:  # 第二种调用方式：host, port, user, password, database, insert_sql, values
                    host = args[0]
                    port = args[1]
                    user = args[2]
                    password = args[3]
                    database = args[4]
                    insert_sql = args[5]
                    values = args[6]
                    batch_size = args[7] if len(args) > 7 else 1000
                    max_workers = args[8] if len(args) > 8 else 4
            else:
                raise ValueError("参数不足")
            
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
                    return len(batch)
                except Exception as e:
                    thread_conn.rollback()
                    raise e
                finally:
                    self.close_connection(thread_conn)
            
            # 使用线程池执行插入
            total_inserted = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = executor.map(insert_batch, batches)
                total_inserted = sum(results)
            
            return total_inserted
        except Exception as e:
            raise e

# 全局数据库管理器实例
db_manager = DatabaseManager()