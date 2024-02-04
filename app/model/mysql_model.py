from utils.sql_helper import create_session
from utils.sql_models import JobUrl


class MySQLModel:

    def __init__(self):
        self.db = create_session()
    
    def __del__(self):
        self.db.close()

    @property
    def job_url_data(self):
        data = self.db.query(JobUrl).all()
        return data

