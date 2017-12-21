import sys
import time
from bitgen.bot import Bot

# logging
import logging
logger = logging.getLogger('bitgen.test')


def main():
    logging.getLogger('bitgen').setLevel(logging.DEBUG)
    bot = Bot()
    bot.start()
    logger.debug("bot launched")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.stderr.write('\r' + "exiting...\n")
        bot.view.tele.updater.stop()
        logger.debug("exited")


if __name__ == '__main__':
    main()
