'''
Created on 29.12.2010

@author: mark
'''
import io
import builtins as exceptions
import sys
import traceback

class SockIOException(exceptions.Exception):
    
    def __init__(self):
        return

class SockIOData:

    typeString=1
    typeNumber=2
    typeCommand=3
    typeBinary=4
    typeLongDirect=64
    
        

    

class SockWrite(SockIOData):
    '''
    classdocs
    '''
    def __init__(self):
        pass

    
    def writeString(self, key, value, byteIO):
        byteIO.write(SockIOData.typeString.to_bytes(1, byteorder='big', signed=False))
        self.__writeRawBytes(key.encode('UTF-8'), byteIO)
        self.__writeRawBytes(value.encode('UTF-8'), byteIO)
    
    def __writeRawBytes(self, bytes, byteIO):
        length=len(bytes)
        hiByte=abs(int(length / 256))
        loByte=length % 256
        byteIO.write(hiByte.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(loByte.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(bytes)
        
    def writeLongDirect(self, value, byteIO):
        byteIO.write(SockIOData.typeLongDirect.to_bytes(1, byteorder='big', signed=False))
        byte0=abs(int(value / 16777216))
        value=value % 16777216
        byte1=abs(int(value / 65536))
        value=value % 65536
        byte2=abs(int(value / 256))
        byte3=value % 256
        byteIO.write(byte0.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte1.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte2.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte3.to_bytes(1, byteorder='big', signed=False))

        
    def writeBinaryDirect(self, value, byteIO):
        byteIO.write(value)
        
    def writeBinary(self, key, value, byteIO):
        byteIO.write(SockIOData.typeBinary.to_bytes(1, byteorder='big', signed=False))
        self.__writeRawBytes(key.encode('UTF-8'), byteIO)
        ln=len(value)
        byte0=abs(int(ln / 16777216))
        ln=ln % 16777216
        byte1=abs(int(ln / 65536))
        ln=ln % 65536
        byte2=abs(int(ln / 256))
        byte3=ln % 256
        byteIO.write(byte0.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte1.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte2.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte3.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(value)
        
    def writeLong(self, key, value, byteIO):
        byteIO.write(SockIOData.typeNumber.to_bytes(1, byteorder='big', signed=False))
        self.__writeRawBytes(key.encode('UTF-8'), byteIO)
        byte0=abs(int(value / 16777216))
        value=value % 16777216
        byte1=abs(int(value / 65536))
        value=value % 65536
        byte2=abs(int(value / 256))
        byte3=value % 256
        byteIO.write(byte0.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte1.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte2.to_bytes(1, byteorder='big', signed=False))
        byteIO.write(byte3.to_bytes(1, byteorder='big', signed=False))
        
        
class SockRead(SockIOData):
    
    
    ###
    # Returns a tuple
    # dataType, key, value
    def read(self, byteIO):
        typ = int.from_bytes(byteIO.read(1), byteorder='big', signed=False)
        if typ == 0:
            raise SockIOException
        key, value = { SockIOData.typeString : lambda : (self.__readRawBytes(byteIO), self.__readRawBytes(byteIO)),
                       SockIOData.typeNumber : lambda : (self.__readRawBytes(byteIO), self.__readRawLong(byteIO)),
                       SockIOData.typeBinary : lambda : (self.__readRawBytes(byteIO), self.__readRawBinary(byteIO)),
                       SockIOData.typeLongDirect : lambda : ( "", self.__readRawLong(byteIO))
                      } [typ]()
        return (typ, key, value)
    
    
    def __readRawBytes(self, byteIO):
        length = int.from_bytes(byteIO.read(2), byteorder='big', signed=False)
        return byteIO.read(length).decode('UTF-8')

    def __readRawLong(self, byteIO):
        return int.from_bytes(byteIO.read(4), byteorder='big', signed=False)

    def __readRawBinary(self, byteIO):
        length=self.__readRawLong(byteIO)
        return byteIO.read(length)


    
class ReadDictionary:
    
    def __init__(self):
        pass
    
    def read(self, data):
        d={}
        sockRd=SockRead()
        buf=io.BytesIO(data)
        try:
            while True:                            
                _, key, value=sockRd.read(buf)
                d[key]=value
        except SockIOException:
            pass
        buf.close()
        return d

class WriteDictionary:
    
    def write(self, data):
        sockWt=SockWrite()
        buf=io.BytesIO()
        for k in data.keys():
            if type(data[k]) is int:
                sockWt.writeLong(k, data[k], buf)
            elif type(data[k]) is str:
                sockWt.writeString(k, data[k], buf)
            elif type(data[k] is dict):
                sockWt.writeBinary(k, WriteDictionary().write(data[k]), buf)
        return buf.getvalue()
            
        

def formatExceptionInfo(log, maxTBlevel=5):
    cla, exc, trbk = sys.exc_info()
    excName = cla.__name__
    try:
        excArgs = exc.__dict__["args"]
    except KeyError:
        excArgs = "<no args>"
    excTb = traceback.format_tb(trbk, maxTBlevel)
    log.debug(excName)
    log.debug(excArgs)
    log.debug(excTb)
    
 
FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])

def dump(src, length=8):
    N=0; result=''
    while src:
        s,src = src[:length],src[length:]
        hexa = ' '.join(["%02X"%ord(x) for x in s])
        s = s.translate(FILTER)
        result += "%04X   %-*s   %s\n" % (N, length*3, hexa, s)
        N+=length
    return result
       
    