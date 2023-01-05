from cacheout import CacheManager, LFUCache

l1cache: CacheManager = CacheManager(
    {
        'douban_media': {
            'maxsize': 100,
            'ttl': 86400
        },
        'media_image': {
            'maxsize': 1024,
            'ttl': 21600
        }
    },
    cache_class=LFUCache
)
