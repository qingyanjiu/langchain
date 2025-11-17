import redis
import json

import requests

class DifyLoginHelper:
    def __init__(self, config_file_path: str = 'dify-login-config.json'):
        self.config_file_path = config_file_path
        self.config = self._get_config()
        self.redis_client = self._get_redis_client()
    
    def _get_config(self) -> dict:
        config = {}
        with open(self.config_file_path, 'r') as f:
            config = json.loads(f.read())
        return config
    
    # 连接redis
    def _get_redis_client(self) -> redis.Redis:
        pool = redis.ConnectionPool(
            host = self.config['redis']['host'],
            port = self.config['redis']['port'],
            username = self.config['redis']['username'] if self.config['redis']['username'] else '',
            password = self.config['redis']['password'] if self.config['redis']['password'] else '',
            db = self.config['redis']['db'],
            decode_responses=True  # 返回 str 而不是 bytes
        )
        return redis.Redis(connection_pool=pool)
    
    # 登录 dify并持久化token
    def do_dify_login(self):
        token = ''
        login_url = f"http://{self.config['dify']['host']}:{self.config['dify']['port']}/console/api/login"
        login_data = {
            "email": self.config['dify']['username'],
            "password": self.config['dify']['password'],
            "language": "zh-Hans",
            "remember_me": True
        }
        try:
            response = requests.post(login_url, json=login_data)
            response_json = response.json()
            if response_json['result'] == 'success':
                response_data = response_json['data']
                token = response_data['access_token']
                expire = 2400
                # 设置token，同时设置过期时间40分钟
                self.redis_client.set('dify_token', token, ex = expire)
            print("dify登录成功")
        except Exception as e:
            print(e)
        return token
            
    # 获取token
    def get_access_token(self) -> str:
        token = self.redis_client.get('dify_token')
        if not token:
            print('登录dify获取token')
            token = self.do_dify_login()
        return token

# if __name__ == '__main__':
#     helper = DifyLoginHelper(config_file_path='agent/dify-login-config.json')
#     helper.do_dify_login()