import os
import config
import jeev

if __name__ == '__main__':
    try:
        jeev.run(config)

    except KeyboardInterrupt:
        os._exit(0)