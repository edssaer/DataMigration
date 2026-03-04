from flask import Blueprint, jsonify, request, send_from_directory
from app.services.database_service import db_service
from app.models.data_source import data_source_manager
from app.models.migration_task import task_manager
import os
import json
import time
import logging
import sys
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)

@api.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    try:
        logger.info("健康检查请求")
        return jsonify({'status': 'ok', 'message': '服务运行正常'})
    except Exception as e:
        logger.error(f"健康检查失败: {e}\n{traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': '服务异常'}), 500

@api.route('/api/data', methods=['GET'])
def get_data():
    """测试数据接口"""
    try:
        logger.info("获取测试数据请求")
        return jsonify({'data': ['item1', 'item2', 'item3']})
    except Exception as e:
        logger.error(f"获取测试数据失败: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@api.route('/api/data', methods=['POST'])
def create_data():
    """测试创建数据接口"""
    try:
        logger.info("创建测试数据请求")
        return jsonify({'status': 'created', 'message': '数据创建成功'})
    except Exception as e:
        logger.error(f"创建测试数据失败: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@api.route('/api/database/test', methods=['POST'])
def test_database_connection():
    """测试数据库连接"""
    try:
        data = request.json
        host = data.get('host')
        port = data.get('port', 3306)
        user = data.get('user')
        password = data.get('password')
        database = data.get('database')
        
        logger.info(f"测试数据库连接请求: {host}:{port}/{database}")
        success, message = db_service.test_connection(host, port, user, password, database)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error(f"测试数据库连接失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/database/query', methods=['POST'])
def execute_query():
    """执行SQL查询"""
    try:
        data = request.json
        host = data.get('host')
        port = data.get('port', 3306)
        user = data.get('user')
        password = data.get('password')
        database = data.get('database')
        query = data.get('query')
        
        logger.info(f"执行SQL查询请求: {host}:{port}/{database}, 查询: {query[:100]}...")
        conn = db_service.get_connection(host, port, user, password, database)
        success, result = db_service.execute_query(conn, query)
        db_service.close_connection(conn)
        return jsonify({'success': success, 'result': result})
    except Exception as e:
        logger.error(f"执行SQL查询失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/database/migrate', methods=['POST'])
def migrate_data():
    """执行数据迁移"""
    try:
        data = request.json
        logger.info(f"接收到迁移请求: {data}")

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
        logger.info(f"原始table_structure: {table_structure}, 类型: {type(table_structure)}")
        # 确保table_structure是列表格式
        if table_structure is None:
            table_structure = []
        elif isinstance(table_structure, str):
            try:
                import json
                table_structure = json.loads(table_structure)
                logger.info(f"解析后table_structure: {table_structure}")
            except Exception as e:
                logger.error(f"解析table_structure失败: {e}\n{traceback.format_exc()}")
                table_structure = []
        elif not isinstance(table_structure, list):
            logger.error(f"table_structure类型错误: {type(table_structure)}")
            table_structure = []
        if_exists = data.get('if_exists', 'insert')  # insert, truncate, rename
        field_mapping = data.get('field_mapping', {})  # 字段映射
        logger.info(f"处理后参数: table_structure={table_structure}, if_exists={if_exists}")

        # 连接源数据库并执行查询
        source_conn = None
        try:
            source_conn = db_service.get_connection(source_host, source_port, source_user, source_password, source_database)
            success, result = db_service.execute_query(source_conn, source_query)
            if not success:
                error_msg = str(result) if result else '未知错误'
                db_service.close_connection(source_conn)
                logger.error(f"查询源数据失败: {error_msg}")
                return jsonify({'success': False, 'message': f'查询源数据失败: {error_msg}'})
            source_data = result
            logger.info(f"查询源数据成功，获取到 {len(source_data)} 条记录")
        except Exception as e:
            if source_conn:
                db_service.close_connection(source_conn)
            logger.error(f"连接源数据库失败: {e}\n{traceback.format_exc()}")
            return jsonify({'success': False, 'message': f'连接源数据库失败: {str(e)}'})

        # 连接目标数据库
        try:
            target_conn = db_service.get_connection(target_host, target_port, target_user, target_password, target_database)
        except Exception as e:
            logger.error(f"连接目标数据库失败: {e}\n{traceback.format_exc()}")
            db_service.close_connection(source_conn)
            return jsonify({'success': False, 'message': f'连接目标数据库失败: {str(e)}'})

        # 检查表是否存在
        table_exists = db_service.table_exists(target_conn, target_table)
        
        if table_exists:
            if if_exists == 'truncate':
                # 清空表数据
                if not db_service.truncate_table(target_conn, target_table):
                    db_service.close_connection(source_conn)
                    db_service.close_connection(target_conn)
                    return jsonify({'success': False, 'message': '清空表数据失败'})
            elif if_exists == 'rename':
                # 重命名表
                new_table_name = f"{target_table}_{int(time.time())}"
                if not db_service.rename_table(target_conn, target_table, new_table_name):
                    db_service.close_connection(source_conn)
                    db_service.close_connection(target_conn)
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
            success, _ = db_service.execute_query(target_conn, create_table_sql)
            if not success:
                db_service.close_connection(source_conn)
                db_service.close_connection(target_conn)
                return jsonify({'success': False, 'message': '创建目标表失败'})
            logger.info(f"创建目标表成功: {target_table}")

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
                logger.info(f"使用字段映射: {field_mapping}")
            else:
                # 使用同名字段
                target_columns = list(source_data[0].keys())
                source_columns = target_columns
                logger.info(f"使用同名字段: {target_columns}")

            if target_columns:
                logger.info(f"源数据字段: {target_columns}")
                logger.info(f"源数据示例: {source_data[0] if source_data else '无数据'}")
                
                # 过滤出目标表中实际存在的字段
                existing_columns = []
                try:
                    # 查询目标表的实际字段
                    show_columns_sql = f"SHOW COLUMNS FROM `{target_table}`"
                    logger.info(f"执行SQL: {show_columns_sql}")
                    success, columns_result = db_service.execute_query(target_conn, show_columns_sql)
                    logger.info(f"查询结果: success={success}, columns_result={columns_result}")
                    if success and columns_result:
                        # 处理不同格式的返回结果
                        if isinstance(columns_result[0], dict):
                            # 如果返回的是字典列表
                            existing_columns = [col['Field'] for col in columns_result]
                        else:
                            # 如果返回的是元组列表
                            existing_columns = [col[0] for col in columns_result]
                        logger.info(f"目标表 {target_table} 的实际字段: {existing_columns}")
                    else:
                        logger.error(f"查询目标表字段失败，success={success}, columns_result={columns_result}")
                except Exception as e:
                    logger.error(f"查询目标表字段失败: {e}\n{traceback.format_exc()}")
                
                # 只使用目标表中存在的字段
                filtered_target_columns = []
                filtered_source_columns = []
                for target_col, source_col in zip(target_columns, source_columns):
                    logger.info(f"检查字段: target_col={target_col}, source_col={source_col}, in_existing={target_col in existing_columns}")
                    if target_col in existing_columns:
                        filtered_target_columns.append(target_col)
                        filtered_source_columns.append(source_col)
                
                logger.info(f"过滤后目标字段: {filtered_target_columns}")
                logger.info(f"过滤后源字段: {filtered_source_columns}")
                
                if filtered_target_columns:
                    placeholders = ["%s"] * len(filtered_target_columns)
                    insert_sql = f"INSERT INTO `{target_table}` ({', '.join(['`' + col + '`' for col in filtered_target_columns])}) VALUES ({', '.join(placeholders)})"
                    logger.info(f"构建的插入SQL语句: {insert_sql}")

                    # 批量插入
                    values = []
                    for row in source_data:
                        row_values = []
                        for col in filtered_source_columns:
                            row_values.append(row[col])
                        values.append(row_values)
                    logger.info(f"准备插入 {len(values)} 条记录")

                    # 使用多线程插入
                    try:
                        rows_affected = db_service.multi_threaded_insert(
                            target_host,
                            target_port,
                            target_user,
                            target_password,
                            target_database,
                            insert_sql,
                            values
                        )
                    except Exception as e:
                        logger.error(f"多线程插入失败，使用单线程: {e}\n{traceback.format_exc()}")
                        # 多线程失败时使用单线程
                        with target_conn.cursor() as cursor:
                            cursor.executemany(insert_sql, values)
                            target_conn.commit()
                        rows_affected = len(values)
                else:
                    logger.error("目标表中没有与源数据匹配的字段")
                    return jsonify({'success': False, 'message': '目标表中没有与源数据匹配的字段'})

        # 关闭连接
        db_service.close_connection(source_conn)
        db_service.close_connection(target_conn)

        logger.info(f"数据迁移成功，影响行数: {rows_affected}")
        return jsonify({'success': True, 'message': '数据迁移成功', 'rows_affected': rows_affected})
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"数据迁移失败: {e}\n{error_traceback}")
        # 关闭连接（如果已定义）
        if 'source_conn' in locals():
            try:
                db_service.close_connection(source_conn)
            except:
                pass
        if 'target_conn' in locals():
            try:
                db_service.close_connection(target_conn)
            except:
                pass
        return jsonify({'success': False, 'message': str(e), 'traceback': error_traceback}), 500

@api.route('/', methods=['GET'])
def index():
    """返回首页"""
    try:
        logger.info("返回首页请求")
        return send_from_directory(os.getcwd(), 'index.html')
    except Exception as e:
        logger.error(f"返回首页失败: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

# 数据源管理API
@api.route('/api/data-sources', methods=['GET'])
def get_data_sources():
    """获取所有数据源"""
    try:
        logger.info("获取所有数据源请求")
        data_sources = data_source_manager.get_all_data_sources()
        logger.info(f"获取到 {len(data_sources)} 个数据源")
        return jsonify({'success': True, 'data': data_sources})
    except Exception as e:
        logger.error(f"获取数据源失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/data-sources', methods=['POST'])
def add_data_source():
    """添加数据源"""
    try:
        data = request.json
        logger.info(f"添加数据源请求: {data}")
        data_source = data_source_manager.add_data_source(data)
        logger.info(f"添加数据源成功: {data_source}")
        return jsonify({'success': True, 'data': data_source})
    except Exception as e:
        logger.error(f"添加数据源失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/data-sources/<int:index>', methods=['PUT'])
def update_data_source(index):
    """更新数据源"""
    try:
        data = request.json
        logger.info(f"更新数据源请求: 索引 {index}, 数据 {data}")
        success = data_source_manager.update_data_source(index, data)
        logger.info(f"更新数据源成功: {success}")
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"更新数据源失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/data-sources/<int:index>', methods=['DELETE'])
def delete_data_source(index):
    """删除数据源"""
    try:
        logger.info(f"删除数据源请求: 索引 {index}")
        success = data_source_manager.delete_data_source(index)
        logger.info(f"删除数据源成功: {success}")
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"删除数据源失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 迁移任务管理API
@api.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有迁移任务"""
    try:
        logger.info("获取所有迁移任务请求")
        tasks = task_manager.get_all_tasks()
        logger.info(f"获取到 {len(tasks)} 个迁移任务")
        return jsonify({'success': True, 'data': tasks})
    except Exception as e:
        logger.error(f"获取迁移任务失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/tasks', methods=['POST'])
def add_task():
    """添加迁移任务"""
    try:
        data = request.json
        logger.info(f"添加迁移任务请求: {data}")
        task = task_manager.add_task(data)
        logger.info(f"添加迁移任务成功: {task}")
        return jsonify({'success': True, 'data': task})
    except Exception as e:
        logger.error(f"添加迁移任务失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/tasks/<string:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新迁移任务"""
    try:
        data = request.json
        logger.info(f"更新迁移任务请求: ID {task_id}, 数据 {data}")
        success = task_manager.update_task(task_id, data)
        logger.info(f"更新迁移任务成功: {success}")
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"更新迁移任务失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/tasks/<string:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除迁移任务"""
    try:
        logger.info(f"删除迁移任务请求: ID {task_id}")
        success = task_manager.delete_task(task_id)
        logger.info(f"删除迁移任务成功: {success}")
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"删除迁移任务失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/tasks/<string:task_id>/run', methods=['POST'])
def run_task(task_id):
    """执行迁移任务"""
    try:
        logger.info(f"执行迁移任务请求: ID {task_id}")
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return jsonify({'success': False, 'message': '任务不存在'})
        
        # 更新任务状态
        task_manager.update_task_status(task_id, 'running')
        
        # 从任务配置中获取源数据库和目标数据库信息
        source_config = task['source_config']
        target_config = task['target_config']
        source_query = task['source_query']
        target_table = task['target_table']
        table_structure = task['table_structure']
        if_exists = task.get('if_exists', 'insert')  # insert, truncate, rename
        field_mapping = task.get('field_mapping', {})  # 字段映射
        
        # 连接源数据库并执行查询
        source_conn = db_service.get_connection(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database']
        )
        success, source_data = db_service.execute_query(source_conn, source_query)
        if not success:
            db_service.close_connection(source_conn)
            task_manager.update_task_status(task_id, 'failed')
            logger.error(f"查询源数据失败: {source_data}")
            return jsonify({'success': False, 'message': '查询源数据失败'})
        logger.info(f"查询源数据成功，获取到 {len(source_data)} 条记录")
        
        # 连接目标数据库
        target_conn = db_service.get_connection(
            target_config['host'],
            target_config['port'],
            target_config['user'],
            target_config['password'],
            target_config['database']
        )
        
        # 检查表是否存在
        table_exists = db_service.table_exists(target_conn, target_table)
        
        if table_exists:
            if if_exists == 'truncate':
                # 清空表数据
                if not db_service.truncate_table(target_conn, target_table):
                    db_service.close_connection(source_conn)
                    db_service.close_connection(target_conn)
                    task_manager.update_task_status(task_id, 'failed')
                    return jsonify({'success': False, 'message': '清空表数据失败'})
            elif if_exists == 'rename':
                # 重命名表
                new_table_name = f"{target_table}_{int(time.time())}"
                if not db_service.rename_table(target_conn, target_table, new_table_name):
                    db_service.close_connection(source_conn)
                    db_service.close_connection(target_conn)
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
            success, _ = db_service.execute_query(target_conn, create_table_sql)
            if not success:
                db_service.close_connection(source_conn)
                db_service.close_connection(target_conn)
                task_manager.update_task_status(task_id, 'failed')
                return jsonify({'success': False, 'message': '创建目标表失败'})
            logger.info(f"创建目标表成功: {target_table}")
        
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
                logger.info(f"使用字段映射: {field_mapping}")
            else:
                # 使用同名字段
                target_columns = list(source_data[0].keys())
                source_columns = target_columns
                logger.info(f"使用同名字段: {target_columns}")

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
                    rows_affected = db_service.multi_threaded_insert(
                        target_config['host'],
                        target_config['port'],
                        target_config['user'],
                        target_config['password'],
                        target_config['database'],
                        insert_sql,
                        values
                    )
                except Exception as e:
                    logger.error(f"多线程插入失败，使用单线程: {e}\n{traceback.format_exc()}")
                    # 多线程失败时使用单线程
                    with target_conn.cursor() as cursor:
                        cursor.executemany(insert_sql, values)
                        target_conn.commit()
                    rows_affected = len(values)
        
        # 关闭连接
        db_service.close_connection(source_conn)
        db_service.close_connection(target_conn)
        
        # 更新任务状态
        task_manager.update_task_status(task_id, 'completed')
        
        logger.info(f"任务执行成功，影响行数: {rows_affected}")
        return jsonify({'success': True, 'message': '任务执行成功', 'rows_affected': rows_affected})
    except Exception as e:
        logger.error(f"执行迁移任务失败: {e}\n{traceback.format_exc()}")
        # 只有在run_task函数中才需要更新任务状态
        if 'task_id' in locals():
            task_manager.update_task_status(task_id, 'failed')
        # 关闭连接（如果已定义）
        if 'source_conn' in locals():
            try:
                db_service.close_connection(source_conn)
            except:
                pass
        if 'target_conn' in locals():
            try:
                db_service.close_connection(target_conn)
            except:
                pass
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/settings', methods=['GET'])
def get_settings():
    """获取应用设置"""
    try:
        logger.info("获取应用设置请求")
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
                    logger.info(f"获取应用设置成功: {settings}")
                    return jsonify({'success': True, 'settings': {**default_settings, **settings}})
            except Exception as e:
                logger.error(f"读取设置文件失败: {e}\n{traceback.format_exc()}")
                return jsonify({'success': True, 'settings': default_settings})
        logger.info(f"使用默认设置: {default_settings}")
        return jsonify({'success': True, 'settings': default_settings})
    except Exception as e:
        logger.error(f"获取应用设置失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api.route('/api/settings', methods=['POST'])
def save_settings():
    """保存应用设置"""
    try:
        data = request.json
        logger.info(f"保存应用设置请求: {data}")
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        settings_path = os.path.join(base_dir, 'settings.json')
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("设置保存成功")
        return jsonify({'success': True, 'message': '设置保存成功'})
    except Exception as e:
        logger.error(f"保存应用设置失败: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': str(e)}), 500
