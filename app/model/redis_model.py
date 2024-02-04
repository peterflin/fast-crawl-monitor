import redis
from config import REDIS_HOST, REDIS_PORT, REDIS_PWD


class RedisModel:

    def __init__(self):
        self.redis = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, socket_timeout=3, password=REDIS_PWD)
    
    def __del__(self):
        self.redis.close()

    @property
    def error_stat(self):
        errors = []
        error_keys = self.redis.lrange("error_state_key", 0, -1)
        for key in error_keys:
            stored_data = self.redis.hgetall(key.decode('utf8'))
            loaded_data = {key.decode('utf-8'): value.decode('utf-8') for key, value in stored_data.items()}
            errors.append(loaded_data)
        return errors
    
    @property
    def crawl_states(self):
        states_keys = self.redis.lrange("crawl_state_key", 0, -1)
        states = []
        for key in states_keys:
            stored_data = self.redis.hgetall(key.decode("utf8"))
            loaded_data = {key.decode('utf-8'): value.decode('utf-8') for key, value in stored_data.items()}
            states.append(loaded_data)
        return states

    @property
    def states_data(self):
        data = {}
        data["kafka"] = {k.decode("utf8"): v.decode("utf8") for k, v in self.redis.hgetall("module_state_kafka").items()}
        data["redis"] = {k.decode("utf8"): v.decode("utf8") for k, v in self.redis.hgetall("module_state_redis").items()}
        return data
    
    @property
    def signup_servers(self):
        return [e.decode("utf8") for e in self.redis.lrange("signup_server", 0, -1)]

