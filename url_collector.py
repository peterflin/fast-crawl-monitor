import redis
import settings
from lambda_processor import LambdaProcessor
from scutils.redis_queue import RedisQueue
import time
import kafka
import logging
import threading
import json
import socket
import traceback
import hashlib


logging.basicConfig(format='%(asctime)s [%(name)-12s]: [%(levelname)s] : %(message)s', level=logging.INFO)


# "URL Collector" module
class UrlCollector(object):

    def __init__(self, open_on='localhost'):
        self.open_on = open_on
        self.url_cache_timeout = settings.URL_COLLECTOR_URL_CACHE_TIMEOUT  # set cache timeout
        self.redis_conn = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                      password=settings.REDIS_PASSWORD)
        self.url_queue = RedisQueue(self.redis_conn, settings.REDIS_REQUEST_QUEUE_PREFIX_KEY)  # 取得url的queue
        self.html_queue = RedisQueue(self.redis_conn, settings.REDIS_HTML_QUEUE)  # 塞入回傳html的queue
        self.kafka_conn = kafka.KafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        # self.kafka_html_topic = "html.collections"
        self.url_cache = {}  # url cache
        self.new_request_list = []  # 暫存從redis取得的url
        self.logger = logging.getLogger(__class__.__name__)
        self.stop_flag = False  # 控制整個模組停止

        # 用於trigger lambda的thread
        self.lambda_caller = threading.Thread(target=self.lambda_request)
        self.lambda_caller.setDaemon(True)
        self.lambda_caller.start()

        # # socket setting
        # self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self._socket.bind((settings.URL_COLLECTOR_SOCKET_HOST, settings.URL_COLLECTOR_SOCKET_PORT))
        # self._socket.listen(5)
        # print(settings.URL_COLLECTOR_SOCKET_HOST)
        # self._socket_thread = threading.Thread(target=self._socket_process)
        # self._socket_thread.setDaemon(True)
        # self._socket_thread.start()
        # self._socket_access_key = "abs12346"

    # main function
    def run(self):
        self.logger.info("Run loop.")
        while 1:
            if self.stop_flag:
                print("------break------")
                break
            # pop data, if no data will return none
            # step 2.
            new_data = self.url_queue.pop()
            try:
                # not none代表有資料
                if new_data is not None:
                    new_url = new_data['url']
                    self.logger.info("new url: %s" % new_url)
                    # 檢查是網站還是網址，是網站便跳過cache的排除
                    if new_data['level'] == 0 or new_url not in self.url_cache:
                        # state enqueue
                        message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "enqueue",
                                   "state-message": "Enqueue and wait to request.",
                                   "parser_name": new_data["parser_name"],
                                   "url": new_data['url'], "uid": new_data['uid'], "open_on": self.open_on}
                        future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                      bytes(json.dumps(message), encoding='utf8'))
                        result = future.get(timeout=10)
                        self.logger.info("Send State to Kafka, partition: {}".format(result.partition))
                        self.logger.info("add new url.")
                        if new_data['level'] != 0:  # 更新網址請求的cache，且不將此url加入cache
                            self.url_cache[new_url] = time.time()
                        self.new_request_list.append({"url": new_url, "parser_name": new_data["parser_name"],
                                                      "uid": new_data['uid']})
                    else:
                        message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "drop",
                                   "state-message": "Filter by cache {}.".format(new_url),
                                   "parser_name": new_data["parser_name"],
                                   "url": new_data['url'], "uid": new_data['uid'], "open_on": self.open_on}
                        future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                      bytes(json.dumps(message), encoding='utf8'))
                        result = future.get(timeout=10)
                        self.logger.info(result)
                        self.logger.info("Filter by cache {}".format(new_url))
                # none時休息5秒
                elif new_data is None:
                    self.logger.warning("There is no data in Redis.")
                    time.sleep(5)
                self.logger.warning('There is {} urls wait to request.'.format(len(self.new_request_list)))

                # clear cache
                del_list = []
                for url in self.url_cache:
                    if time.time() - self.url_cache[url] > self.url_cache_timeout:
                        del_list.append(url)
                for url in del_list:
                    self.logger.info("Clear cache {}.".format(url))
                    del self.url_cache[url]
            except:

                message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "error",
                           "state-message": "Collect url error at url collector(run).\n" + traceback.format_exc(),
                           "parser_name": new_data["parser_name"] if new_data is not None else "",
                           "url": new_data['url'] if new_data is not None else "",
                           "uid": new_data['uid'] if new_data is not None else "",
                           "error message": traceback.format_exc(), "open_on": self.open_on}
                future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                              bytes(json.dumps(message), encoding='utf8'))
                result = future.get(timeout=10)

    # 控制trigger lambda的function
    def lambda_request(self):
        count = 0
        while 1:
            if self.stop_flag:
                break
            # 達某個門檻即可發布出去，可繼續附加或修改門檻條件
            if len(self.new_request_list) >= settings.URL_COLLECTOR_URL_NUMBER:
                # call lambda
                # step 3. + 4.
                try:
                    self.logger.info("Request url.")
                    # update cache
                    for url in self.new_request_list:
                        if url['url'] not in self.url_cache:
                            self.url_cache[url['url']] = time.time()
                        else:
                            self.url_cache[url['url']] = time.time()
                    # return_data = LambdaProcessor().request_lambda(self.new_request_list)  # call lambda
                    return_data = LambdaProcessor().request(self.new_request_list)  # call request(使用requests)
                    for ret in return_data:
                        if ret['url'] in self.new_request_list:
                            self.new_request_list.remove(ret['url'])
                            try:
                                message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                           "state": "dequeue",
                                           "state-message": "Dequeue and request.", "parser_name": ret["parser_name"],
                                           "url": ret['url'], "uid": ret['uid'], "open_on": self.open_on}
                                future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                              bytes(json.dumps(message), encoding='utf8'))
                                result = future.get(timeout=10)
                                self.logger.info(result)
                            except KeyError:
                                message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                           "state": "error",
                                           "state-message": "KeyError when send state message to kafka " +
                                                            "at url collector(lambda_request).",
                                           "parser_name": ret['parser_name'] if 'parser_name' in ret else "",
                                           "url": ret['url'] if 'url' in ret else "",
                                           "uid": ret['uid'] if 'uid' in ret else "",
                                           "error message": traceback.format_exc(), "open_on": self.open_on}
                                future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                              bytes(json.dumps(message), encoding='utf8'))
                                result = future.get(timeout=10)
                                self.logger.error(traceback.format_exc())
                    # let "return data" type is list
                    self.logger.info("Push return data.")
                    # step 5.
                    for html_data in return_data:
                        # html_data => {"url": "https://www.testurl.com/",
                        #               "html": "html document",
                        #               "parser_name": "parser name",
                        #               "uid": "this job uid"}
                        self.html_queue.push(html_data)
                    self.logger.debug("Update cache.")
                except Exception:
                    message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "error",
                               "state-message": "Error when call lambda at url collector(lambda_request).",
                               "parser_name": "", "url": "", "uid": "",
                               "error message": traceback.format_exc(), "open_on": self.open_on}
                    future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                  bytes(json.dumps(message), encoding='utf8'))
                    result = future.get(timeout=10)
                    self.logger.error(traceback.format_exc())

                # except:
                #     message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "error",
                #                "state-message": "Occur error at url collector(lambda_request).", "parser_name": "",
                #                "url": d['url'], "uid": d['uid'], "error message": traceback.format_exc()}
                #     future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                #                                   bytes(json.dumps(message), encoding='utf8'))
                #     result = future.get(timeout=10)
            else:  # 單純show訊息
                count += 1
                time.sleep(5)
                if count == 6:
                    self.logger.info("There are %d urls in request list." % len(self.new_request_list))
                    count = 0

    def stop(self):
        self.stop_flag = True

    def _socket_process(self):
        # while 1:
        #     conn, addr = self._socket.accept()
        #     self.logger.info("An accept from {}:{}".format(addr[0], addr[1]))
        #     data = conn.recv(1024)
        #     if data.decode() == self._socket_access_key:
        #         send_message = {"new_request": len(self.new_request_list), "alive": 1,
        #                         "lambda_trigger": int(self.lambda_caller.is_alive())}
        #         conn.send(bytes(json.dumps(send_message), encoding='utf8'))
        #         conn.close()
        #     else:
        #         conn.close()
        while 1:
            if self.stop_flag:
                break
            send_message = {"module": self.__class__.__name__,
                            "new_request": len(self.new_request_list),
                            "alive": 1,
                            "lambda_trigger": int(self.lambda_caller.is_alive())}
            f = self.kafka_conn.send(settings.KAFKA_MODULE_STATUS_TOPIC,
                                     bytes(json.dumps(send_message), encoding='utf8'))
            result = f.get(timeout=10)
            self.logger.info("Send module status, topic={}, partition={}, offset={}".format(
                result.topic, result.partition, result.offset))
            time.sleep(10)


if __name__ == '__main__':
    # UrlCollector().run()
    u = UrlCollector()
    u.run()
