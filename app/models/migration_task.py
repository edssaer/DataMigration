import json
import os
import datetime

class MigrationTaskManager:
    def __init__(self):
        self.tasks_file = 'migration_tasks.json'
        self.tasks = self.load_tasks()
    
    def load_tasks(self):
        """加载迁移任务配置"""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def save_tasks(self):
        """保存迁移任务配置"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def add_task(self, task):
        """添加迁移任务"""
        # 添加任务ID和创建时间
        task['id'] = str(len(self.tasks) + 1)
        task['created_at'] = datetime.datetime.now().isoformat()
        task['status'] = 'pending'
        self.tasks.append(task)
        self.save_tasks()
        return task
    
    def update_task(self, task_id, task):
        """更新迁移任务"""
        for i, t in enumerate(self.tasks):
            if t['id'] == task_id:
                self.tasks[i] = task
                self.save_tasks()
                return True
        return False
    
    def delete_task(self, task_id):
        """删除迁移任务"""
        self.tasks = [t for t in self.tasks if t['id'] != task_id]
        self.save_tasks()
        return True
    
    def get_task(self, task_id):
        """获取迁移任务"""
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None
    
    def get_all_tasks(self):
        """获取所有迁移任务"""
        return self.tasks
    
    def update_task_status(self, task_id, status):
        """更新任务状态"""
        for i, task in enumerate(self.tasks):
            if task['id'] == task_id:
                self.tasks[i]['status'] = status
                self.tasks[i]['updated_at'] = datetime.datetime.now().isoformat()
                self.save_tasks()
                return True
        return False

# 全局迁移任务管理器实例
task_manager = MigrationTaskManager()