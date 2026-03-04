from flask import Blueprint, jsonify, request, send_from_directory
from app.services.database import db_manager
from app.models.data_source import data_source_manager
from app.models.migration_task import task_manager
import os
import json
import time

api = Blueprint('api', __name__)

@api.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': '服务运行正常'})

@api.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({'data': ['item1', 'item2', 'item3']})

@api.route('/api/data', methods=['POST'])
def create_data():
    return jsonify({'status': 'created', 'message': '数据创建成功'})

@api.route('/api/database/test', methods=['POST'])
def test_database_connection():
    """测试数据库连接"""
    data = request.json
    host = data.get('host')
    port = data.get('port', 3306)
    user = data.get('user')
    password = data.get('password')
    database = data.get('database')
    
    success, message = db_manager.test_connection(host, port, user, password, database)
    return jsonify({'success': success, 'message': message})

@api.route('/api/database/query', methods=['POST'])
def execute_query():
    """执行SQL查询"""
    data = request.json
    host = data.get('host')
    port = data.get('port', 3306)
    user = data.get('user')
    password = data.get('password')
    database = data.get('database')
    query = data.get('query')
    
    try:
        conn = db_manager.get_connection(host, port, user, password, database)
        success, result = db_manager.execute_query(conn, query)
        db_manager.close_connection(conn)
        return jsonify({'success': success, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@api.route('/api/database/migrate', methods=['POST'])
def migrate_data():
    """执行数据迁移"""
    data = request.json

    # 源数据库信息
    source_host = data.get('source_host')
    source_port = data.get('source_port', 3306)
    source_user = data.get('source_user')
    source_password = data.get('source_password')
    source_database = data.get('source_database')
    source_query = data.get('source_query')

    # 目标数据库信息
    target_host = data.get('target_host')
    target_port = data.get('target_port', 3306)
    target_user = data.get('target_user')
    target_password = data.get('target_password')
    target_database = data.get('target_database')
    target_table = data.get('target_table')
    table_structure = data.get('table_structure')
    if_exists = data.get('if_exists', 'insert')  # insert, truncate, rename
    field_mapping = data.get('field_mapping', {})  # 字段映射

    try:
        # 连接源数据库并执行查询
        source_conn = db_manager.get_connection(source_host, source_port, source_user, source_password, source_database)
        success, source_data = db_manager.execute_query(source_conn, source_query)
        if not success:
            db_manager.close_connection(source_conn)
            return jsonify({'success': False, 'message': '查询源数据失败'})

        # 连接目标数据库
        target_conn = db_manager.get_connection(target_host, target_port, target_user, target_password, target_database)

        # 检查表是否存在
        table_exists = db_manager.table_exists(target_conn, target_table)
        
        if table_exists:
            if if_exists == 'truncate':
                # 清空表数据
                if not db_manager.truncate_table(target_conn, target_table):
                    db_manager.close_connection(source_conn)
                    db_manager.close_connection(target_conn)
                    return jsonify({'success': False, 'message': '清空表数据失败'})
            elif if_exists == 'rename':
                # 重命名表
                new_table_name = f"{target_table}_{int(time.time())}"
                if not db_manager.rename_table(target_conn, target_table, new_table_name):
                    db_manager.close_connection(source_conn)
                    db_manager.close_connection(target_conn)
                    return jsonify({'success': False, 'message': '重命名表失败'})
            # insert 模式不需要处理，直接插入

        # 如果表不存在或需要重新创建
        if not table_exists or if_exists == 'rename':
            # 生成建表语句
            create_table_sql = f"CREATE TABLE IF NOT EXISTS `{target_table}` ("
            columns = []
            for field in table_structure:
                column_def = f"`{field['name']}` {field['type']}"
                if field.get('length'):
                    column_def += f"({field['length']})"
                if field.get('collation'):
                    column_def += f" COLLATE {field['collation']}"
                if field.get('nullable') is False:
                    column_def += " NOT NULL"
                if field.get('default') is not None:
                    column_def += f" DEFAULT {field['default']}"
                if field.get('primary_key'):
                    column_def += " PRIMARY KEY"
                columns.append(column_def)
            # 使用默认排序规则
            charset = 'utf8mb4'
            collation = 'utf8mb4_general_ci'
            create_table_sql += ", ".join(columns) + f") ENGINE=InnoDB DEFAULT CHARSET={charset} COLLATE={collation};"

            # 执行建表语句
            success, _ = db_manager.execute_query(target_conn, create_table_sql)
            if not success:
                db_manager.close_connection(source_conn)
                db_manager.close_connection(target_conn)
                return jsonify({'success': False, 'message': '创建目标表失败'})

        # 插入数据
        rows_affected = 0
        if source_data:
            # 处理字段映射
            if field_mapping:
                # 使用映射后的字段
                target_columns = []
                source_columns = []
                for target_field, source_field in field_mapping.items():
                    if source_field in source_data[0]:
                        target_columns.append(target_field)
                        source_columns.append(source_field)
            else:
                # 使用同名字段
                target_columns = list(source_data[0].keys())
                source_columns = target_columns

            if target_columns:
                placeholders = ["%s"] * len(target_columns)
                insert_sql = f"INSERT INTO `{target_table}` ({', '.join(['`' + col + '`' for col in target_columns])}) VALUES ({', '.join(placeholders)})"

                # 批量插入
                values = []
                for row in source_data:
                    row_values = []
                    for col in source_columns:
                        row_values.append(row[col])
                    values.append(row_values)

                # 使用多线程插入
                try:
                    # 构建目标数据库配置
                    target_config = {
                        'host': target_host,
                        'port': target_port,
                        'user': target_user,
                        'password': target_password,
                        'database': target_database
                    }
                    rows_affected = db_manager.multi_threaded_insert(
                        target_config['host'],
                        target_config['port'],
                        target_config['user'],
                        target_config['password'],
                        target_config['database'],
                        insert_sql,
                        values
                    )
                except Exception as e:
                    # 多线程失败时使用单线程
                    with target_conn.cursor() as cursor:
                        cursor.executemany(insert_sql, values)
                        target_conn.commit()
                    rows_affected = len(values)

        # 关闭连接
        db_manager.close_connection(source_conn)
        db_manager.close_connection(target_conn)

        return jsonify({'success': True, 'message': '数据迁移成功', 'rows_affected': rows_affected})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@api.route('/', methods=['GET'])
def index():
    """返回首页"""
    return send_from_directory(os.getcwd(), 'index.html')

# 数据源管理API
@api.route('/api/data-sources', methods=['GET'])
def get_data_sources():
    """获取所有数据源"""
    data_sources = data_source_manager.get_all_data_sources()
    return jsonify({'success': True, 'data': data_sources})

@api.route('/api/data-sources', methods=['POST'])
def add_data_source():
    """添加数据源"""
    data = request.json
    data_source = data_source_manager.add_data_source(data)
    return jsonify({'success': True, 'data': data_source})

@api.route('/api/data-sources/<int:index>', methods=['PUT'])
def update_data_source(index):
    """更新数据源"""
    data = request.json
    success = data_source_manager.update_data_source(index, data)
    return jsonify({'success': success})

@api.route('/api/data-sources/<int:index>', methods=['DELETE'])
def delete_data_source(index):
    """删除数据源"""
    success = data_source_manager.delete_data_source(index)
    return jsonify({'success': success})

# 迁移任务管理API
@api.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有迁移任务"""
    tasks = task_manager.get_all_tasks()
    return jsonify({'success': True, 'data': tasks})

@api.route('/api/tasks', methods=['POST'])
def add_task():
    """添加迁移任务"""
    data = request.json
    task = task_manager.add_task(data)
    return jsonify({'success': True, 'data': task})

@api.route('/api/tasks/<string:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新迁移任务"""
    data = request.json
    success = task_manager.update_task(task_id, data)
    return jsonify({'success': success})

@api.route('/api/tasks/<string:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除迁移任务"""
    success = task_manager.delete_task(task_id)
    return jsonify({'success': success})

@api.route('/api/tasks/<string:task_id>/run', methods=['POST'])
def run_task(task_id):
    """执行迁移任务"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'success': False, 'message': '任务不存在'})
    
    # 更新任务状态
    task_manager.update_task_status(task_id, 'running')
    
    try:
        # 从任务配置中获取源数据库和目标数据库信息
        source_config = task['source_config']
        target_config = task['target_config']
        source_query = task['source_query']
        target_table = task['target_table']
        table_structure = task['table_structure']
        if_exists = task.get('if_exists', 'insert')  # insert, truncate, rename
        field_mapping = task.get('field_mapping', {})  # 字段映射
        
        # 连接源数据库并执行查询
        source_conn = db_manager.get_connection(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database']
        )
        success, source_data = db_manager.execute_query(source_conn, source_query)
        if not success:
            db_manager.close_connection(source_conn)
            task_manager.update_task_status(task_id, 'failed')
            return jsonify({'success': False, 'message': '查询源数据失败'})
        
        # 连接目标数据库
        target_conn = db_manager.get_connection(
            target_config['host'],
            target_config['port'],
            target_config['user'],
            target_config['password'],
            target_config['database']
        )
        
        # 检查表是否存在
        table_exists = db_manager.table_exists(target_conn, target_table)
        
        if table_exists:
            if if_exists == 'truncate':
                # 清空表数据
                if not db_manager.truncate_table(target_conn, target_table):
                    db_manager.close_connection(source_conn)
                    db_manager.close_connection(target_conn)
                    task_manager.update_task_status(task_id, 'failed')
                    return jsonify({'success': False, 'message': '清空表数据失败'})
            elif if_exists == 'rename':
                # 重命名表
                import time
                new_table_name = f"{target_table}_{int(time.time())}"
                if not db_manager.rename_table(target_conn, target_table, new_table_name):
                    db_manager.close_connection(source_conn)
                    db_manager.close_connection(target_conn)
                    task_manager.update_task_status(task_id, 'failed')
                    return jsonify({'success': False, 'message': '重命名表失败'})
            # insert 模式不需要处理，直接插入
        
        # 如果表不存在或需要重新创建
        if not table_exists or if_exists == 'rename':
            # 生成建表语句
            create_table_sql = f"CREATE TABLE IF NOT EXISTS `{target_table}` ("
            columns = []
            for field in table_structure:
                column_def = f"`{field['name']}` {field['type']}"
                if field.get('length'):
                    column_def += f"({field['length']})"
                if field.get('collation'):
                    column_def += f" COLLATE {field['collation']}"
                if field.get('nullable') is False:
                    column_def += " NOT NULL"
                if field.get('default') is not None:
                    column_def += f" DEFAULT {field['default']}"
                if field.get('primary_key'):
                    column_def += " PRIMARY KEY"
                columns.append(column_def)
            # 使用默认排序规则
            charset = 'utf8mb4'
            collation = 'utf8mb4_general_ci'
            create_table_sql += ", ".join(columns) + f") ENGINE=InnoDB DEFAULT CHARSET={charset} COLLATE={collation};"
            
            # 执行建表语句
            success, _ = db_manager.execute_query(target_conn, create_table_sql)
            if not success:
                db_manager.close_connection(source_conn)
                db_manager.close_connection(target_conn)
                task_manager.update_task_status(task_id, 'failed')
                return jsonify({'success': False, 'message': '创建目标表失败'})
        
        # 插入数据
        rows_affected = 0
        if source_data:
            # 处理字段映射
            if field_mapping:
                # 使用映射后的字段
                target_columns = []
                source_columns = []
                for target_field, source_field in field_mapping.items():
                    if source_field in source_data[0]:
                        target_columns.append(target_field)
                        source_columns.append(source_field)
            else:
                # 使用同名字段
                target_columns = list(source_data[0].keys())
                source_columns = target_columns

            if target_columns:
                placeholders = ["%s"] * len(target_columns)
                insert_sql = f"INSERT INTO `{target_table}` ({', '.join(['`' + col + '`' for col in target_columns])}) VALUES ({', '.join(placeholders)})"

                # 批量插入
                values = []
                for row in source_data:
                    row_values = []
                    for col in source_columns:
                        row_values.append(row[col])
                    values.append(row_values)

                # 使用多线程插入
                try:
                    # 构建目标数据库配置
                    target_config = {
                        'host': target_host,
                        'port': target_port,
                        'user': target_user,
                        'password': target_password,
                        'database': target_database
                    }
                    rows_affected = db_manager.multi_threaded_insert(
                        target_config['host'],
                        target_config['port'],
                        target_config['user'],
                        target_config['password'],
                        target_config['database'],
                        insert_sql,
                        values
                    )
                except Exception as e:
                    # 多线程失败时使用单线程
                    with target_conn.cursor() as cursor:
                        cursor.executemany(insert_sql, values)
                        target_conn.commit()
                    rows_affected = len(values)
        
        # 关闭连接
        db_manager.close_connection(source_conn)
        db_manager.close_connection(target_conn)
        
        # 更新任务状态
        task_manager.update_task_status(task_id, 'completed')
        
        return jsonify({'success': True, 'message': '任务执行成功', 'rows_affected': rows_affected})
    except Exception as e:
        task_manager.update_task_status(task_id, 'failed')
        return jsonify({'success': False, 'message': str(e)})

@api.route('/api/settings', methods=['GET'])
def get_settings():
    """获取应用设置"""
    import sys
    import json
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    settings_path = os.path.join(base_dir, 'settings.json')
    default_settings = {
        'default_charset': 'utf8mb4',
        'default_collation': 'utf8mb4_general_ci',
        'default_engine': 'InnoDB',
        'batch_size': 1000,
        'allow_remote': False,
        'log_level': 'info'
    }
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return jsonify({'success': True, 'settings': {**default_settings, **settings}})
        except:
            return jsonify({'success': True, 'settings': default_settings})
    return jsonify({'success': True, 'settings': default_settings})

@api.route('/api/settings', methods=['POST'])
def save_settings():
    """保存应用设置"""
    import sys
    import json
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    settings_path = os.path.join(base_dir, 'settings.json')
    data = request.json
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True, 'message': '设置保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
