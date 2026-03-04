import pymysql

# 检查large_test_data表的结构
def check_table_structure():
    # 连接数据库
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='@W203222w',
        database='NJYY'
    )
    
    try:
        with conn.cursor() as cursor:
            # 查询表结构
            cursor.execute("DESCRIBE large_test_data")
            fields = cursor.fetchall()
            print("large_test_data表结构:")
            for field in fields:
                print(f"字段名: {field[0]}, 类型: {field[1]}, 是否为空: {field[2]}, 默认值: {field[4]}, 主键: {field[3]}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_table_structure()
