__author__ = 'Yoav Francis and Tomer Cagan'

from werkzeug.contrib.cache import MemcachedCache, SimpleCache

class HybridCache(object):
    """
    A hybrid cache class that provide in-process cache that is backup up by out-of-process cache
    When setting a key it will set it in both in-process and out-of-process
    When getting a key it will try to retrieve first from in-process and if not, from out-of-process
    """

    def __init__(self, remote_addresses):
        self.in_proc_cache = SimpleCache(1000, 3600)    #todo - pass these are arguments
        self.remote_addresses = remote_addresses
        self.out_proc_cache = MemcachedCache(remote_addresses)

    def get(self, key):
        """
        get an item from the hybrid cache
        first in the in-process and then in the out-of-process
        in case the key does not exist in both return None
        if the value exist in out of process but not in-process then it is added
        """
        val = self.in_proc_cache.get(key)

        if val is None:
            val = MemcachedCache(self.remote_addresses).get(key)
            if val is not None:
                self.in_proc_cache.add(key, val, None)  #todo: for how long to cache?

        return val

    def add(self, key, value, timeout = 300):
        """
        store a key-value in the hybrid cache - both in and out-off process
        """
        #self.out_proc_cache.add(key, value, timeout = timeout)
        MemcachedCache(self.remote_addresses).add(key, value, timeout)
        self.in_proc_cache.add(key, value, timeout = timeout)


if __name__ == "main":
    pass
#TODO - tests
