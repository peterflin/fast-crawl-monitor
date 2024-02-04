import os
REDIS_HOST = os.getenv("redis_host", "127.0.0.1")
REDIS_PORT = os.getenv("redis_port", 6379)
REDIS_PWD = os.getenv("redis_pwd", "0000")
DB_URI = os.getenv("db_uri", "mysql+pymysql://root:@127.0.0.1/fast_crawl")
