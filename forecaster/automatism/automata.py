# -*- coding: utf-8 -*-

"""
forecaster.automatism.automata
~~~~~~~~~~~~~~

This is the main module for automatism.
"""

import time
from threading import Thread, Event
from forecaster.glob import Configurer, get_path
from forecaster.patterns import Subject
from forecaster.automatism.handler import Handler
from forecaster.exceptions import MissingConfig
from trading212api.exceptions import *

# logging
import logging
logger = logging.getLogger('forecaster.automatism.automata')


class Automata(Subject):
    """responsible for making automatism work"""
    def __init__(self, ultracontroller):
        super().__init__()
        self.attach(ultracontroller)
        self.ultra = ultracontroller  # bound to bot
        self.omni = ultracontroller.omni
        self.model = ultracontroller.model
        self.conf = Configurer(get_path('automatism.yml'))
        self.conf.read()  # read strategy variables
        self.handler = Handler(ultracontroller.controller)
        self.ACTIVE = Event()  # init the leading event
        self.OPEN = Event()  # init the postion presence event
        logger.debug("automata initied")

    def start(self):
        """start automatism"""
        self.ACTIVE.set()  # start the event automatism
        logger.debug("automata started")
        main_logger = logging.getLogger('forecaster')
        log_level = main_logger.level
        # suppress debug messages
        main_logger.setLevel(logging.WARNING)
        self.model.pred_all()  # instance the model
        main_logger.setLevel(log_level)
        self.start_cycle()

    def stop(self):
        self.ACTIVE.clear()
        self.OPEN.clear()
        logger.debug("automata stopped")

    def start_cycle(self):
        Thread(target=self.keep_open).start()
        Thread(target=self.work).start()
        logger.debug("cycles started")

    def keep_open(self):
        """keep open session"""
        while self.ACTIVE.is_set():
            try:
                username = self.omni().pers_data['username']
                password = self.omni().pers_data['password']
            except KeyError:
                raise MissingConfig
            try:  # catch unathorized access
                self.handler.client.login(username, password)
            except RequestError as e:
                if e.status != 401:
                    raise
            self.ultra.view.renew()  # renew connection
            logger.debug("keep session live")
            self._sleep(60*10, self.ACTIVE)

    def work(self):
        """main cycle"""
        self._sleep(self.handler.time_left_to_update(), self.ACTIVE)  # first launch
        while self.ACTIVE.is_set():
            self.work_open()
            time_left = self.handler.time_left_to_update()
            self._sleep(time_left, self.ACTIVE)
            self.work_close()

    def work_open(self):
        """cycle for opening new transactions"""
        logger.debug("working open")
        predictions = self.model.pred_all()  # get the predictions
        margin_risk = self.conf.config['margin-risk']
        approved = []  # init approved
        for prediction in predictions:
            mode = self.check(prediction['value'])  # get the mode
            if mode is None:  # if check not respected ignore it
                continue
            else:  # append to approved
                approved.append([prediction, mode])
        self.handler.client.refresh()
        free_funds = self.handler.client.account.funds['free']
        margin_per_pred = margin_risk*free_funds/len(approved)
        for prediction in approved:
            mode = prediction[1]
            prod = prediction[0]['name']+'_ZERO'
            # make an auto transaction, quantity will be calculated in handler (ZERO SPREAD)
            try:
                res = self.handler.transaction(mode, prod, margin_per_pred)
            except ProductNotAvaible as e:
                logger.warning("Product %s not avaible" % prod)
                continue
            self.notify_observers(  # notify viewers
                event="open", data={'name': prod, 'margin': res['margin']})
            logger.info("completed %s transaction %d of %s with margin of %s " % (
                mode, res['quantity'], prod, res['margin']))
            self.OPEN.set()

    def work_close(self):
        """cycle for closing old transactions"""
        logger.debug("working close")
        if not self.OPEN.is_set():
            logger.debug("OPEN passed")
            return
        for position in self.handler.client.account.positions:
            self.handler.client.close_position(position.id)
            self.notify_observers(event="close", data={'res': position.result})
            logger.info("position %s closed" % position.id)
        self.OPEN.clear()

    def check(self, pred):
        """check if prediction margin is respected"""
        margin = self.conf.config['maximum-model-margin']
        if pred > 1-margin:
            return 'buy'
        elif pred < 0+margin:
            return 'sell'
        else:
            return None

    def _sleep(self, t, event):
        """sleep check"""
        start = time.time()
        while time.time() < start + t and event.is_set():
            time.sleep(1)
        if not event.is_set():
            return False
        else:
            return True
