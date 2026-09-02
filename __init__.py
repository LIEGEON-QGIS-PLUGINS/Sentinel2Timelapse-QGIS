def classFactory(iface):
    from .sentinel_time import SentinelPlugin
    return SentinelPlugin(iface)