import base64
import datetime
import io
import socket
import sys
import time
import uuid

from Crypto.Cipher import AES

from myio.liebrand.udplogger.Utility import WriteDictionary, SockWrite

bs = 16

def _pad(s):
    x = io.BytesIO()
    x.write(s)
    b = bs - len(s) % bs
    for i in range(0, b):
        x.write(b.to_bytes(1, byteorder='big', signed=False))
    return x.getvalue()


def encrypt(cipher, raw):
        raw = _pad(raw)
        encrypted = cipher.encrypt(raw)
        encoded = base64.b64encode(encrypted)
        return str(encoded, 'utf-8')

if __name__ == '__main__':

    ip = sys.argv[1]
    port = sys.argv[2]
    if len(sys.argv)>3:
        key = 'dAFGQfI8X1yvzLtTwo2A9axmJSpW17ul'
    else:
        key = 'LOLLIPOPLOLLIPOP'
    print(key)
    cipher = AES.new(key, AES.MODE_ECB)

    dct = {
        'app': 'sample',
        'uid': str(uuid.uuid4()),
        'when': str(datetime.datetime.now()),
        'severity': 'info',
        'message': 'sample message'
    }
    cnt = 1
    sequence = 1
    writeDct = WriteDictionary()
    sockWt = SockWrite()
    for idx in range(cnt):
        dct['sequence'] = sequence
        data = writeDct.write(dct)
        dct = {
            'envelope' : encrypt(cipher, data)
        }
        data = writeDct.write(dct)
        sequence += 1

        ctlBuffer = io.BytesIO()
        sockWt.writeLongDirect(len(data), ctlBuffer)
        sockWt.writeBinaryDirect(data, ctlBuffer)
        dta = ctlBuffer.getvalue()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print ("Message send to %s:%d" % (ip, int(port)))
        sock.sendto(dta, (ip, int(port)))
        sock.close()
        time.sleep(0.05)
