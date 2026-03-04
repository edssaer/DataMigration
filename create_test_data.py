import pymysql
import random
import string
import time

def create_test_table():
    # 连接数据库
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='@W203222w',
        database='njyy',
        charset='utf8mb4'
    )
    
    try:
        with conn.cursor() as cursor:
            # 创建测试表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS test_source_table (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                email VARCHAR(100),
                phone VARCHAR(20),
                address VARCHAR(255),
                age INT,
                salary DECIMAL(10,2),
                department VARCHAR(50),
                hire_date DATE,
                status VARCHAR(20)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cursor.execute(create_table_sql)
            conn.commit()
            print("测试表创建成功")
            
            # 清空表数据
            cursor.execute("TRUNCATE TABLE test_source_table")
            conn.commit()
            print("表数据已清空")
            
            # 生成10万条测试数据
            start_time = time.time()
            batch_size = 1000
            total_records = 100000
            
            for batch in range(0, total_records, batch_size):
                values = []
                for i in range(batch_size):
                    if batch + i >= total_records:
                        break
                    
                    name = ''.join(random.choices(string.ascii_letters, k=10))
                    email = f"{name}@example.com"
                    phone = f"138{random.randint(10000000, 99999999)}"
                    address = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
                    age = random.randint(18, 65)
                    salary = round(random.uniform(3000, 20000), 2)
                    department = random.choice(['IT', 'HR', 'Finance', 'Marketing', 'Sales'])
                    hire_date = f"202{random.randint(0, 6)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
                    status = random.choice(['active', 'inactive', 'suspended'])
                    
                    values.append((name, email, phone, address, age, salary, department, hire_date, status))
                
                if values:
                    insert_sql = """
                    INSERT INTO test_source_table (name, email, phone, address, age, salary, department, hire_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.executemany(insert_sql, values)
                    conn.commit()
                    print(f"已插入 {batch + len(values)} 条数据")
            
            end_time = time.time()
            print(f"数据生成完成，耗时: {end_time - start_time:.2f} 秒")
            
            # 验证数据量
            cursor.execute("SELECT COUNT(*) FROM test_source_table")
            count = cursor.fetchone()[0]
            print(f"表中实际数据量: {count}")
            
    except Exception as e:
        print(f"错误: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_test_table()
