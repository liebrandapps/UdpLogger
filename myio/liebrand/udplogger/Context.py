import sys
import logging
import time
import builtins as exceptions
from datetime import datetime
from logging.handlers import RotatingFileHandler
from os.path import join, exists, dirname, isdir
from os import access, W_OK, R_OK

from myio.liebrand.udplogger.Config import Config


class Context:

    CONFIG_DIR = "./"

    def __init__(self, configFile, initialConfig, loggerName):
        self.cfgOk = False
        self.logOk = False
        path = join(Context.CONFIG_DIR, configFile)
        self.log = None
        if not (exists(path)):
            self.printLogLine(sys.stderr,
                              "[CTX] No config file %s found at %s - assuming defaults" % (configFile, Context.CONFIG_DIR))
        self.cfgOk = True
        self.cfg = Config(path)
        self.cfg.addScope(initialConfig)
        self.logOk = self.setupLogger(loggerName)
        self.threadMonitor = {}
        self.lastThreadCheck = None

    def getStatus(self):
        return [self.cfgOk, self.logOk]

    def getTimeStamp(self):
        return time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(time.time()))

    def printLogLine(self, fl, message):
        fl.write('%s %s\n' % (self.getTimeStamp(), message))
        fl.flush()

    def setupLogger(self, loggerName):
        try:
            self.log = logging.Logger(loggerName)
            self.loghdl = RotatingFileHandler(self.cfg.general_logFileName, 'a', self.cfg.general_maxFilesize, 4)
            #self.loghdl = logging.FileHandler(cfg.logFileName)
            self.loghdl.setFormatter(logging.Formatter(self.cfg.general_msgFormat))
            self.loghdl.setLevel(self.cfg.general_logLevel)
            self.log.addHandler(self.loghdl)
            self.log.disabled = False
            self.initialLogLevel = self.cfg.general_logLevel
            self.debugLevel = False
            return True
        except exceptions.Exception as e:
            self.printLogLine(sys.stderr, "[CTX] Unable to initialize logging. Reason: %s" % e)
            return False


    def checkThreads(self, now):
        if self.lastThreadCheck is None or (now - self.lastThreadCheck).seconds>300:
            self.lastThreadCheck = now
            for k in self.threadMonitor:
                if (now - self.threadMonitor[k]).seconds>900:
                    # thread has not updated since 15 minutes
                    self.log.warn("[CTX] Thread for class %s has not sent an alive message for %d seconds" %
                                  (k, ((now - self.threadMonitor[k]).seconds)))

