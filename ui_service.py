import argparse
import uuid
import logging
import time
import json
# import plotly
import traceback

from flask import Flask, render_template, request, flash, redirect, Markup, make_response
from flask_table import Table, Col, DatetimeCol
from flask_cors import CORS
from collections import deque
from threading import Thread

# from scutils.log_factory import LogFactory
from scutils.settings_wrapper import SettingsWrapper

# from rest_api import SCRestAPI

from kafka import KafkaConsumer
import pymysql
import sys
import redis
import add_request
import requests
import pkgutil
import inspect
import parsers
from scrapy.spiders import Spider


logging.basicConfig(format='%(asctime)s [%(name)-12s]: [%(levelname)s] : %(message)s', level=logging.INFO)
lg_fmt = logging.Formatter('%(asctime)s [%(name)-12s]: [%(levelname)s] : %(message)s')


class AdminUIService(object):

    # static strings
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    start_time = 0
    closed = False
    _initiate_stats_req_thread = None
    _states_thread = None
    _module_status_thread = None
    _service_status_thread = None
    _routine_thread = None
    _routine_running_state = True
    _signup_server = set()

    def __init__(self, settings_name):
        """
        @param settings_name: the local settings file name
        """
        self.settings_name = settings_name
        self.wrapper = SettingsWrapper()
        self.logger = None
        self.app = Flask(__name__)
        CORS(self.app)
        self.app.secret_key = 'some_secret12'
        self.my_uuid = str(uuid.uuid4()).split('-')[4]
        self.appid = Flask(__name__).name
        self.pollids_km = deque([])
        self.pollids_rm = deque([])
        self.pollids_c = deque([])
        self.stats = {}
        self.states = []
        self.error_stats = []
        self._module_status = {"UrlCollector": {"alive": 0, "receive_time": 0.0, "lambda_trigger": 0},
                               "HtmlProcessor": {"alive": 0, "receive_time": 0.0},
                               "kafka": {"alive": 0, "receive_time": 0.0},
                               "redis": {"alive": 0, "receive_time": 0.0}}
        self.state2code = {"init": 0, "request": 1, "parse": 2, "store": 3, "error": 4, "enqueue": 5, "dequeue": 6,
                           "drop": 7}
        self.code2state = {self.state2code[k]: k for k in self.state2code}
        self.urls_option = "<select name='url' class='form-control'></select>"
        self.url_list = {}
        self.routine_stop_flag = False
        self.modules = ["UrlCollector", "HtmlProcessor", "DataConsumer", "StatesConsumer"]
        self.job_index = {}

    def setup(self, level=None, log_file=None, json=None):
        """
        Load everything up. Note that any arg here will override both
        default and custom settings

        @param level: the log level
        @param log_file: boolean t/f whether to log to a file, else stdout
        @param json: boolean t/f whether to write the logs in json
        """
        self.settings = self.wrapper.load(self.settings_name)
        # eval("import {}.py".format(self.settings_name))
        # self.settings = eval(self.settings_name).wrapper

        # my_level = level if level else self.settings['LOG_LEVEL']
        # # negate because logger wants True for std out
        # my_output = not log_file if log_file else self.settings['LOG_STDOUT']
        # my_json = json if json else self.settings['LOG_JSON']
        self.logger = logging.getLogger(__class__.__name__)
        # self.logger.addFilter(ModuleFilter())

        self._decorate_routes()

        self._states_thread = Thread(target=self._states_from_db)
        self._states_thread.setDaemon(True)
        self._states_thread.start()
        time.sleep(5)
        self._module_status_thread = Thread(target=self._process_module_status)
        self._module_status_thread.setDaemon(True)
        self._module_status_thread.start()
        time.sleep(5)
        self._routine_thread = Thread(target=self.routine)
        self._routine_thread.setDaemon(True)
        self._routine_thread.start()

        self.start_time = self.get_time()

        # disable flask logger
        # if self.settings['FLASK_LOGGING_ENABLED'] == False:
        #     log = logging.getLogger('werkzeug')
        #     log.disabled = True

    def get_time(self):
        """Returns the current time"""
        return time.time()

    def run(self):
        """
        Main flask run loop
        """
        self.logger.info("Running main flask method on port " + str(self.settings['FLASK_PORT']))
        self.app.run(host='0.0.0.0', port=self.settings['FLASK_PORT'], debug=self.settings['DEBUG'])

    # Flask Table
    class ItemTable(Table):
        classes = ['table', 'table-striped']
        timestamp = DatetimeCol('timestamp')
        total_requests = Col('total_requests')

    class ErrorCountTable(Table):
        classes = ['table', 'col-md-12 col-lg-12']
        domain = Col("Parser", td_html_attrs={"class": "col-md-4 col-lg-3"})
        count = Col("Error Count", td_html_attrs={"class": "col-md-4 col-lg-3"})

    class StateTable(Table):
        classes = ['table', 'col-md-12 col-lg-12']
        crawlid = Col('Crawl ID', td_html_attrs={"class": "col-md-4 col-lg-3"})
        spider = Col('Parser', td_html_attrs={"class": "col-md-1 col-lg-1"})
        start_time = Col('Job Start Time', td_html_attrs={"class": "col-md-2 col-lg-2"})
        tp = Col('Time', td_html_attrs={"class": "col-md-2 col-lg-2"})
        url = Col('URL', td_html_attrs={"class": "col-md-3 col-lg-3"})
        st = Col('State', td_html_attrs={"class": "col-md-1 col-lg-1"})
        # state_message = Col('State Comment', td_html_attrs={"class": "col-md-4 col-lg-3"})

    class ListStateTable(Table):
        classes = ['table', 'col-md-12 col-lg-12']
        url = Col('URL', td_html_attrs={"class": "col-md-3 col-lg-3"})
        tp = Col('Time', td_html_attrs={"class": "col-md-2 col-lg-2"})
        st = Col('State', td_html_attrs={"class": "col-md-1 col-lg-1"})

    class ListUidTable(Table):
        classes = ['table', 'table-striped', 'uid']
        no = Col("", td_html_attrs={"class": "col-md-1 col-lg-1"})
        crawlid = Col('Crawl ID', td_html_attrs={"class": "col-md-7 col-lg-7"})
        timestamp = Col("Time", td_html_attrs={"class": "col-md-4 col-lg-4"})

    class JobURL(Table):
        classes = ['table', 'table-striped', 'col-md-12 col-lg-12']
        url = Col("URL", td_html_attrs={"class": "col-md-4 col-lg-4"})
        parser_name = Col("Parser", td_html_attrs={"class": "col-md-2 col-lg-2"})
        enable = Col("Enable", td_html_attrs={"class": "col-md-1 col-lg-1"})

    def _close_thread(self, thread, thread_name):
        """Closes daemon threads

        @param thread: the thread to close
        @param thread_name: a human readable name of the thread
        """
        if thread is not None and thread.isAlive():
            self.logger.debug("Waiting for {} thread to close".format(thread_name))
            thread.join(timeout=self.settings['DAEMON_THREAD_JOIN_TIMEOUT'])
            if thread.isAlive():
                self.logger.warn("{} daemon thread unable to be shutdown"
                                 " within timeout".format(thread_name))

    def close(self):
        """
        Cleans up anything from the process
        """
        self.logger.info("Trying to close UI Service")
        self.closed = True

        # self._close_thread(self._initiate_stats_req_thread, "Stats Loop")
        self.logger.info("Closed UI Service")

    def gen_uid(self):
        return str(uuid.uuid1())

    # 固定時間發布任務
    def routine(self):
        db = pymysql.connect(**self.settings['DB_SETTING'])
        cursor = db.cursor()
        c = 0
        while 1:
            if self._routine_running_state:
                if c % 5 == 0:
                    url_in = [u for u in self.url_list]
                    print(url_in)
                    all_parser = []
                    for importer, modname, ispkg in pkgutil.iter_modules(parsers.__path__, parsers.__name__ + "."):
                        module = __import__(modname, fromlist=["dummy"])
                        # print(module.__name__)
                        for i in inspect.getmembers(module):
                            try:
                                if hasattr(i[1], '__bases__'):
                                    if i[1].__bases__[0] == Spider:
                                        clss = getattr(module, i[0])
                                        all_parser.append(clss)
                            except:
                                print(traceback.format_exc())
                    for p in all_parser:
                        for url in p.start_urls:
                            cursor.execute("select url from job_url where url='{}'".format(url))
                            if not cursor.fetchone() and url not in url_in:
                                cursor.execute(
                                    "insert into job_url(url, parser_name, enable) values('{}','{}',1)".format(
                                        url, p.__name__
                                    ))
                                db.commit()
                                self.url_list[url] = p.__name__ + ":parse"
                    for url in self.url_list:
                        add_request.add(url.strip(), self.url_list[url].strip(), self.gen_uid())
                        time.sleep(1)
                time.sleep(60)
                c += 1
            else:
                time.sleep(3)
                c = 0

    # /run_routine 頁面
    def run_routine(self):
        # 固定時間發布任務
        # 點選State的start/stop按鈕，會有state參數
        # 如果現在是start, 會跑if == False, stop會跑elif == True，並重新導向

        # 開關服務上的模組
        # 點選Server的start/stop按鈕，會有switch,server, module參數
        # 根據switch參數，start會呼叫server的ModuleLauncher的start_module
        # stop則stop_module
        if request.form.get("state", None) is not None:
            if request.form.get("state", None) == 'False':
                self.routine_stop_flag = False
                self._routine_running_state = True
                redirect("/run_routine")
            elif request.form.get("state", None) == 'True':
                self._routine_running_state = False
                redirect("/run_routine")
        if request.form.get("module", None) is not None and request.form.get("server", None) is not None \
                and request.form.get("switch", None) == 'start':
            requests.get(request.form['server'] + "/start_module/" + request.form['module'])
            redirect("/run_routine")
        elif request.form.get("module", None) is not None and request.form.get("server", None) is not None \
                and request.form.get("switch", None) == 'stop':
            requests.get(request.form['server'] + "/stop_module/" + request.form['module'])
            redirect("/run_routine")
        if self._routine_running_state:
            running_state = Markup('<span class="label label-success">Running</span>')
            running = True
        else:
            running_state = Markup('<span class="label label-danger">Stop</span>')
            running = False
        server_list = {}
        for s in self._signup_server:
            server_list[s] = json.loads(requests.get(s + '/output').text)

        return render_template('run_routine.html', running_state=running_state, running=running,
                               signup=json.dumps(list(self._signup_server)), server_list=server_list)

    # def sign_up(self):
    #     server = request.form.get("server")
    #     if server is not None:
    #         self._signup_server.add(server)
    #         return "OK"
    #     else:
    #         return "Server is None."

    # Routes --------------------

    def _decorate_routes(self):
        """
        Decorates the routes to use within the flask app
        """
        self.logger.debug("Decorating routes")

        self.app.add_url_rule('/', 'index', self.index,
                              methods=['GET'])
        self.app.add_url_rule('/submit', 'submit', self.submit,
                              methods=['POST', 'GET'])
        self.app.add_url_rule('/crawl_states', 'crawl_states', self.crawl_states,
                              methods=['GET'])
        self.app.add_url_rule('/get_states_data', 'get_states_data', self.get_states_data,
                              methods=['GET'])
        self.app.add_url_rule('/get_states_list', 'get_states_list', self.get_states_list,
                              methods=['GET'])
        self.app.add_url_rule("/get/get_uid", 'get_uid', self.gen_uid,
                              methods=['GET'])
        self.app.add_url_rule("/run_routine", 'run_routine', self.run_routine,
                              methods=['POST', 'GET'])
        # self.app.add_url_rule("/signup", 'signup', self.sign_up,
        #                       methods=['POST'])
        self.app.add_url_rule("/get_module_server_states", 'get_module_server_states', self.get_module_server_states,
                              methods=['GET'])
        self.app.add_url_rule("/job_list", 'job_list', self.job_list,
                              methods=['GET', 'POST'])
        self.app.add_url_rule("/change_enable", 'change_enable', self.change_web_enable,
                              methods=['GET'])

    # index頁面
    def index(self):
        self.logger.info("'index' endpoint called")
        # r = self._rest_api.index()
        # if not 'status' in r: # we got a valid response from the index endpoint
        #     status = r
        # else:
        status = {
            "kafka_connected": False,
            "node_health": "RED",
            "redis_connected": False,
            "uptime_sec": 0
        }
        uid = uuid.uuid1()
        return render_template('index.html', status=status, url_list=Markup(self.urls_option), uid=uid)

    # 手動發布任務
    def submit(self):
        self.logger.info("'submit' endpoint called")
        # try:
        if request.method == 'POST':
            if not request.form['url']:
                self.logger.debug("request form does not have a url")
                flash('Submit failed')
                return redirect("/")
            else:
                self.logger.debug("generating submit request")
                data = {
                    "url": request.form['url'],
                    "crawlid": request.form["crawlid"],
                    # "maxdepth": int(request.form.get("depth", None)),
                    # "priority": int(request.form.get("priority", None)),
                    # "appid": "admin-ui",
                }
                r = add_request.add(data['url'], self.url_list[data['url']], data['crawlid'])
                # r = self._rest_api.feed(data=data)

                if self._module_status['UrlCollector']['alive'] != 1:
                    flash("Url Collector broken")
                elif self._module_status['HtmlProcessor']['alive'] != 1:
                    flash("Html Processor broken")
                elif r["status"] == "SUCCESS":
                    flash('You successfully submitted a crawl job')
                elif self._module_status['redis']['alive'] != 1:
                    flash("Redis broken.")
                elif self._module_status['kafka']['alive'] != 1:
                    flash("Kafka broken.")
                else:
                    flash('Submit failed')
                return redirect("/")
        else:
            self.logger.warn("Unsupported request method type", {
                                "method_type": request.method
                             })
            return make_response("error", 500)
        # except Exception:
        #     self.logger.error("Uncaught Exception", {
        #                         'ex': traceback.format_exc()
        #                       })
        #     return make_response("error", 500)

    # 無限迴圈，隔一段時間重新更新kafka、redis、各server上的模組狀態及製作top10錯誤列表
    def _states_from_db(self):
        # self.states = {"urls": {}}
        # try:
        state2code = self.state2code
        code2state = {state2code[k]: k for k in state2code}
        while 1:
            # update states data
            self.states = []
            db = pymysql.connect(**self.settings['DB_SETTING'])
            cursor = db.cursor()
            # parsers = [row[1] for row in data]
            sql = "SELECT crawlid FROM crawl_states where crawlid != '' or crawlid is not Null group by crawlid order by tp desc limit 5"
            cursor.execute(sql)
            data = cursor.fetchall()
            crawlid = [s[0] for s in data]
            for id in crawlid:
                sql = "SELECT * FROM crawl_states WHERE crawlid='{}' ORDER BY tp DESC".format(id)
                cursor.execute(sql)
                id_data = cursor.fetchall()
                row = id_data[0]
                start_time = str(id_data[-1][4])
                # print(sql, row[3])

                this_data = {"st": code2state[row[0]],
                             "spider": Markup("<a href='/get_states_list?parser=" + row[2] + "'>" + row[2] + "</a>"),
                             # "domain": row[2],
                             "start_time": start_time,
                             "tp": str(row[4]),
                             "url": Markup("<a href='" + row[3] + "' target='_blank'>" + row[3] + "</a>"),
                             "crawlid": Markup("<a href='/get_states_list?uid=" + row[5] + "'>" + row[5] + "</a>"), }
                             # "state_message": row[6]}
                self.states.append(this_data)

            self.error_stats = []
            sql = "select count(*), domain from crawl_states where states=4 and domain !='' group by domain order by count(*) desc limit 10"
            cursor.execute(sql)
            data = cursor.fetchall()
            for row in data:
                self.error_stats.append({"count": row[0], "domain": row[1]})
            cursor.close()
            db.close()

            # test redis
            try:
                r = redis.StrictRedis(host='127.0.0.1', port=6379, socket_timeout=3, password='redis@cia_0119')
                if r.ping():
                    self._module_status['redis']['receive_time'] = time.time()
                    self._module_status['redis']['alive'] = 1
            # if 'redis' not in self._module_status:
            #     self._module_status['redis'] = {}
            #     self._module_status['redis']['receive_time'] = time.time()
            #     self._module_status['redis']['alive'] = 1
            except:
                pass

            # test kafka
            try:
                conn = KafkaConsumer(bootstrap_servers=self.settings['KAFKA_BOOTSTRAP_SERVERS'])
                self._module_status['kafka']['receive_time'] = time.time()
                self._module_status['kafka']['alive'] = 1
            except:
                pass

            # get url data
            self.urls_option = "<select name='url' class='form-control'></select>"
            try:
                db = pymysql.connect(**self.settings['DB_SETTING'])
                cursor = db.cursor()
                cursor.execute("SELECT * FROM job_url")
                data = cursor.fetchall()
                self.url_list = {}
                self.urls_option = "<select name='url' class='form-control'>"
                for url in data:
                    if url[2] == 1:
                        self.url_list[url[0]] = url[1]
                    self.urls_option += "<option value='" + url[0] + "'>" + url[1].split(":")[0] + " : " + \
                                        url[0] + "</option>"
                self.urls_option += "</select>"
            except:
                self.urls_option = "<select name='url' class='form-control'></select>"
            print(self._module_status)
            time.sleep(3)

    # 取得有哪些server註冊、可使用
    def _process_module_status(self):
        while 1:
            db = pymysql.connect(**self.settings['DB_SETTING'])
            cursor = db.cursor()
            cursor.execute("select * from server_signup where connection_check > '{}'".format(
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 10))
            ))
            data = cursor.fetchall()
            self._signup_server = set({})
            for row in data:
                self._signup_server.add(row[0])
            cursor.close()
            db.close()
            time.sleep(10)

    # crawl_states頁面
    def crawl_states(self):
        self.logger.info("'crawl_states' endpoint called")
        # r = self._rest_api.index()
        # if not 'status' in r:  # we got a valid response from the index endpoint
        #     status = r
        # else:
        status = {
            "kafka_connected": False,
            "node_health": "RED",
            "redis_connected": False,
            "uptime_sec": 0
        }

        items = []
        state2code = {"init": 0, "request": 1, "parse": 2, "store": 3, "error": 4, "enqueue": 5, "dequeue": 6}
        code2state = {state2code[k]: k for k in state2code}
        table = self.StateTable(self.states)
        return render_template('crawl_states.html', status=status, table=table)

    # 回傳錯誤列表、各模組運形狀況、UI的其他thread運行狀況(是否停止)
    def get_states_data(self):
        # table = self.StateTable(self.states, no_items="Wait for loading.")
        table = self.ErrorCountTable(self.error_stats, no_items="Wait for loading.")
        for module in ['UrlCollector', 'HtmlProcessor', 'redis', 'kafka']:
            if module in self._module_status:
                if time.time() - self._module_status[module]['receive_time'] > 20:
                    self._module_status[module]['alive'] = 0
                    if module == 'UrlCollector':
                        self._module_status[module]['lambda_trigger'] = 0

        return json.dumps({"states": table.__html__(), "modules_status": self._module_status,
                           "update_process_state_thread": int(self._states_thread.is_alive()),
                           "update_module_state_thread": int(self._module_status_thread.is_alive())})

    # 取得已註冊的server運行狀況，並至做好html回傳
    def get_module_server_states(self):
        server_module_state = {}
        module_state_html = ""
        panel = lambda state: "success" if state == 'Running' else "danger"
        if len(self._signup_server) == 0:
            return '<div class="col-xs-8 col-sm-6 col-md-3 col-lg-3"><div class="panel panel-info"><div class="panel-heading"><h3 class="panel-title">UrlCollector</h3></div><div class="panel-body">No Server Available.</div></div></div><div class="col-xs-8 col-sm-6 col-md-3 col-lg-3"><div class="panel panel-info"><div class="panel-heading"><h3 class="panel-title">HtmlProcessor</h3></div><div class="panel-body">No Server Available.</div></div></div><div class="col-xs-8 col-sm-6 col-md-3 col-lg-3"><div class="panel panel-info"><div class="panel-heading"><h3 class="panel-title">DataConsumer</h3></div><div class="panel-body">No Server Available.</div></div></div><div class="col-xs-8 col-sm-6 col-md-3 col-lg-3"><div class="panel panel-info"><div class="panel-heading"><h3 class="panel-title">StatesConsumer</h3></div><div class="panel-body">No Server Available.</div></div></div>'
        for server in self._signup_server:
            try:
                modules_state = json.loads(requests.get(server + "/output").text)
            except requests.ConnectionError:
                # modules_state = dict([(m, "Not Running") for m, s in self.modules])
                pass
            else:
                for module in modules_state:
                    if module not in server_module_state:
                        server_module_state[module] = {}
                    server_module_state[module][server] = \
                        modules_state[module] if modules_state[module] is not None else "Not Running"
        for module in server_module_state:
            module_state_html += '<div class="col-xs-8 col-sm-6 col-md-3 col-lg-3"><div class="panel panel-info"><div class="panel-heading"><h3 class="panel-title">' + module + '</h3></div><div class="panel-body">'
            for server in server_module_state[module]:
                module_state_html += '<span class="label label-primary">' + server + ':<span class="label-' + panel(
                    server_module_state[module][server]) + '"> ' + server_module_state[module][
                                         server] + '</span></span>'
            module_state_html += '</div></div></div>'

        return module_state_html

    # get_states_data頁面
    # parser參數: 此網站的crawlid歷史列表
    # crawlid: 此crawlid的process state歷史
    def get_states_list(self):
        uid = request.args.get('uid')
        parser_name = request.args.get('parser')
        url = request.args.get("url")
        after = request.args.get('after')
        after = int(after) if after is not None else 0
        if parser_name is None and uid is not None and url is None:
            db = pymysql.connect(**self.settings['DB_SETTING'])
            cursor = db.cursor()
            # parsers = [row[1] for row in data]
            sql = "SELECT * FROM crawl_states where crawlid = '{}' order by tp desc limit 11 offset {}".format(
                uid, after)
            cursor.execute(sql)
            data = cursor.fetchall()
            uid_data = []
            button_enable = {"before": False if after == 0 else True,
                             "next": True if len(data) > 10 else False}
            for row in data:
                this_data = {"st": self.code2state[row[0]],
                             "url": Markup("<a href='" + row[3] + "' target='_blank'>" + row[3] +
                                           "</a> - <a href='/get_states_list?url=" + row[3] + "&uid=" + uid
                                           + "'>URL Info</a>"),
                             "tp": str(row[4])}
                             # "state_message": row[6]}
                uid_data.append(this_data)
            table = self.ListStateTable(uid_data)
            title = Markup("Web States: <b>" + uid + "</b> - <a href='/get_states_list?parser=" + data[0][2] + "'>"
                           + data[0][2] + "</a>, Start At: " + str(data[0][4]))
            return render_template('uid_list.html', table=table, title=title, btn_enable=button_enable)
        elif parser_name is not None and uid is None and url is None:
            self.logger.info("Get UID list.")
            db = pymysql.connect(**self.settings['DB_SETTING'])
            cursor = db.cursor()
            # parsers = [row[1] for row in data]
            sql = "SELECT tp, crawlid FROM crawl_states where domain = '{}'".format(parser_name)
            sql = sql + " group by crawlid order by tp desc  limit 11 offset {}".format(after)
            cursor.execute(sql)
            data = cursor.fetchall()
            uid_data = []
            count = after
            button_enable = {"before": False if after == 0 else True,
                             "next": True if len(data) > 10 else False}
            for row in data[:10]:
                this_data = {"no": count + 1,
                             "timestamp": row[0],
                             "crawlid": Markup("<a href='/get_states_list?uid=" + row[1] + "'>" + row[1] + "</a>")}
                uid_data.append(this_data)
                count += 1
            table = self.ListUidTable(uid_data)
            title = Markup("Web States History: <b>" + parser_name + "</b>")
            return render_template('uid_list.html', table=table, title=title, btn_enable=button_enable)
        elif url is not None and uid is not None:
            db = pymysql.connect(**self.settings['DB_SETTING'])
            cursor = db.cursor()
            # parsers = [row[1] for row in data]
            print(uid, url)
            sql = "SELECT * FROM crawl_states where crawlid = '{}' and url='{}' order by tp desc".format(uid, url)
            cursor.execute(sql)
            data = cursor.fetchall()
            uid_data = []
            button_enable = {"before": False if after == 0 else True,
                             "next": True if len(data) > 10 else False}
            for row in data:
                this_data = {"st": self.code2state[row[0]],
                             "url": Markup("<a href='" + row[3] + "' target='_blank'>" + row[3] +
                                           "</a> - <a href='/get_states_list?url=" + row[3] + "&uid=" + uid
                                           + "'>URL Info</a>"),
                             "tp": str(row[4])}
                # "state_message": row[6]}
                uid_data.append(this_data)
            table = self.ListStateTable(uid_data)
            title = Markup("Web States: <b><a href='/get_states_list?uid=" + uid + "'>" + uid
                           + "</a></b> - <a href='/get_states_list?parser=" + data[0][2] + "'>"
                           + data[0][2] + "</a>, Start At: " + str(data[0][4]))
            return render_template('uid_list.html', table=table, title=title, btn_enable=button_enable)

    # job_list頁面
    def job_list(self):
        db = pymysql.connect(**self.settings['DB_SETTING'])
        cursor = db.cursor()
        cursor.execute("select * from job_url")
        data = cursor.fetchall()
        job = []
        enable2str = lambda e: "True" if e == 1 else "False"
        button_color = lambda e: "primary" if e == 1 else "danger"
        self.job_index = {}
        index_count = 0
        form = "<form action='change_enable' method='GET'><input name='url' type='hidden' value='{url}'><input name='ori_state' type='hidden' value='{ori_state}'>{button}</form>"
        for row in data:
            job.append({'url': Markup("<a href='" + row[0] + "' target='_blank'>" + row[0] + "</a>"),
                        'parser_name': Markup("<a href='/get_states_list?parser=" + row[1].split(":")[0] + "'>"
                                              + row[1].split(":")[0] + "</a>"),
                        'enable': Markup(form.format(url=index_count, ori_state=row[2],
                                                     button="<button class='btn btn-" + button_color(row[2]) + "'>"
                                                            + enable2str(row[2]) + "</button>"))})
            self.job_index[index_count] = row[0]
            index_count += 1
        table = self.JobURL(job)
        return render_template("job_list.html", job_table=table)

    # job list上點選某網站，點選網站是否加入任務列表的開關，更新資料庫後，重新導向
    def change_web_enable(self):
        url = request.args.get("url")
        ori_state = request.args.get("ori_state")
        if url is not None and ori_state is not None:
            db = pymysql.connect(**self.settings['DB_SETTING'])
            cursor = db.cursor()
            if int(ori_state) == 1 and int(url) in self.job_index:
                cursor.execute("update job_url set enable=0 where url='{}'".format(self.job_index[int(url)]))
                db.commit()
            elif int(ori_state) == 0 and int(url) in self.job_index:
                cursor.execute("update job_url set enable=1 where url='{}'".format(self.job_index[int(url)]))
                db.commit()
            db.close()
            cursor.close()
            return redirect('/job_list')
        else:
            return redirect('/job_list')


class ModuleFilter(logging.Filter):

    def filter(self, record):
        print('-----------{}-----------'.format(record.name))
        record.name = "FFFF"
        if record.name != 'kafka.conn':
            return True
        else:
            return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Admin UI Service\n')

    parser.add_argument('-s', '--settings', action='store',
                        required=False,
                        help="The settings file to read from",
                        default="localsettings.py")
    parser.add_argument('-ll', '--log-level', action='store',
                        required=False, help="The log level",
                        default=None,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                 'CRITICAL'])
    parser.add_argument('-lf', '--log-file', action='store_const',
                        required=False, const=True, default=None,
                        help='Log the output to the file specified in '
                        'settings.py. Otherwise logs to stdout')
    parser.add_argument('-lj', '--log-json', action='store_const',
                        required=False, const=True, default=None,
                        help="Log the data in JSON format")

    args = vars(parser.parse_args())
    ui_service = AdminUIService(args['settings'])
    ui_service.setup(level=args['log_level'], log_file=args['log_file'], json=args['log_json'])

    try:
        ui_service.run()
    finally:
        ui_service.close()
