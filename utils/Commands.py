# by blues

import time
import os
from utils.SerialUtils import *
from utils.Protocol import *
from random import randint
from loguru import logger


if not os.path.isdir('./logs'):
    os.mkdir('./logs')

logger.add(
    "./logs/stmEmulator.log",
    format="{level}\t{time:YY-MM-DD HH:mm:ss.ms}\t{message}",
    rotation="1 MB",
    compression="tar.gz"
)

ModeTimer = 1.5 * 60  # min * 60


def HoursToMin(tm: str):
    return f"{(int(tm[:2]) * 60) + int(tm[2:]):04d}"


@logger.catch
def Write(mess: str, connect):
    connect.write(crcAdd(mess))


def GL(connect, mess=None):
    Write(f"#GL000{ACK}", connect)
    logger.success("[GL]: 000")


def GV(connect, mess=None):
    string_version = '#GVRLLh151Cs053b'
    # version = '#GVRLLh151Cs047m'
    Write(string_version + ACK, connect)
    logger.success(f"[GV]: {string_version}")


class Time:
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
            Write(tm + ACK, connect)
            logger.success(f"[GT]: {tm} - {time.strftime('%d.%m.%Y %H:%M', tStruct)}")
        else:
            tm = time.strftime('#GT%H%M%d0%w%m%y')
            Write(tm + ACK, connect)
            logger.success(f"[GT]: {tm} - {time.strftime('%d.%m.%Y %H:%M', tStruct)}")

    def setTime(self, connect, mess=None):
        data = byteToStr(mess[3:-3]) if b'$ST' in mess else None
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
        Write(DONE, connect)
        logger.success(f"[ST]: mess = {mess}, delta={self.deltaTime}")


class Mode:
    """docstring for Mode"""

    def __init__(self):
        super(Mode, self).__init__()
        self.mode = '10'
        self.timer = None

    def _getTimer(self):
        if not self.timer:
            return 0
        else:
            return time.monotonic() - self.timer

    def getMode(self, mess, connect):
        if self._getTimer() >= ModeTimer:
            self.mode = '10'
            self.timer = None
        Write(f"#GM{self.mode}{ACK}", connect)
        logger.info(f"[GM]: Mode= {self.mode}")

    def setMode(self, mess, connect):
        mess = byteToStr(mess)
        mode = int(mess[mess.index('SM') + 2])
        self.mode = f'{mode}0'
        Write(DONE, connect)
        logger.success(f"[SM]: Mode= {self.mode}")


class State:

    def __init__(self):
        super(State, self).__init__()

    def getTemperature(self, mess, connect):
        Write(f"#GA0505{ACK}", connect)
        logger.success("[GA]: 0505")

    def getFan(self, mess, connect):
        fanSpeed = f"{randint(0,9999):04d}"
        Write(f"#GS{fanSpeed}{ACK}", connect)
        logger.success(f"[GS]: Fan speed= {fanSpeed}")

    def getClockCalibration(self, mess, connect):
        Write(f"#GL1000{ACK}", connect)
        logger.success("[GL]: 1000")

    def getPWMDivider(self, mess, connect):
        PWM = f"{randint(0,65535):05d}"
        Write(f"#GP{PWM}{ACK}", connect)
        logger.success(f"[GP]: PWM= {PWM}")


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
        # logger.debug(f"Points= {points}")
        pointsChannels, pointsTimes = points[:-1], points[-1]
        if pointsTimes[0] < tmInMin < pointsTimes[1]:
            delta = pointsTimes[1] - pointsTimes[0] if pointsTimes[1] < 1440 else (
                1440 - pointsTimes[1]) + pointsTimes[0]  # in min
        else:
            delta = 1440 - abs(pointsTimes[1] - pointsTimes[0])
        channels = []
        for couple in pointsChannels:
            couple = [10000 - i for i in couple]
            k = (couple[1] - couple[0]) / delta if couple[0] != couple[1] else 0
            channels.append((int(couple[0] + (k * (tmInMin - pointsTimes[0])))))
        # logger.debug(f"Channels calculated:\n{channels}")
        return channels

    def setChannels(self, mess, connect):
        mess = byteToStr(mess)
        self.channels = [10000 - int(i)
                         for i in mess[mess.index('SC') + 5:mess.index(ENQ)].split(US)]
        Write(DONE, connect)
        logger.success(f"[SC] Channels: {self.channels}")

    def getChannels(self, mess, connect):
        if self.cycle:
            timeNow = time.time() + self.deltaTime
            self.channels = self.calcChannels(self.cycle, timeNow)
        if self.mode == 20:
            Write(f"#GC{US.join([f'{10000-n:05d}' for n in self.channels])}{ACK}", connect)
        else:
            Write(f"#GC{US.join([f'{n:05d}' for n in self.channels])}{ACK}", connect)
        logger.success(f"[GC] Channels: {self.channels}")

    def HashCalc(self, cycle=None):
        if not cycle:
            return self.HASH
        HexCycle = to8bytes(self.cycle)
        CycleCRC = cycleCRC(HexCycle)
        result = (f"{len(self.cycle):02d}", f"{CycleCRC:05d}")
        logger.debug(f"[HashCalc] func: result= {result}")
        return result

    def setHash(self, hs: tuple):
        self.HASH = hs
        # logger.debug(f"setHash func: set self.Hash to {hs}")

    def returnHASH(self, mess, connect):
        result = f'#GH{self.HASH[0]}{US}{self.HASH[1]}{ACK}'
        Write(result, connect)
        logger.success(f"[GH] HASH: {result}")
