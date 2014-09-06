import logging
import jeev

if __name__ == '__main__':
    import coloredlogs
    coloredlogs.install(level=logging.DEBUG)
    try:
        import config
    except ImportError:
        config = object()

    jeev.run(config)
