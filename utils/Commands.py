# by blues

import time
import sys
from utils.SerialUtils import *
from utils.Protocol import *
from random import randint


def HoursToMin(tm: str):
    return f"{(int(tm[:2]) * 60) + int(tm[2:]):04d}"


def Write(mess: str, connect):
    connect.write(
        crcAdd(mess))


def GL(connect, mess=None):
    logger(sys._getframe().f_code.co_name, locals())
    Write(f"#GL000{ACK}", connect)


def GT(connect, mess=None):
    tm = time.strftime('#GT%H%M%d0%w%m%y')
    logger(sys._getframe().f_code.co_name, locals())
    Write(tm + ACK, connect)


def GV(connect, mess=None):
    version = '#GVRLLh151Cs047m'
    logger(sys._getframe().f_code.co_name, locals())
    Write(version + ACK, connect)


def GC(connect, mess=None):
    logger(sys._getframe().f_code.co_name, locals())
    values = []
    for i in range(10):
        values.append(f"{randint(7000, 10001):05d}")
    channels = f"#GC{US.join(values)}{ACK}"
    Write(channels, connect)


# def SM(connect, mess=None):
#     logger(sys._getframe().f_code.co_name, locals())
#     Write(DONE, connect)


def SC(connect, mess=None):
    """4.4.1
            '$ SCddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddENQHEXHEX'
            'HEX HEX'      - CRC16,
            'dd'           - время действия для режима выполнения суточного графика (#GM10) (1...99 сек),
            'ddddd'        - значение яркости в канале (0 - максимум, 10000 – выключен).
        4.4.2 Ответы:
            'DONE HEX HEX' - значение установлено;
            'FAIL HEX HEX' - ошибка формата;
            'NAK HEX HEX'  - ошибка приема."""
    Write(DONE, connect)
    logger(sys._getframe().f_code.co_name, locals())
    if mess:
        mess = byteToStr(mess)
        channels = mess[mess.index('05') + 3:mess.index(ENQ)].split(US)
        channels = [(10000 - int(i)) / 100 for i in channels if len(i)]
        for i in range(len(channels)):
            print(f'{i + 1}. {"#"*int(channels[i])} {channels[i]}')


class Mode(object):
    """docstring for Mode"""

    def __init__(self):
        super(Mode, self).__init__()
        self.mode = '10'

    def getMode(self, mess, connect):
        Write(f"#GM{self.mode}{ACK}", connect)
        logger(sys._getframe().f_code.co_name, locals())

    def setMode(self, mess, connect):
        mess = byteToStr(mess)
        mode = int(mess[mess.index('SM') + 2])
        self.mode = f'{mode}0'
        logger(sys._getframe().f_code.co_name, locals())
        Write(DONE, connect)


class dc(object):
    """docstring for dc"""

    def __init__(self):
        super(dc, self).__init__()
        self.HASH = ('06', '60218')
        self.cycle = None
        # print(self.cycle)

    def HashCalc(self, cycle=None):
        if not cycle:
            return self.HASH
        HexCycle = to8bytes(self.cycle)
        CycleCRC = cycleCRC(HexCycle)
        result = (f"{len(self.cycle):02d}", f"{CycleCRC:05d}")
        loc = dict(locals())
        logger(sys._getframe().f_code.co_name, loc)
        return result

    def setHash(self, hs):
        self.HASH = hs

    def returnHASH(self):
        return self.HASH


class gh(dc):
    """docstring for GH"""

    def __init__(self):
        super(gh, self).__init__()

    def returnHash(self, **kwargs):
        loc = dict(locals())
        logger(sys._getframe().f_code.co_name, loc)
        connect = kwargs['connect']
        result = f'#GH{self.returnHASH()[0]}{US}{self.returnHASH()[1]}{ACK}'
        print(result)
        Write(result, connect)
