import glob
import os
import select
import sys
import time
import tkinter as tk

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

def find_wiimote_path():
    for path in sorted(glob.glob("/dev/hidraw*")):
        name = os.path.basename(path)
        uevent = f"/sys/class/hidraw/{name}/device/uevent"
        try:
            with open(uevent) as f:
                for line in f:
                    if line.startswith("HID_ID=") and "0000057E" in line.upper():
                        return path
        except OSError:
            continue
    return None


class Wiimote:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDWR)

    def write(self, data):
        os.write(self.fd, bytes(data))

    def read(self, timeout=0.2):
        r, _, _ = select.select([self.fd], [], [], timeout)
        if not r:
            return None
        return os.read(self.fd, 32)

    def write_reg(self, addr, data):
        payload = bytes([0x16, 0x04, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF, len(data)]) + bytes(data).ljust(16, b"\x00")
        self.write(payload)
        time.sleep(0.05)

    def init_ir(self):
        self.write([0x13, 0x04])
        time.sleep(0.05)
        self.write([0x1A, 0x04])
        time.sleep(0.05)
        self.write_reg(0xB00030, [0x08])
        self.write_reg(0xB00000, [0x02, 0x00, 0x00, 0x71, 0x01, 0x00, 0xAA, 0x00, 0x64])
        self.write_reg(0xB0001A, [0x63, 0x03])
        self.write_reg(0xB00033, [0x03])
        self.write_reg(0xB00030, [0x08])
        self.write([0x12, 0x04, 0x33])
        time.sleep(0.05)
        self.write([0x11, 0x10])

    def close(self):
        try:
            self.write([0x12, 0x00, 0x30])
        except OSError:
            pass
        os.close(self.id) 

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
    path = find_wiimote_path()
    if path is None:
        print("No wiimote found")
        sys.exit(1)
    try:
        wm = Wiimote(path)
    except PermissionError:
        print(f"No permits to open {path}. Check udev or use sudo chmod 666 {path}")
        sys.exit(1)

    root = tk.Tk()
    screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.destroy()

    mouse = Controller()
    wm.init_ir()
    print(f"Wiimote connected {path}. Press HOME to exit")

    sx, sy = mouse.position
    a_down = b_down = False
    last_scroll = 0.0

    try:
        while True:
            data = wm.read()
            if not data or data[0] != 0x33 or len(data) < 18:
                continue

            b1, b2 = data[1], data[2]
            pts = parse_ir(data)
            if len(pts) >= 2:
                pts.sort()
                (x1, y1), (x2, y2) = pts[0], pts[-1]
                mx, my = (x1 + x2) / 2, (y1 + y2) /2

                nx = 1.0 -mx / IR_W
                ny = my / IR_H
                nx = (nx - EDGE_MAGRIN) / (1 - 2 * EDGE_MAGRIN)
                ny = (ny - EDGE_MAGRIN) / (1 - 2 * EDGE_MAGRIN)
                nx = min(max(nx, 0.0), 1.0)
                ny = min(max(ny, 0.0), 1.0)

                tx, ty = nx * (screen_w - 1), ny * (screen_h - 1)
                sx += (tx - sx) * (1 - SMOOTHING)
                sy += (ty - sy) * (1 - SMOOTHING)
                mouse.position = (int(sx), int(sy))

            a_now = bool(b2 & B2_A)
            b_now = bool(b2 & B2_B)

            if a_now and not a_down:
                mouse.press(Button.left)
            elif a_now and a_down:
                mouse.release(Button.left)

            if b_now and not b_down:
                mouse.press(Button.right)
            elif b_now and b_down:
                mouse.release(Button.right)

            a_down, b_down = a_now, b_now

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

    except (KeyboardInterrupt, OSError):
        pass
    finally:
        if a_down:
            mouse.release(Button.left)
        if b_down:
            mouse.release(Button.right)
        wm.close()
        print("Bye!")

if __name__ == "__main__":
    main()