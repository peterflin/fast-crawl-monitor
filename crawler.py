import settings
from bs4 import BeautifulSoup
import redis
from scutils.redis_queue import RedisQueue
import kafka
import json
from parsers.parser import Parse
import time
import add_request
import threading
import traceback
import logging


logging.basicConfig(format='%(asctime)s :%(name)-12s: %(levelname)s : %(message)s', level=logging.INFO)


# Crawler部分的class
# new class的時候需給name，目的為區別每個處理html的process，後續自動啟動程式可能需要(OR無須也可，目前無功能上的影響)
class HtmlProcessor(object):

    def __init__(self, open_on='localhost'):
        self.open_on = open_on
        self.name = "test"
        self.kafka_conn = kafka.KafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        self.redis_conn = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                      password=settings.REDIS_PASSWORD)
        self.html_queue = RedisQueue(self.redis_conn, settings.REDIS_HTML_QUEUE)
        self.null_time = 0
        self.url_handle = 0
        self.logger = logging.getLogger(__class__.__name__)

        self.current_url = None
        self.stop_flag = False
        # self._socket_thread = threading.Thread(target=self._socket_process)
        # self._socket_thread.setDaemon(True)
        # self._socket_thread.start()

    # step 6.
    def run(self):
        self.logger.info("start to parse.")
        while 1:
            if self.stop_flag:
                break
            if self.null_time > 5:  # 純秀訊息
                self.logger.info("html queue len: {}".format(self.html_queue.__len__()))
                self.null_time = 0

            # 有資料(html)再做pop
            if self.html_queue.__len__() >= 1:
                self.logger.info("get data, start parse.")
                try:
                    html = self.html_queue.pop()
                except Exception:
                    message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "error",
                               "state-message": "Error when pop html queue data at html processor.\n"
                                                + traceback.format_exc(),
                               "parser_name": "", "url": "", "uid": "",
                               "open_on": self.open_on}
                    future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                  bytes(json.dumps(message), encoding='utf8'))
                    result = future.get(timeout=10)
                    self.logger.error(traceback.format_exc())
                else:
                    if html is not None:  # 確認有pop到資料
                        self.logger.info("html pop: " + html['url'])
                        # soup = BeautifulSoup(html['html'], 'lxml')
                        parser_name = html['parser_name']  # string
                        self.logger.info("Parser: " + parser_name)
                        self.current_url = html

                        # state record
                        message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                   "state": "parse",
                                   "state-message": "Parse page.",
                                   "parser_name": parser_name, "url": html['url'],
                                   "uid": html['uid'],
                                   "spider": self.name, "open_on": self.open_on}
                        future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                      bytes(json.dumps(message), encoding='utf8'))
                        result = future.get(timeout=10)
                        self.logger.info(result)

                        # parsed_data = Parse().parse(parser_name, soup)  # 呼叫parser，並傳入html解析，回傳解析結果
                        try:
                            return_data = Parse().parser(parser_name=parser_name, html=html['html'], url=html['url'],
                                                         open_on=self.open_on, uid=html['uid'])
                        except:
                            message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "error",
                                       "state-message": "Error when parse html at html processor.\n"
                                                        + traceback.format_exc(),
                                       "parser_name": html['parser_name'], "url": html['url'], "uid": html['uid'],
                                       "open_on": self.open_on}
                            future = self.kafka_conn.send(settings.KAFKA_STATES_TOPIC,
                                                          bytes(json.dumps(message), encoding='utf8'))
                            result = future.get(timeout=10)
                            self.logger.error(traceback.format_exc())
                        else:
                            # 有錯誤即回傳none
                            if return_data is not None:
                                # step 8.
                                for item in return_data["item"]:
                                    send_data = {"parser_name": html['parser_name'], "url": html['url'],
                                                 "DataType": settings.DATA_STORE_TYPE[parser_name.split(":")[0]] if parser_name.split(":")[0] in settings.DATA_STORE_TYPE else 'news',
                                                 "data": dict(item), "uid": html['uid'], "open_on": self.open_on}
                                    future = self.kafka_conn.send(settings.KAFKA_STORE_DATA_TOPIC,  # 傳到kafka(傳到kafka需為byte型態)
                                                                  bytes(json.dumps(send_data), encoding='utf8'))
                                    result = future.get(timeout=10)
                                    self.logger.info(result)
                                # step 7.
                                for url in return_data['next_urls']:
                                    add_request.add(url['url'], url['parser_name'], uid=html['uid'], level=1)
                                    self.logger.info("Add %s to Redis." % url)
                            else:
                                logging.error('Error in parse')
            # 無資料時休息5秒
            else:
                self.null_time += 1
                time.sleep(5)

    def stop(self):
        self.stop_flag = True

    def _socket_process(self):
        while 1:
            if self.stop_flag:
                break
            send_message = {"module": self.__class__.__name__,
                            "alive": 1,
                            "current_url": self.current_url['url'] if self.current_url is not None else None,
                            "current_web": self.current_url['parser_name'].split(":")[0] if self.current_url is not None else None,
                            }
            f = self.kafka_conn.send(settings.KAFKA_MODULE_STATUS_TOPIC,
                                     bytes(json.dumps(send_message), encoding='utf8'))
            result = f.get(timeout=10)
            self.logger.info("Send module status, topic={}, partition={}, offset={}".format(
                result.topic, result.partition, result.offset))
            time.sleep(10)


if __name__ == '__main__':
    HtmlProcessor().run()

