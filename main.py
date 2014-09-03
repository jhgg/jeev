import jeev

if __name__ == '__main__':
    try:
        import config
    except ImportError:
        config = object()

    jeev.run(config)
