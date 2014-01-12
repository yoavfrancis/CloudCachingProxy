__author__ = 'Yoav Francis and Tomer Cagan'

import os
import logging

from hybrid_cache import HybridCache

CACHING_RESOURCES =  ["jpg", "gif", "jpeg", "png"]
CACHE_HOST_LIST = '/home/ubuntu/cache.config'

class ProxyCachingLogic:
    """
    Proxy caching logic implementation over the HybridCache
    """

    def __init__(self):
        self.cache = HybridCache(open(CACHE_HOST_LIST, 'r').readlines())

    def get(self, host_address, resource_path):
        """
        Getter function
        """
        if not os.path.splitext(resource_path)[1][1:] in CACHING_RESOURCES:
            return None

        key = "/".join([host_address, resource_path])
        print "Looking for {0}".format(key)

        data = self.cache.get(key)
        if data is None:
            logging.debug("Cache miss")
        else:
            logging.debug("Cache miss")

        return data

    def set(self, host_address, resource_path, data):
        """
        Setter function
        """
        if not os.path.splitext(resource_path)[1][1:] in CACHING_RESOURCES:
            logging.debug("Resource is not in caching policy")
            return False

        key = "/".join([host_address, resource_path])

        if data is None:
            logging.warn("Key: {0} attempt to put None data".format(key))
            return False


        self.cache.add(key, data, 300)
        logging.debug("Added {0} to cache".format(key))
        return True




