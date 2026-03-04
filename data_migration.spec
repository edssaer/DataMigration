# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ('app', 'app'),  # 包含 app 目录
    ('index.html', '.'),  # 包含 index.html 文件
    ('data_sources.json', '.'),  # 包含 data_sources.json 文件
    ('migration_tasks.json', '.'),  # 包含 migration_tasks.json 文件
    ('.env', '.'),  # 包含 .env 文件
    ('requirements.txt', '.'),  # 包含 requirements.txt 文件
]

a = Analysis(['app.py'],
             pathex=['d:\\TREACN\\DataMigration'],
             binaries=[],
             datas=added_files,
             hiddenimports=['flask_cors', 'pymysql', 'dotenv'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

executable = EXE(pyz,
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              [],
              name='DataMigrationTool',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=True,
              upx_exclude=[],
              runtime_tmpdir=None,
              console=True,  # 显示控制台窗口，便于查看错误信息
              disable_windowed_traceback=False,
              target_arch=None,
              codesign_identity=None,
              entitlements_file=None)
