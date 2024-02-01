import redis


class RedisModel:

    def __init__(self):
        self.redis = redis.StrictRedis(host='127.0.0.1', port=6379, socket_timeout=3, password='redis@cia_0119')

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

