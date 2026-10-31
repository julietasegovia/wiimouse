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

def parse_ir(data):
    points = []
    ir = data[6:18]
    for i in range(0, 12, 3):
        b0, b1, b2, = ir[i], ir[i+1], ir[i+2]
        if b0 == 0xFF and b1 == 0xFF and b2 == 0xFF:
            continue
        x = b0 | ((b2>>4) & 0x03) << 8
        y = b1 | ((b2>>6) & 0x03) << 8
        points.append((x,y))
    return points

def main():
    dev = find_wiimote()
    if dev is None:
        print("No Wiimote Found.")
        sys.exit(1)

    root = tk.Tk()
    screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.destroy()

    mouse = Controller()
    init_ir_and_reporting(dev)
    print("Wiimote connected. Press HOME to quit")

    sx, sy = mouse.position
    a_down = b_down = False
    last_scroll = 0.0

    try:
        while True:
            data = dev.read(32, 200)
            if not data or data[0] != 0x33:
                continue

            b1, b2 = data[1], data[2]

            pts = parse_ir(data)
            if len(pts) >= 2:
                pts.sort()
                (x1, y1), (x2, y2) = pts[0], pts[-1]
                mx, my = (x1 + x2)/2, (y1 + y2)/2

                nx = 1.0 -mx / IR_W
                ny = my / IR_H

                nx = (nx - EDGE_MAGRIN) / (1-2 * EDGE_MAGRIN)
                ny = (ny - EDGE_MAGRIN) / (1-2 * EDGE_MAGRIN)
                nx = min(max(nx, 0.0), 1.0)
                ny = min(max(ny, 0.0), 1.0)

                tx, ty = nx * (screen_w - 1), ny * (screen_h - 1)
                sx += (tx - sx) * (1 - SMOOTHING)
                sy += (ty - sy) * (1 - SMOOTHING)
                mouse.position = (int(sx), int(sy))

            # buttons. A for left click B for right click
            a_now = bool(b2 & B2_A)
            b_now = bool(b2 & B2_B)

            if a_now and not a_down:
                mouse.press(Button.left)
            elif not a_now and a_down:
                mouse.release(Button.left)

            if b_now and not b_down:
                mouse.press(Button.right)
            elif not b_now and b_down:
                mouse.release(Button.right)

            a_down, b_down = a_now, b_now

            # D-pad scroll
            now = time.time()
            if now - last_scroll > SCROLL_DELAY:
                if b1 & B1_UP:
                    mouse.scroll(0, 1)
                    last_scroll = now
                elif b1 & B1_DOWN:
                    mouse.scroll(0, -1)
                    last_scroll = now

            if b2 & B2_HOME:
                break

    except KeyboardInterrupt:
        pass
    finally:
        if a_down:
            mouse.release(Button.left)
        if b_down:
            mouse.release(Button.right)
        dev.write(bytes([0x12, 0x00, 0x30]))
        dev.close()
        print("Bye")

if __name__ == "__main__":
    main()