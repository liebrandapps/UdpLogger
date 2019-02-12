import base64
import os
import shutil
import threading
from zipfile import ZipFile, ZIP_DEFLATED

from Crypto.Cipher import AES

from myio.liebrand.udplogger.Utility import ReadDictionary


class LogWriter(threading.Thread):

    DEFAULT = "default"
    ZIP = ".zip"
    ENVELOPE = "envelope"

    def __init__(self, instance, ctx):
        threading.Thread.__init__(self)
        self._terminate = False
        self.instance = instance if instance is not None else LogWriter.DEFAULT
        self.log = ctx.log
        self.logQueue = []
        self.wakeup = threading.Event()
        if instance is None:
            self.logFilename = ctx.cfg.general_defaultLog
            self.logRotate = ctx.cfg.general_logRotate
            self.logMaxSize = ctx.cfg.general_logMaxSize
            self.logHistory = ctx.cfg.general_logHistory
            self.logZipHistory = ctx.cfg.general_logZipHistory
            self.logHistoryDir = ctx.cfg.general_logHistoryDir
            self.logFormat = ctx.cfg.general_logFormat
            self.AESKey = ctx.cfg.general_AESKey
            self.encrypted = not (self.AESKey is None or len(self.AESKey) == 0)


    def log(self, app, when, uid, severity, message):
        dct = {
            'app': app,
            'when': when,
            'uid': uid,
            'severity': severity,
            'message': message
        }
        self.logDict(dct)

    def logDict(self, dct):
        if LogWriter.ENVELOPE in dct and not self.encrypted:
            self.log.error("Received encrypted log message from client %s without AES key configured. Cannot log message." % dct['ip'])
            return
        if LogWriter.ENVELOPE not in dct:
            self.logQueue.append(dct)
            self.wakeup.set()
            return
        cipher = AES.new(self.AESKey, AES.MODE_ECB)
        decoded = base64.b64decode(dct[LogWriter.ENVELOPE])
        decrypted = cipher.decrypt(decoded)
        data = decrypted[: -decrypted[len(decrypted) - 1]]
        newDct = ReadDictionary().read(data)
        self.logQueue.append(newDct)
        self.wakeup.set()

    def terminate(self):
        self._terminate = True
        self.wakeup.set()

    def run(self):
        self.log.info("Starting udp logger %s" % self.instance)
        fileSize = 0
        if self.logRotate and os.path.exists(self.logFilename):
            fileSize = os.stat(self.logFilename).st_size
        while not self._terminate:
            while len(self.logQueue)>0:
                dct = self.logQueue.pop(0)

                message = self.logFormat % dct
                message += '\n'
                with open(self.logFilename, 'a') as f:
                    f.write(message)

                msgLen = len(message)
                fileSize += msgLen
                if self.logRotate and fileSize>self.logMaxSize:
                    self.archiveLog()
                    fileSize = 0

            self.wakeup.wait(300)
            self.wakeup.clear()
        self.log.info("Stopping udp logger %s" % self.instance)


    def archiveLog(self):
        logFilename = os.path.basename(self.logFilename)
        if not os.path.exists(self.logHistoryDir):
            os.mkdir(self.logHistoryDir)
        # start w/o zip history
        if self.logZipHistory>0:
            # move archives up by 1
            prevFileName = ""
            for idx in range(self.logZipHistory, 0, -1):
                zipFileName = os.path.join(self.logHistoryDir, logFilename + "." + str(idx) + LogWriter.ZIP)
                if idx < self.logZipHistory and os.path.exists(zipFileName):
                    os.rename(zipFileName, prevFileName)
                prevFileName = zipFileName

            # add first zip file
            fileName = os.path.join(self.logHistoryDir, logFilename + "." + str(self.logHistory))
            if os.path.exists(fileName):
                with ZipFile(zipFileName, 'w') as zf:
                    zf.write(fileName, compress_type=ZIP_DEFLATED)

        # move non archived by 1
        prevFileName = ""
        for idx in range(self.logHistory, 0, -1):
            fileName = os.path.join(self.logHistoryDir, logFilename + "." + str(idx))
            if idx < self.logHistory and os.path.exists(fileName):
                os.rename(fileName, prevFileName)
            prevFileName = fileName

        if os.path.exists(self.logFilename):
            shutil.move(self.logFilename, fileName)

        open(self.logFilename, 'a').close()
