# -*- coding: utf-8 -*-

"""
forecaster.core.view.tele
~~~~~~~~~~~~~~

This module provides telegram integration.
"""

import telegram
from telegram import Bot
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler
from telegram.ext.filters import Filters
from forecaster.glob import CURR
from forecaster.core.view.glob import OmniViewer, DefaultViewer
from telegram.error import TimedOut

# logging
import logging
logger = logging.getLogger('forecaster.view.tele')


class TeleViewer(DefaultViewer):
    """telegram handler"""
    def __init__(self, supervisor):
        super().__init__(supervisor)
        self.token = OmniViewer().security['telegram-token']
        self.bot = Bot(token=self.token)
        self.updater = Updater(token=self.token)
        self.dispatcher = self.updater.dispatcher
        logger.debug("telegram viewer initiated")

    def listen(self):
        """listen every connections"""
        handlers = []  # append every command
        handlers.append(ConversationHandler(
            entry_points=[CommandHandler('config', self.cmd_config)],
            states={'username_key':
                    [MessageHandler(Filters.text, self.username_key, pass_chat_data=True)],
                    'password_key':
                    [MessageHandler(Filters.text, self.password_key, pass_chat_data=True)]},
            fallbacks=[CommandHandler('cancel', ConversationHandler.END)]))
        handlers.append(CommandHandler('predict', self.cmd_predict))
        handlers.append(CommandHandler('start', self.cmd_start))
        handlers.append(CommandHandler('stop', self.cmd_stop))
        handlers.append(CommandHandler('restart', self.cmd_restart))
        for hand in handlers:
            self.dispatcher.add_handler(hand)
        self.updater.start_polling()  # listen connections

    def cmd_start(self, bot, update):
        logger.debug("start command caught")
        self.chat_id = update.message.chat_id
        update.message.reply_text("Starting...")
        self.notify_observers('start-bot')
        update.message.reply_text("Bot started")

    def cmd_stop(self, bot, update):
        logger.debug("stop command caught")
        update.message.reply_text("Stopping...")
        self.notify_observers('stop-bot')
        update.message.reply_text("Bot stopped")

    def cmd_restart(self, bot, update):
        logger.debug("restart command caught")
        update.message.reply_text("Restarting...")
        self.notify_observers('stop-bot')
        self.notify_observers('start-bot')
        update.message.reply_text("Bot restarted")

    def cmd_config(self, bot, update):
        logger.debug("config command caught")
        update.message.reply_text("Bot configuration. This is for logging in coinbase.")
        update.message.reply_text("Please insert your Trading212 username")
        return 'username_key'

    def cmd_predict(self, bot, update):
        logger.debug("predict command caught")
        update.message.reply_text("Predicting trend...")
        self.notify_observers('predict')

    def username_key(self, bot, update, chat_data):
        chat_data['username'] = update.message.text
        OmniViewer().pers_data['username'] = chat_data['username']
        update.message.reply_text("Please insert password")
        return 'password_key'

    def password_key(self, bot, update, chat_data):
        chat_data['password'] = update.message.text
        OmniViewer().pers_data['password'] = chat_data['password']
        logger.debug("%s" % OmniViewer().pers_data)
        OmniViewer().collection['PERS_DATA'].save()
        update.message.reply_text("Configuration saved")
        return ConversationHandler.END

    def config_needed(self):
        logger.debug("configuration needed")
        self.bot.send_message(chat_id=self.chat_id, text="Configuration needed to continue")
        raise

    def out_pred(self, pred_dict):
        logger.debug("prediction processed")
        text = "Prediction:"
        text += "\nTiming: 10 hours"
        for curr in pred_dict:
            text += '\n_%s_ - *%.3f*' % (curr['name'], curr['value'])
        self.bot.send_message(chat_id=self.chat_id, text=text,
                              parse_mode=telegram.ParseMode.MARKDOWN)

    def new_pos(self, name, margin):
        logger.debug("new_position telegram")
        text = "Opened position *%s*\nMargin: *%.2f*" % (name, margin)
        self.bot.send_message(chat_id=self.chat_id, text=text,
                              parse_mode=telegram.ParseMode.MARKDOWN)

    def close_pos(self, result):
        logger.debug("close_position telegram")
        text = "Closed position with gain of *%.2f*" % result
        self.bot.send_message(chat_id=self.chat_id, text=text,
                              parse_mode=telegram.ParseMode.MARKDOWN)

    def renew_connection(self):
        try:
            self.bot.getChat(chat_id=self.chat_id, timeout=5)  # get chat info to renew connection
        except TimedOut as e:
            logger.error("Telegram timed out, renewing")
        logger.debug("renewed connection")


# # Create a button menu to show in Telegram messages
# def build_menu(buttons, n_cols=1, header_buttons=None, footer_buttons=None):
#     menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
#
#     if header_buttons:
#         menu.insert(0, header_buttons)
#     if footer_buttons:
#         menu.append(footer_buttons)
#
#     return menu
#
#
# # Custom keyboards
# def keyboard_confirm():
#     buttons = [
#         KeyboardButton("YES"),
#         KeyboardButton("NO")
#     ]
#
#     return ReplyKeyboardMarkup(build_menu(buttons, n_cols=2))