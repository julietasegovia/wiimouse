import select
import sys
import time

from evdev import AbsInfo, InputDevice, UInput, ecodes as e, list_devices

SMOOTHING = 0.35
SCROLL_DELAY = 0.08
EDGE_MARGIN = 0.04

IR_W, IR_H = 1023, 767
ABS_MAX = 32767
IR_AXES = [(e.ABS_HAT0X, e.ABS_HAT0Y), (e.ABS_HAT1X, e.ABS_HAT1Y), (e.ABS_HAT2X, e.ABS_HAT2Y), (e.ABS_HAT3X, e.ABS_HAT3Y)]

def find_devices():
    buttons = ir = None
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        name = dev.name
        if name == "Nintendo Wii Remote":
            buttons = dev
        elif name == "Nintendo Wii Remote IR":
            ir = dev
    return buttons, ir

def main():
    buttons, ir = find_devices()
    if buttons is None or ir is None:
        print("No wiimote found")
        print("Check with grep -i wii /proc/bus/input/devices")
        sys.exit(1)

    try:
        ui = UInput(
            {
                e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT],
                e.EV_REL: [e.REL_WHEEL],
                e.EV_ABS: [
                    (e.ABS_X, AbsInfo(0, 0, ABS_MAX, 0, 0, 0)),
                    (e.ABS_Y, AbsInfo(0, 0, ABS_MAX, 0, 0, 0)),
                ],
            },
            name="Wiimote Virtual Mouse"
        )
    except PermissionError:
        print("No permits, try sudo chmod 666 /dev/uinput")
        sys.exit(1)

    buttons.grab()
    ir.grab()

    print("Wiimote connected. Press HOME to exit")

    points = {axes:[1023, 1023] for axes in IR_AXES}
    sx = sy = None
    up = down = False
    last_scroll = 0.0
    running = True

    try:
        while running:
            r, _, _ = select.select([buttons.fd, ir.fd], [], [], 0.05)
            for fd in r:
                dev = buttons if fd == buttons.fd else ir
                for ev in dev.read():
                    if dev is buttons and ev.type == e.EV_KEY:
                        if ev.code == e.BTN_A:
                            ui.write(e.EV_KEY, e.BTN_LEFT, 1 if ev.value else 0)
                            ui.syn()
                        elif ev.code == e.BTN_B:
                            ui.write(e.EV_KEY, e.BTN_RIGHT, 1 if ev.value else 0)
                            ui.syn()
                        elif ev.code == e.KEY_UP:
                            up = ev.value != 0
                        elif ev.code == e.KEY_DOWN:
                            down = ev.value != 0
                        elif ev.code == e.BTN_MODE and ev.value ==1: #home button
                            running = False
                    
                    elif dev is ir:
                        if ev.type == e.EV_ABS:
                            for axes in IR_AXES:
                                if ev.code == axes[0]:
                                    points[axes][0] = ev.value
                                elif ev.code == axes[1]:
                                    points[axes][1] = ev.value
                        elif ev.type == e.EV_SYN:
                            valid = [tuple(p) for p in points.values() if not (p[0] >= 1023 and p[1] >= 1023)]
                            if len(valid) >= 2:
                                valid.sort()
                                (x1, y1), (x2, y2) = valid[0], valid[-1]
                                mx, my = (x1 + x2) / 2, (y1 + y2) / 2

                                nx = 1.0 - mx / IR_W
                                ny = my / IR_H
                                nx = (nx - EDGE_MARGIN) / (1 - 2 * EDGE_MARGIN)
                                ny = (ny - EDGE_MARGIN) / (1 - 2 * EDGE_MARGIN)
                                nx = min(max(nx, 0.0), 1.0)
                                ny = min(max(ny, 0.0), 1.0)

                                tx, ty = nx * ABS_MAX, ny * ABS_MAX
                                if sx is None:
                                    sx, sy = tx, ty
                                sx += (tx - sx) *(1 - SMOOTHING)
                                sy += (ty - sy) * (1 - SMOOTHING)
                                ui.write(e.EV_ABS, e.ABS_X, int(sx))
                                ui.write(e.EV_ABS, e.ABS_Y, int(sy))
                                ui.syn()

            now = time.time()
            if now - last_scroll > SCROLL_DELAY:
                if up:
                    ui.write(e.EV_REL, e.REL_WHEEL, 1)
                    ui.syn()
                    last_scroll = now
                elif down:
                    ui.write(e.EV_REL, e.REL_WHEEL, -1)
                    ui.syn()
                    last_scroll = now

    except (KeyboardInterrupt, OSError):
        pass
    finally:
        for dev in (buttons, ir):
            try:
                dev.ungrab()
            except OSError:
                pass
        ui.close()
        print("Bye!")

if __name__ == "__main__":
    main()