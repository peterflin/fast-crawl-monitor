# coding: utf-8
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class CrawlState(Base):
    __tablename__ = 'crawl_states'

    states = Column(INTEGER(11), primary_key=True, nullable=False)
    spider = Column(String(50), nullable=False)
    domain = Column(String(50), nullable=False)
    url = Column(String(150), primary_key=True, nullable=False)
    tp = Column(DateTime, nullable=False, index=True)
    crawlid = Column(String(150), primary_key=True, nullable=False)
    state_comment = Column(String(1000))
    open_on = Column(String(50))


class JobUrl(Base):
    __tablename__ = 'job_url'

    url = Column(String(150), primary_key=True)
    parser_name = Column(String(50))
    enable = Column(TINYINT(4))


class News(Base):
    __tablename__ = 'news'

    title = Column(String(500))
    content = Column(Text)
    tp = Column(DateTime)
    url = Column(String(150), primary_key=True)
    author = Column(String(150))
    source = Column(String(50))
    uid = Column(String(50))


class ServerSignup(Base):
    __tablename__ = 'server_signup'

    server = Column(String(50), primary_key=True)
    join_time = Column(DateTime)
    connection_check = Column(DateTime)


class User(Base):
    __tablename__ = 'user'

    account = Column(String(20), primary_key=True)
    passwd = Column(String(20))
