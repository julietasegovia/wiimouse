# WiiMouse
## Why did I make this?
I don't have a TV on my room, so usually I lay down and watch movies on my computer. The thing is, if I had to pause or turn up the volume I had to stand up to reach my mouse. 

So, I remembered my old Wii and realized that the system of the Wiimote is exactly what I wanted but for my PC. I did some research and discovered that You can easily connect a Wiimote with bluetooth on a Linux system. So, here's the script I used to translate the Wiimote input into instructions for the PC.

## What you need

- A Linux system with Bluetooth (I use Fedora)
- A Wiimote
- A powered sensorbar
- Python3 with the packages python3-devel, gcc and xrandr

## Video Demo

[Here](https://drive.google.com/file/d/1k8awHS2si7uaI_aQeHk4bku0rFye6q7g/view?usp=sharing)

## Controls

Button | Action
-------|-------
A | Left click
B | Right click
D-pad up/down | Scroll up/down
+/- | Volume up/down (I forgot to demonstrate this one on the video lmao)
1 | Switch monitor focus
HOME | Cut the script

## How it works
The hard work was already made as the kernel hid-wiimote driver already exists. So, with that driver the PC already 'listens' to the wiimote input. With my script, I just let the computer know what I want it to do with that input.

Basically, this script just translates the already existing inputs to mouse (and sometimes other) inputs. On the top of the script you'll find a bunch of constant variables, most of them describe for how long something is considered a 'click' or a 'scroll' as the wiimote just registers a button press. You can change these settings to your liking, of course.

## How to run it

Dependencies
```bash
sudo dnf install python3-devel gcc xrandr
pip install evdev
```

Enable uinput
```bash
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf
```

Give your user permits
```bash
echo 'KERNEL=="event*", SUBSYSTEM=="input", ATTRS{name}=="Nintendo Wii Remote*", MODE="0666"' | sudo tee /etc/udev/rules.d/99-wiimote-input.rules

echo 'KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0666"' | sudo tee -a /etc/udev/rules.d/99-wiimote-input.rules

sudo udevadm control --reload-rules
```

Let BlueZ accpet the Wiimote
```bash
sudo sed -i 's/^#\?ClassicBondedOnly=.*/ClassicBondedOnly=false/' /etc/bluetooth/input.conf

grep ClassicBondedOnly /etc/bluetooth/input.conf

sudo systemctl restart bluetooth
```

Then, connect the Wiimote via bluetooth and run the script
```bash
python wiimote_monitors.py
```

Just like in the original Wii, the Wiimote has a hard time reading the sensor when it's to close to it so I would advice to use this while being at least 1 or 2 feet away from it.
