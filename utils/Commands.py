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


def GV(connect, mess=None):
    version = '#GVRLLh151Cs047m'
    logger(sys._getframe().f_code.co_name, locals())
    Write(version + ACK, connect)


# def GC(connect, mess=None):
#     logger(sys._getframe().f_code.co_name, locals())
#     values = []
#     for i in range(10):
#         values.append(f"{randint(7000, 10001):05d}")
#     channels = f"#GC{US.join(values)}{ACK}"
#     Write(channels, connect)


# def SC(connect, mess=None):
#     """4.4.1
#             '$ SCddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddUSdddddENQHEXHEX'
#             'HEX HEX'      - CRC16,
#             'dd'           - время действия для режима выполнения суточного графика (#GM10) (1...99 сек),
#             'ddddd'        - значение яркости в канале (0 - максимум, 10000 – выключен).
#         4.4.2 Ответы:
#             'DONE HEX HEX' - значение установлено;
#             'FAIL HEX HEX' - ошибка формата;
#             'NAK HEX HEX'  - ошибка приема."""
#     Write(DONE, connect)
#     logger(sys._getframe().f_code.co_name, locals())
#     if mess:
#         print(mess)
#         mess = byteToStr(mess)
#         channels = mess[mess.index('SC') + 5:mess.index(ENQ)].split(US)
#         channels = [(10000 - int(i)) / 100 for i in channels if len(i)]
#         for i in range(len(channels)):
#             print(f'{i + 1}. {"#"*int(channels[i])} {channels[i]}')


class Time(object):
    """docstring for Time"""

    def __init__(self):
        super(Time, self).__init__()
        self.deltaTime = 0

    def timeInSeconds(self):
        struct = time.localtime(time.time() + self.deltaTime)
        inSec = struct.tm_hour * 60 * 60 + struct.tm_min * 60 + struct.tm_sec
        return inSec

    def getTime(self, connect, mess=None):
        print(self.deltaTime)
        if self.deltaTime is not None:
            tStruct = time.localtime(time.time() + self.deltaTime)
            tm = time.strftime('#GT%H%M%d0%w%m%y', tStruct)
            logger("GT", locals())
            Write(tm + ACK, connect)
        else:
            tm = time.strftime('#GT%H%M%d0%w%m%y')
            logger("GT", locals())
            Write(tm + ACK, connect)

    def setTime(self, connect, mess=None):
        data = byteToStr(mess[3:-3]) if b'$ST' in mess else None
        print(mess, data)
        if not data:
            return
        tStruct = time.struct_time((
            int('20' + data[-2:]),
            int(data[-4:-2]),
            int(data[4:6]),
            int(data[:2]),
            int(data[2:4]),
            0, 0, 0, 0))
        self.deltaTime = time.mktime(tStruct) - time.time()
        logger("ST", locals())
        Write(DONE, connect)


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


class State(object):

    def __init__(self):
        super(State, self).__init__()

    def getTemperature(self, mess, connect):
        Write(f"#GA0505{ACK}", connect)
        logger(sys._getframe().f_code.co_name, locals())

    def getFan(self, mess, connect):
        Write(f"#GS{randint(0,9999):04d}{ACK}", connect)
        logger(sys._getframe().f_code.co_name, locals())

    def getClockCalibration(self, mess, connect):
        Write(f"#GL1000{ACK}", connect)
        logger(sys._getframe().f_code.co_name, locals())

    def getPWMDivider(self, mess, connect):
        Write(f"#GP{randint(0,65535):05d}{ACK}", connect)
        logger(sys._getframe().f_code.co_name, locals())


class dc(Mode, Time, State):
    """class - daily cycle object, functionary emulation of GH, SC, GC and cycle write command"""

    def __init__(self):
        super(dc, self).__init__()
        self.HASH = ('06', '60218')
        self.cycle = None
        self.channels = [10000] * 10

    def timeToTwoPoints(self, timeInMin):
        for i in self.cycle:
            if i[-1] >= timeInMin:
                return self.cycle[self.cycle.index(i) - 1], i

    def calcChannels(self, cycle, tm):
        tmInMin = self.timeInSeconds() / 60
        points = [i for i in zip(*self.timeToTwoPoints(tmInMin))
                  ] if len(self.cycle) > 2 else [i for i in zip(*self.cycle)]
        print(points)
        pointsChannels, pointsTimes = points[:-1], points[-1]
        if pointsTimes[0] < tmInMin < pointsTimes[1]:
            delta = pointsTimes[1] - pointsTimes[0] if pointsTimes[1] < 1440 else (
                1440 - pointsTimes[1]) + pointsTimes[0]  # in min
        else:
            delta = 1440 - abs(pointsTimes[1] - pointsTimes[0])
        channels = []
        for couple in pointsChannels:
            couple = [10000 - i for i in couple]
            # base = couple[0] if couple[0] <= couple[1] else couple[1]
            # if l[1] < l[0]:
            #     l = l[::-1]
            k = (couple[1] - couple[0]) / delta if couple[0] != couple[1] else 0
            channels.append((int(couple[0] + (k * (tmInMin - pointsTimes[0])))))
            print(f"l = {couple}, k = {k}, delta = {delta}, point = {channels[-1]}")
        return channels

    def setChannels(self, mess, connect):
        mess = byteToStr(mess)
        self.channels = [10000 - int(i) for i in mess[mess.index('SC') + 5:mess.index(ENQ)].split(US)]
        Write(DONE, connect)

    def getChannels(self, mess, connect):
        if self.cycle:
            timeNow = time.time() + self.deltaTime
            self.channels = self.calcChannels(self.cycle, timeNow)
            # Write(f"#GC{US.join(channels)}{ACK}", connect)
        print(self.channels)
        if self.mode == 20:
            Write(f"#GC{US.join([f'{10000-n:05d}' for n in self.channels])}{ACK}", connect)
        else:
            Write(f"#GC{US.join([f'{n:05d}' for n in self.channels])}{ACK}", connect)

    def HashCalc(self, cycle=None):
        if not cycle:
            return self.HASH
        HexCycle = to8bytes(self.cycle)
        CycleCRC = cycleCRC(HexCycle)
        result = (f"{len(self.cycle):02d}", f"{CycleCRC:05d}")
        loc = dict(locals())
        logger(sys._getframe().f_code.co_name, loc)
        return result

    def setHash(self, hs: tuple):
        self.HASH = hs

    def returnHASH(self, mess, connect):
        result = f'#GH{self.HASH[0]}{US}{self.HASH[1]}{ACK}'
        Write(result, connect)
