from cachetools import Cache, TTLCache

class TTLItemCache(TTLCache):
    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__, ttl=None):
        super(TTLItemCache, self).__setitem__(key, value)
        if ttl:
            link = self._TTLCache__links.get(key, None)
            if link:
                link.expires += ttl - self.ttl


cache = TTLItemCache(maxsize=4096, ttl=10)

cache.__setitem__('key1', 'val1')
cache.__setitem__('key2', 'val2', ttl=60)

while True:
	key = input('Key: ')
	# try:
	if key in cache:
		print(cache[key])
	else:
		print('not in cache')
	# except Exception as e:
	# 	print(e)

