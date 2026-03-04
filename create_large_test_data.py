#!/usr/bin/env python3
"""
创建大量测试数据，用于测试多线程数据迁移功能
"""

import pymysql
import time
import random
import string

# 数据库连接信息
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '@W203222w',
    'database': 'NJYY'
}

# 测试表名
TEST_TABLE = 'large_test_data'

# 生成随机字符串
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# 创建测试表
def create_test_table():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 删除已存在的表
            cursor.execute(f"DROP TABLE IF EXISTS `{TEST_TABLE}`")
            # 创建新表
            create_table_sql = f"""
            CREATE TABLE `{TEST_TABLE}` (
                `id` INT PRIMARY KEY AUTO_INCREMENT,
                `name` VARCHAR(100),
                `email` VARCHAR(100),
                `phone` VARCHAR(20),
                `address` VARCHAR(255),
                `salary` DECIMAL(10, 2),
                `department` VARCHAR(50),
                `hire_date` DATE,
                `is_active` BOOLEAN,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
            """
            cursor.execute(create_table_sql)
            conn.commit()
            print(f"测试表 {TEST_TABLE} 创建成功")
    finally:
        conn.close()

# 批量插入测试数据
def insert_test_data(batch_size=1000, total_records=100000):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            start_time = time.time()
            records_inserted = 0
            
            while records_inserted < total_records:
                # 计算当前批次的大小
                current_batch = min(batch_size, total_records - records_inserted)
                
                # 生成批次数据
                values = []
                for _ in range(current_batch):
                    name = generate_random_string(20)
                    email = f"{generate_random_string(10)}@example.com"
                    phone = f"138{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
                    address = generate_random_string(100)
                    salary = round(random.uniform(3000, 20000), 2)
                    department = random.choice(['技术部', '市场部', '销售部', '人力资源部', '财务部'])
                    hire_date = f"202{random.randint(0, 4)}-{random.randint(1, 12)}-{random.randint(1, 28)}"
                    is_active = random.choice([True, False])
                    
                    values.append((name, email, phone, address, salary, department, hire_date, is_active))
                
                # 执行批量插入
                insert_sql = f"""
                INSERT INTO `{TEST_TABLE}` 
                (name, email, phone, address, salary, department, hire_date, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.executemany(insert_sql, values)
                conn.commit()
                
                records_inserted += current_batch
                elapsed_time = time.time() - start_time
                print(f"已插入 {records_inserted} 条记录，耗时 {elapsed_time:.2f} 秒")
            
            total_elapsed = time.time() - start_time
            print(f"\n数据生成完成！")
            print(f"总记录数: {total_records}")
            print(f"总耗时: {total_elapsed:.2f} 秒")
            print(f"平均速度: {total_records / total_elapsed:.2f} 条/秒")
    finally:
        conn.close()

if __name__ == "__main__":
    print("开始创建测试数据...")
    create_test_table()
    insert_test_data(batch_size=5000, total_records=100000)
    print("测试数据创建完成！")
