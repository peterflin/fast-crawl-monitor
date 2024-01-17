#coding=utf8
import redis
from scutils.redis_queue import RedisQueue
import settings
import time
import json
import kafka
import logging
import uuid
import traceback


# "Add Request" module
# 參數: url, parser name, uid
# uid: job id，用來記錄此次request的job
# option參數: level(level=0時不會因為cache而跳過這次的請求)
# step 1.

logging.basicConfig(format='%(asctime)s [%(name)-12s]: [%(levelname)s] : %(message)s', level=logging.INFO)


def add(url, parser_name, uid, level=0):

    try:
        # record state
        kafka_conn = kafka.KafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "init",
                   "state-message": "Send url to Redis.", "parser_name": parser_name, "url": url,
                   "uid": str(uid)}
        message = json.dumps(message)
        print('test')
        future = kafka_conn.send(settings.KAFKA_STATES_TOPIC, bytes(message, encoding='utf8'))
        result = future.get(timeout=10)
        print('test2')
        logging.info(result)

        # work
        request_key = settings.REDIS_REQUEST_QUEUE_PREFIX_KEY
        redis_conn = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD)
        queue = RedisQueue(redis_conn, request_key)
        queue.push({"url": url, "level": level, "parser_name": parser_name, "uid": uid})
        # redis_conn.hset(url, 'parser', parser)
        # redis_conn.hset(url, 'time', time.time())
        # redis_conn.hset(url, 'domain', domain)

        logging.info("Add %s to Redis" % url)
        return {"status": "SUCCESS"}
    except:
        kafka_conn = kafka.KafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "error",
                   "state-message": "Send url {} to Redis error at add request.", "parser_name": parser_name, "url": url,
                   "uid": str(uid), "error message": traceback.format_exc()}
        message = json.dumps(message)
        future = kafka_conn.send(settings.KAFKA_STATES_TOPIC, bytes(message, encoding='utf8'))
        result = future.get(timeout=10)
        logging.info(result)
        return {"status": "FAIL"}


if __name__ == '__main__':
    uid = uuid.uuid1()
    uid = str(uid)
    add("https://www.ptt.cc/bbs/Gossiping/index.html", "PttCrawler:parse", uid=uid)  # 測試用
    # add("http://www.nownews.com/", "Nownews:parse", uid=uid)
    # for i in range(39000, 38900, -1):
    #     print(i)
    #     uid = uuid.uuid1()
    #     uid = str(uid)
    #     add('https://www.ptt.cc/bbs/Gossiping/index{}.html'.format(i), "PttCrawler:parse", uid=uid)
    #     time.sleep(10)
