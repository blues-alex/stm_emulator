#!/usr/bin/env python3

import sys
import pprint
from utils.SerialUtils import *
from utils.Protocol import *
from utils.Commands import *

DC = dc()
GT = DC.getTime
ST = DC.setTime
GH = DC.returnHASH
SM = DC.setMode
GM = DC.getMode
GC = DC.getChannels
SC = DC.setChannels
GA = DC.getTemperature
GS = DC.getFan
GL = DC.getClockCalibration
GP = DC.getPWMDivider

COMMANDS = {'GT': GT,
            'GV': GV,
            'GC': GC,
            'GH': GH,
            'SM': SM,
            'GM': GM,
            'GL': GL,
            'GA': GA,
            'GS': GS,
            'SC': SC,
            'ST': ST,
            'GL': GL,
            'GP': GP
            }


def messCrcCheck(mess):
    if type(mess) == bytes:
        return CRC16(byteToStr(mess[:-2])) == mess[-2:]
    else:
        return CRC16(mess[:-2]) == mess[-2:]


def Reader(connect):
    mess = b''
    while True:
        b = connect.read()
        if b in [b'$', b'\x01']:
            mess += b
            while b not in map(bytes, [[5], [2]]):
                b = connect.read()
                mess += b
            mess += connect.read(2)
            break
    return mess


def CycleReader(connect):
    mess = b''
    b = connect.read()
    if b in map(bytes, [[4], [3]]):
        # logger.debug(f"End of cycle: {b[0]:02x}")
        return b
    while b not in map(bytes, [[4], [3], [0x1e]]):
        b = connect.read()
        mess += b
    # logger.debug(f"cycleWriter mess:\n{mess}")
    return mess + connect.read(2)


def Handler(mess, connect):
    if messCrcCheck(mess):
        if b'\x24' in mess:
            req = byteToStr(mess[mess.index(b'\x24') + 1:mess.index(b'\x24') + 3])
            COMMANDS[req](connect=connect, mess=mess)
            logger.debug(f"Incomming Request: {req}, mess= {mess}")
        elif mess[0] in [1, 3, 4]:
            logger.info(f"Start write cycle {mess}")
            Write(ACK, connect)
            cycle = []
            while True:
                point = CycleReader(connect)
                if (US in byteToStr(point)) and (RS in byteToStr(point)):
                    if messCrcCheck(point):
                        parse_point = [i for i in byteToStr(point).split(RS)[0].split(US)]
                        parse_point.append(HoursToMin(parse_point.pop(0)))
                        parse_point = [int(i) for i in parse_point]
                        cycle.append(parse_point)
                        Write(ACK, connect)
                elif len(point) and point[0] == 3:
                    DC.cycle = cycle
                    DC.setHash(DC.HashCalc(cycle=cycle))
                    logger.success(f"New cycle: \n{pprint.pformat(cycle)}")
                    logger.info(f"New cycle HASH = {DC.HASH}")
                    Write(ACK, connect)
                elif len(point) and point[0] == 4:
                    logger.success(f"End of writing cycle. Sending ACK.")
                    Write(ACK, connect)
                    break


port = 'COM6'
if (len(sys.argv) > 1):
    port = sys.argv[1]

logger.info(f'Listening on device: {port}')

timeout = 0.01
baudrate = 9600

with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as connect:
    n = 0
    try:
        while True:
            mess = Reader(connect)
            logger.debug(f'[{n}] {mess}')
            Handler(mess, connect)
            n += 1
    except KeyboardInterrupt:
        logger.info(f"Exit!")
