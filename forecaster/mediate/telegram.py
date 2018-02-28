#!/usr/bin/env python

"""
forecaster.mediate.telegram
~~~~~~~~~~~~~~

Handle telegram requests and interface with the service.
"""
import logging

import telegram
from telegram import Bot
from telegram.error import TimedOut
from telegram.ext import (CommandHandler, ConversationHandler, MessageHandler,
                          Updater)
from telegram.ext.filters import Filters

from forecaster.handler import Client
from forecaster.utils import EVENTS, Chainer, get_yaml, save_yaml

logger = logging.getLogger('forecaster.mediate.telegram')


class TelegramMediator(Chainer):
    """telegram interface"""

    def __init__(self, token, successor=None):
        super().__init__(successor)
        self.bot = Bot(token=token)
        self.updater = Updater(token=token)
        self.dispatcher = self.updater.dispatcher

    def handle_request(self, event):
        self.pass_request(event)

    def activate(self):
        """list connections"""
        handlers = []  # append every command
        handlers.append(ConversationHandler(
            entry_points=[CommandHandler('config', self.cmd_config)],
            states={'username_key':
                    [MessageHandler(Filters.text, self.username_key, pass_chat_data=True)],
                    'password_key':
                    [MessageHandler(Filters.text, self.password_key, pass_chat_data=True)]},
            fallbacks=[CommandHandler('cancel', ConversationHandler.END)]))
        handlers.append(CommandHandler('results', self.cmd_results))
        handlers.append(CommandHandler('valued', self.cmd_valued))
        handlers.append(CommandHandler('start', self.cmd_start))
        handlers.append(CommandHandler('stop', self.cmd_stop))
        handlers.append(CommandHandler('restart', self.cmd_restart))
        for hand in handlers:
            self.dispatcher.add_handler(hand)
        self.updater.start_polling()  # listen connections
        logger.debug("Telegram listening")

    def deactivate(self):
        self.updater.stop()

    def cmd_start(self, bot, update):
        logger.debug("start command caught")
        self.chat_id = update.message.chat_id
        update.message.reply_text("Starting...")
        self.handle_request(EVENTS.START_BOT)
        update.message.reply_text("Bot started")

    def cmd_stop(self, bot, update):
        logger.debug("stop command caught")
        self.renew_connection()
        update.message.reply_text("Stopping...")
        self.handle_request(EVENTS.STOP_BOT)
        update.message.reply_text("Bot stopped")

    def cmd_restart(self, bot, update):
        logger.debug("restart command caught")
        self.renew_connection()
        update.message.reply_text("Restarting...")
        self.handle_request(EVENTS.STOP_BOT)
        self.handle_request(EVENTS.START_BOT)
        update.message.reply_text("Bot restarted")

    def cmd_config(self, bot, update):
        logger.debug("config command caught")
        update.message.reply_text("Bot configuration. This is for logging in trading212.")
        update.message.reply_text("Please insert your Trading212 username")
        return 'username_key'

    def username_key(self, bot, update, chat_data):
        chat_data['username'] = update.message.text
        self.credentials = {}
        self.credentials['username'] = chat_data['username']
        update.message.reply_text("Please insert password")
        return 'password_key'

    def password_key(self, bot, update, chat_data):
        chat_data['password'] = update.message.text
        self.credentials['password'] = chat_data['password']
        logger.debug("%s" % self.credentials)
        save_yaml(self.credentials, get_yaml('data'))
        del self.credentials
        update.message.reply_text("Configuration saved")
        return ConversationHandler.END

    def cmd_results(self, bot, update):
        logger.debug("results command caught")
        self.renew_connection()
        text = "Actual results are *%.2f*" % Client().RESULTS
        self.bot.send_message(chat_id=self.chat_id, text=text,
                              parse_mode=telegram.ParseMode.MARKDOWN)

    def cmd_valued(self, bot, update):
        logger.debug("valued command caught")
        self.renew_connection()
        Client().refresh()
        result = Client().api.account.funds['result']
        num_pos = len(Client().api.account.positions)
        text = "Actual value is *%.2f* with *%d* positions" % (result, num_pos)
        self.bot.send_message(chat_id=self.chat_id, text=text,
                              parse_mode=telegram.ParseMode.MARKDOWN)

    def config_needed(self):
        logger.debug("configuration needed")
        self.bot.send_message(chat_id=self.chat_id, text="Configuration needed to continue")
        raise

    def close_pos(self, result):
        logger.debug("close_position telegram")
        self.renew_connection()
        text = "Closed position with gain of *%.2f*" % result
        logger.debug("closed position - revenue of %.2f" % result)
        self.bot.send_message(chat_id=self.chat_id, text=text,
                              parse_mode=telegram.ParseMode.MARKDOWN)

    def renew_connection(self):
        timeout = 5
        while timeout > 0:
            try:
                # get chat info to renew connection
                self.bot.getChat(chat_id=self.chat_id, timeout=1)
                return
            except TimedOut as e:
                logger.error("Telegram timed out, renewing")
                timeout -= 1
        logger.debug("renewed connection")
