import io
import errno
import os
import select
import signal
import sys
import time
import socket


from myio.liebrand.udplogger.Context import Context
from myio.liebrand.udplogger.LogWriter import LogWriter
from myio.liebrand.udplogger.Utility import SockRead, ReadDictionary


class Daemon:

    def __init__(self, pidFile):
        self.pidFile = pidFile

    def getTimeStamp(self):
        return time.strftime('%d.%m.%Y %H:%M:%S',  time.localtime(time.time()))

    def printLogLine(self, file, message):
        file.write('%s %s\n' % (self.getTimeStamp(), message))
        file.flush()

    def startstop(self, todo, stdout="/dev/null", stderr=None, stdin="/dev/null"):
        try:
            pf = open(self.pidFile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if 'stop' == todo or 'restart' == todo:
            if not pid:
                msg = "[UDPL] Could not stop. Pidfile %s is missing\n"
                self.printLogLine(sys.stderr, msg % self.pidFile)
                sys.exit(1)
            self.printLogLine(sys.stdout, "Stopping Process with PID %d" % pid);
            try:
                cnt = 10
                while 1:
                    if cnt < 0:
                        os.kill(pid, signal.SIGKILL)
                    else:
                        os.kill(pid, signal.SIGTERM)
                    time.sleep(3)
                    cnt -= 1
                self.printLogLine("[UDPL] Server refuses to terminate ...")
            except OSError as err:
                err = str(err)
                if err.find("No such process") > 0:
                    if "stop" == todo:
                        if os.path.exists(self.pidFile):
                            os.remove(self.pidFile)
                        sys.exit(0)
                    todo = "start"
                    pid = None
                else:
                    print (str(err))
                    sys.exit(1)
        if 'start' == todo:
            if pid:
                msg = "[UDPL] Start aborted since Pidfile %s exists\n"
                self.printLogLine(sys.stderr, msg % self.pidFile)
                sys.exit(1)
            self.printLogLine(sys.stdout, "Starting Process as Daemon");
            self.daemonize(stdout, stderr, stdin)
        if 'status' == todo:
            if pid:
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    with process.oneshot():
                        msg = "[UDPL] Process with pid %d is running [%s]" % (pid, process.name())
                        self.printLogLine(sys.stdout, msg);
                        sys.exit(0)
                else:
                    msg = "[UDPL] Process with pid %d is NOT running, but we have a PID file - may it crashed." % (pid,)
                    self.printLogLine(sys.stdout, msg)
                    if os.path.exists(self.pidFile):
                        os.remove(self.pidFile)
                        sys.exit(3)
            else:
                msg = "[UDPL] Process seems to be not running - no PIDFile (%s) found."
                self.printLogLine(sys.stderr, msg % self.pidFile)
                sys.exit(0)


    def daemonize(self, stdout='/dev/null', stderr=None, stdin='/dev/null'):
        if not stderr:
            stderr = stdout
        si = open(stdin, 'r')
        so = open(stdout, 'a+')
        se = open(stderr, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("[UDPL] fork #1 failed (%d) %s" % (e.errno, e.strerror))
            sys.exit(1)

        os.umask(0)
        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("[UDPL] fork #2 failed (%d) %s" % (e.errno, e.strerror))
            sys.exit(1)
        pid = str(os.getpid())
        self.printLogLine(sys.stdout, "[UDPL] Process started as Daemon with pid %s" % pid)
        if self.pidFile:
            open(self.pidFile, 'w+').write('%s\n' % pid)

class LogServer:

    LOGGERID = "loggerId"
    IP = "ip"

    def __init__(self, ctx):
        self.ctx = ctx
        self.log = ctx.log
        self.listenPort = ctx.cfg.general_listenPort
        self._terminate = False
        self.controlPipe = os.pipe()


    def terminate(self, sigNo, stackFrame):
        if sigNo==signal.SIGINT:
            self.log.info("[UDPL] Terminating upon Keyboard Interrupt")
        if sigNo==signal.SIGTERM:
            self.log.info("[UDPL] Terminating upon Signal Term")
        self._terminate=True
        os.write(self.controlPipe[1], bytes(1))
        self._terminate = True

    def serve(self):
        self.log.info("Starting UdpLogger")
        signal.signal(signal.SIGTERM, self.terminate)
        signal.signal(signal.SIGINT, self.terminate)
        sockRd = SockRead()
        rdDict = ReadDictionary()
        socketArray = [self.controlPipe[0], ]
        defLogWriter = LogWriter(None, self.ctx)
        defLogWriter.start()
        logWriters = {}

        while not self._terminate:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('', self.listenPort))
                socketArray.append(sock)
                while not self._terminate:
                    try:
                        ready = select.select(socketArray, [], [], 300)
                        if ready[0]:
                            for r in ready[0]:
                                if r == self.controlPipe:
                                    os.read(self.controlPipe[0], 1)
                                    continue
                                if r == sock:
                                    udpData, address = r.recvfrom(1536)
                                    buffer = io.BytesIO(udpData[0:5])
                                    _,_,length = sockRd.read(buffer)
                                    if length<1536:
                                        fields = rdDict.read(udpData[5:])
                                        fields[LogServer.IP]=str(address)
                                        if LogServer.LOGGERID in fields and fields[LogServer.LOGGERID] in logWriters:
                                            logWriters[LogServer.LOGGERID].logDict(fields)
                                        else:
                                            defLogWriter.logDict(fields)

                    except socket.error as e:
                        if e.errno == errno.EINTR:
                            pass

                sock.close()
            except socket.error as e:
                if e.errno == errno.EINTR:
                    pass
                if e.errno == errno.EADDRINUSE:
                    self.log.error("Unable to listen on port %d - already in use" % (self.listenPort))
                else:
                    self.log.error("Unable to listen on port %d - Error %d %s" % (
                    self.listenPort, e.errno, errno.errorcode[e.errno]))
                self._terminate = True
                continue
        defLogWriter.terminate()
        self.log.info("Stopping UdpLogger")

if __name__ == '__main__':
    logFile = "./udpLogger.log"
    cfgDict = {
        'general': {
            'enableLogging': ['Boolean', "yes"],
            "logFileName": ["String", logFile],
            "maxFilesize": ["Integer", 1000000],
            "msgFormat": ["String", "%(asctime)s, %(levelname)s, %(module)s {%(process)d}, %(lineno)d, %(message)s"],
            "logLevel": ['Integer', 10],
            'listenPort' : ['Integer', 8765],
            'defaultLog' : ['String', "./remote.log"],
            'logRotate' : ['Boolean', True],
            'logMaxSize' : ['Integer', 10000],
            'logHistory' : ['Integer', 5],
            'logZipHistory': ['Integer', 10],
            'logHistoryDir' : ['String', './archive'],
            'logFormat': ['String', '%(when)s, %(app)s, %(uid)s, %(sequence)d,  %(severity)s, %(message)s'],
            'AESKey': ['String', 'LOLLIPOPLOLLIPOP' ]
        }
    }
    if len(sys.argv) > 1:
        todo = sys.argv[1]
        if todo in [ 'start', 'stop', 'restart', 'status' ]:
            pidFile = "/tmp/udpLogger.pid"
            logFile = logFile
            d = Daemon(pidFile)
            d.startstop(todo, stdout=logFile, stderr=logFile)
    ctx = Context('./udpLogger.ini', cfgDict, 'UDPLogger')
    status = ctx.getStatus()
    if not(status[0] and status[1]):
        sys.exit(-1)

    LogServer(ctx).serve()
