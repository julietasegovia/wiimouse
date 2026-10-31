import sys
import time
import tkinter as tk

import hid
from pynput.mouse import Button, Controller

# Settings
SMOOTHING = 0.5
SCROLL_DELAY = 0.1
EDGE_MAGRIN = 0.05

NINTENDO_VID = 0x057E
WIIMOTE_PIDS = (0x0306, 0x0330)
IR_W, IR_H = 1024, 768
B1_LEFT, B1_RIGHT, B1_DOWN, B1_UP = 0x01, 0x02, 0x04, 0x08
B2_B, B2_A, B2_HOME = 0x04, 0x08, 0x80

def find_wiimote():
    for pid in WIIMOTE_PIDS:
        devices = hid.enumerate(NINTENDO_VID, pid)
        if devices:
            dev = hid.device()
            dev.open_path(devices[0]["path"])
            return dev
        return None

def write_reg(dev, addr, data):
    payload = bytes([0x16, 0x04, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF, len(data)] + bytes(data).ljust(16, b"\x00"))
    dev.write(payload)
    time.sleep(0.05)

def init_ir_and_reporting(dev):
    dev.write(bytes([0x13, 0x04]))
    time.sleep(0.05)
    dev.write(bytes([0x1A, 0x04]))
    time.sleep(0.05)
    write_reg(dev, 0xB00030, [0x08])
    write_reg(dev, 0xB00000, [0x02, 0x00, 0x00, 0x71, 0x01, 0x00, 0xAA, 0x00, 0x64])
    write_reg(dev, 0xB0001A, [0x63, 0x03])
    write_reg(dev, 0xB00033, [0x03])
    write_reg(dev, 0xB00030, [0x08])
    dev.write(bytes([0x12, 0x04, 0x33]))
    time.sleep(0.05)
    dev.write(bytes([0x11, 0x10]))