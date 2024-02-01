from flask_table import Table, Col, DatetimeCol


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