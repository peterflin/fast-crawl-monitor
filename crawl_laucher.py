import sys
sys.path.append("/home/peterdump/crawl")
import argparse
import uuid
import logging
import time
import json
import traceback

from flask import Flask, render_template, request, Markup
from flask_table import Table, Col, DatetimeCol
from threading import Thread
import pymysql
import add_request, url_collector, crawler, data_consumer, state_consumer
from multiprocessing import Process
import settings


logging.basicConfig(format='%(asctime)s [%(name)-12s]: [%(levelname)s] : %(message)s', level=logging.INFO)


class ModuleLaunchService(object):
    singup_update = None

    def __init__(self):
        self.logger = logging.getLogger(__class__.__name__)
        self.app = Flask(__name__)
        self.app.secret_key = 'some_secret12'
        self.my_uuid = str(uuid.uuid4()).split('-')[4]
        self.appid = Flask(__name__).name
        self._decorate_routes()
        self._host = "http://127.0.0.1:5051"
        self.port = 5051
        self.process_manager = {"UrlCollector": None, "HtmlProcessor": None,
                                "DataConsumer": None, "StatesConsumer": None}
        self.process_object = {}

        self.signup_update = Thread(target=self._signup)
        self.signup_update.setDaemon(True)
        self.signup_update.start()

    def run(self):
        self.logger.info("Running main flask method on port " + str(self.port))
        self.app.run(host='0.0.0.0', port=self.port, debug='INFO')

    def close(self):
        """
        Cleans up anything from the process
        """
        self.logger.info("Trying to close UI Service")
        self.closed = True

        # self._close_thread(self._initiate_stats_req_thread, "Stats Loop")
        self.logger.info("Closed UI Service")

    # Routes --------------------

    def _decorate_routes(self):
        """
        Decorates the routes to use within the flask app
        """
        self.logger.debug("Decorating routes")

        self.app.add_url_rule('/', 'index', self.index,
                              methods=['GET'])
        self.app.add_url_rule("/output", 'output', self.output, methods=['GET'])
        self.app.add_url_rule("/start_module/<module_name>", 'start', self.start_module, methods=['GET'])
        self.app.add_url_rule("/stop_module/<module_name>", 'stop', self.stop_module, methods=['GET'])
        self.app.add_url_rule('/reset', 'reset', self.reset, methods=['GET'])

    def index(self):
        self.logger.info("'index' endpoint called")
        module_name = request.args.get("module")
        return "OK"

    def start_module(self, module_name):
        if module_name is None or module_name == "":
            return self.output()
        if self.process_manager[module_name] is not None:
            if self.process_manager[module_name].is_alive():
                return self.output()
            # else:
            #     process = Thread(target=self.run_module, args=(module_name,))
            #     process.daemon = True
            #     self.process_manager[module_name] = process
            #     process.start()
            #     return self.output()
        if module_name is not None and module_name in self.process_manager:
            process = Thread(target=self.run_module, args=(module_name,))
            process.daemon = True
            self.process_manager[module_name] = process
            process.start()
        return self.output()

    def stop_module(self, module_name):
        if module_name is None or module_name == "":
            return self.output()
        if module_name in self.process_object:
            self.process_object[module_name].stop()
            return self.output()
        else:
            return self.output()

    def output(self):
        output_data = {}
        return json.dumps(self.process_manager, cls=AdJSONEncoder)

    def run_module(self, module):
        module_list = ['url_collector', 'crawler', 'data_consumer', 'state_consumer']
        module_class = None
        if module is not None:
            for m in module_list:
                try:
                    module_class = getattr(eval(m), module)
                    break
                except:
                    pass
        print(module_class)
        mc = module_class(open_on=self._host)
        self.process_object[module] = mc
        mc.run()

    def _signup(self):
        while 1:
            try:
                # self.signup_result = requests.post('http://140.128.102.159:5050/signup',
                #                                    data={"server": "http://140.128.102.159:5051"})
                # self.logger.info(self.signup_result.text)

                db = pymysql.connect(**settings.DB_SETTING)
                cursor = db.cursor()
                cursor.execute("select * from server_signup where server='{}'".format(self._host))
                data = cursor.fetchall()
                if len(data) == 0:
                    cursor.execute("insert into server_signup(server, join_time, connection_check) values('{}', '{}', '{}')".format(
                        self._host, time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(time.time())),
                        time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(time.time()))
                    ))
                    db.commit()
                else:
                    cursor.execute("update server_signup set connection_check='{}'".format(
                        time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(time.time()))))
                    db.commit()
                cursor.close()
                db.close()
                time.sleep(10)
            except:
                self.logger.error(traceback.format_exc())
                self.logger.info("Sign up connection error.")
                time.sleep(10)

    def reset(self):
        for module in self.process_object:
            self.process_object[module].stop()
            while 1:
                if not self.process_manager[module].is_alive():
                    break
            process = Thread(target=self.run_module, args=(module,))
            process.daemon = True
            self.process_manager[module] = process
            process.start()
        # flag = False
        # while 1:
        #     if flag:
        #         break
        #     for module in self.process_manager:
        #         if not self.process_manager[module].is_alive():
        #             flag = True
        #         else:
        #             flag = False
        #             break
        # for module_name in self.process_manager:
        #     process = Thread(target=self.run_module, args=(module_name,))
        #     process.daemon = True
        #     self.process_manager[module_name] = process
        #     process.start()
        return self.output()


class AdJSONEncoder(json.JSONEncoder):
    def default(self, o):
        out = lambda state: "success" if state == 'Running' else "danger"
        if isinstance(o, Process):
            r = "Running" if o.is_alive() else "Stop"
            return r
        if isinstance(o, Thread):
            r = "Running" if o.is_alive() else "Stop"
            # r = o.name
            return r
        return json.JSONEncoder.default(self, o)


if __name__ == '__main__':

    launcher = ModuleLaunchService()

    try:
        launcher.run()
    finally:
        launcher.close()
    # print(getattr(eval("url_collector"), "UrlCollector"))
