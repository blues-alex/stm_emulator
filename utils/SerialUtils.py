# by blues


import time
import serial


def logger(name: str, loc: dict):
    tm = time.strftime("[ %d.%m %H:%M:%S ]")
    relult = [f"    {i} = {loc[i]}" for i in loc if type(loc[i]) in [dict, list, int, float, str]]
    print(tm)
    for n in relult:
        print(n)


def to8bytes(cycle):
    '''значения из матрицы cycle переводятся в 16и битное число байты которого развернуты.
        вся матрица складывается в строку hex значений и преобразуется в байты,
        Принимает список списков по 10 значений int от 0 до 10000 + int время в минутах от начала суток'''

    result = b''
    for p in cycle:
        for b in p:
            n = f"{b:04x}"
            n = n[-2:] + n[:-2]
            # из строки с hex значениями в строку байт
            result += bytes.fromhex(n)
    return result


def CRC16(mess):
    poly = 0x1021
    Init = 0xffff
    # xor = 0x0001
    crc = Init
    for b in mess:
        crc ^= (ord(b) << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ poly
            else:
                crc = (crc << 1)
    Hex = '%04x' % (crc & Init)
    return crcToBytes(Hex)


def cycleCRC(b):
    ''' подсчет значения CRC суточного цикла'''
    poly = 0x1021
    Init = 0xffff
    crc = Init
    for i in range(len(b)):
        crc ^= (b[i] << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ poly
            else:
                crc = (crc << 1)
    CRC = (crc & Init)
    return CRC


def crcToBytes(mess):
    return bytes.fromhex(mess[:2]) + bytes.fromhex(mess[2:])


def crcAdd(mess):
    return bytes(mess, 'ascii') + CRC16(mess)


def byteToStr(mess):
    return mess.decode('ascii', 'replace')


def checkData(data):
    if len(data):
        result = {}
        if data[0] == 35:
            result['answer'] = data[1:3]
            data, crc = data[:-2], data[-2:]
            if CRC16(byteToStr(data)) == crc:
                result['mess'] = data[3:-1]
                result['check'] = True
        else:
            result['answer'] = ''
            data, crc = data[:-2], data[-2:]
            if CRC16(byteToStr(data)) == crc:
                result['mess'] = data
                result['check'] = True
            else:
                result['mess'] = data
                result['check'] = False
    else:
        result = False
    return result


class Connection(object):
    """docstring for Connection"""

    def __init__(self, port=None):
        super(Connection, self).__init__()
        self.port = port if port else '/dev/ttyUSB0'
        self.TIMEOUT = 1

        self.sr = serial.Serial(self.port)
        self.sr.timeout = self.TIMEOUT

        def writeMessage(self, mess):
            result = b''
            self.sr.write(mess)
            timeout = time.time()
            data = False
            while time.time() - timeout <= self.TIMEOUT:
                result += self.sr.read(1)
                if len(result) >= 3:
                    try:
                        if result[-3] in [21, 19, 7]:
                            print(f'Break reading: controller return {byteToStr(result)}')
                            data = False
                            break
                    except Exception:
                        pass
                    if result[-3] in [6, 18]:
                        data = checkData(result)
                        break
                    else:
                        continue
            return data

        def SendMessage(self, mess):
            mess = crcAdd(mess)
            return writeMessage(mess)
