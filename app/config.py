import os
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_PWD = os.getenv("REDIS_PWD", "0000")
DB_URI = os.getenv("DB_URI", "mysql+pymysql://root:@127.0.0.1/fast_crawl")
