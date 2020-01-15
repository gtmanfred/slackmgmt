try:
    import pkg_resources
    HAS_PKG_RESOURCES = True
except ImportError:  # pragma: no cover
    HAS_PKG_RESOURCES = False
    __version__ = ''
else:
    try:
        __version__ = pkg_resources.get_distribution('irc3').version
    except pkg_resources.DistributionNotFound:
        __version__ = ''

__name__ = 'slackmgmt'
