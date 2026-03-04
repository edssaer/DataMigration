from app import app
import json
import os

def get_settings():
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
    default_settings = {
        'allow_remote': False
    }
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default_settings
    return default_settings

if __name__ == '__main__':
    settings = get_settings()
    host = '0.0.0.0' if settings.get('allow_remote', False) else '127.0.0.1'
    app.run(debug=True, host=host, port=5000)
