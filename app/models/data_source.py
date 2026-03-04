import json
import os

class DataSourceManager:
    def __init__(self):
        self.data_sources_file = 'data_sources.json'
        self.data_sources = self.load_data_sources()
    
    def load_data_sources(self):
        """加载数据源配置"""
        if os.path.exists(self.data_sources_file):
            try:
                with open(self.data_sources_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def save_data_sources(self):
        """保存数据源配置"""
        with open(self.data_sources_file, 'w', encoding='utf-8') as f:
            json.dump(self.data_sources, f, ensure_ascii=False, indent=2)
    
    def add_data_source(self, data_source):
        """添加数据源"""
        self.data_sources.append(data_source)
        self.save_data_sources()
        return data_source
    
    def update_data_source(self, index, data_source):
        """更新数据源"""
        if 0 <= index < len(self.data_sources):
            self.data_sources[index] = data_source
            self.save_data_sources()
            return True
        return False
    
    def delete_data_source(self, index):
        """删除数据源"""
        if 0 <= index < len(self.data_sources):
            del self.data_sources[index]
            self.save_data_sources()
            return True
        return False
    
    def get_data_source(self, index):
        """获取数据源"""
        if 0 <= index < len(self.data_sources):
            return self.data_sources[index]
        return None
    
    def get_all_data_sources(self):
        """获取所有数据源"""
        return self.data_sources

# 全局数据源管理器实例
data_source_manager = DataSourceManager()