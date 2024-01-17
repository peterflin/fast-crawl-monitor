import parsers
import pkgutil
# ------------------- REDIS ------------------- #
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = "redis@cia_0119"

REDIS_REQUEST_QUEUE_PREFIX_KEY = "request"  # 請求url後塞到redis的key
REDIS_HTML_QUEUE = "html.queue"  # 向lambda呼叫後回傳html時，塞到redis的key

# ------------------- KAFKA ------------------- #
# HTML_CONSUMER_GROUP = "html.collections"
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9094']
KAFKA_STORE_DATA_TOPIC = "crawled_data"  # parser處理完資料後存向kafka的topic
KAFKA_STATES_TOPIC = "states"  # kafka state topic
KAFKA_STATES_CONSUME_GROUP = 'state_group________test'  # 設定state的consumer group

KAFKA_MODULE_STATUS_TOPIC = "module.status"
KAFKA_MODULE_STATUS_GROUP = "module"

URL_COLLECTOR_URL_CACHE_TIMEOUT = 3600  # (s)，做url的cache時，設定cache何時過期
URL_COLLECTOR_URL_NUMBER = 1  # 收集幾個url後就呼叫lambda
URL_COLLECTOR_SOCKET_HOST = "localhost"
URL_COLLECTOR_SOCKET_PORT = 5200

# ------------------- DB ------------------- #
DB_SETTING = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",
    "db": "hidden_crawl",
    "charset": "utf8"
}

# ------------------- 取得哪種parser需用哪種儲存方式 ------------------- #
DATA_STORE_TYPE = {
    "PttCrawler": "ptt",
    "Nownews": "news",
}

# ------------------- parser python file(module) ------------------- #
# PARSER_MODULE = ['hidden_crawl.parsers.news', 'hidden_crawl.parsers.ptt']
PARSER_MODULE = [__import__(modname, fromlist=['dummy']).__name__
                 for importer, modname, is_pkg in pkgutil.iter_modules(parsers.__path__, parsers.__name__ + ".")]

# Flask configuration
FLASK_LOGGING_ENABLED = True
FLASK_PORT = 5050
DEBUG = True

STAT_REQ_FREQ = 60
STAT_START_DELAY = 10

DAEMON_THREAD_JOIN_TIMEOUT = 10

# logging setup
LOGGER_NAME = 'ui-service'
LOG_DIR = 'logs'
LOG_FILE = 'ui_service.log'
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUPS = 5
LOG_STDOUT = True
LOG_JSON = False
LOG_LEVEL = 'INFO'
