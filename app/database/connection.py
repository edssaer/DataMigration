import pymysql
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 加密密钥
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode())

class DatabaseConnection:
    def __init__(self, host, port, user, password, database, db_type='mysql'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.db_type = db_type
        self.connection = None
    
    def encrypt_password(self, password):
        """加密密码"""
        return fernet.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password):
        """解密密码"""
        return fernet.decrypt(encrypted_password.encode()).decode()
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            if self.db_type == 'mysql':
                self.connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self