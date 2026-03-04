from setuptools import setup

setup(
    name='data-migration-tool',
    version='1.0.0',
    packages=['app'],
    install_requires=[
        'Flask',
        'pymysql',
        'python-dotenv',
        'cryptography'
    ],
    entry_points={
        'console_scripts': [
            'data-migration-server=app:app.run'
        ]
    }
)
