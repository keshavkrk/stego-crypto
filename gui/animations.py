"""
SecureGuard - Safe Animation Effects
Only uses CTk widget properties (no raw Canvas draws).
"""
import math


def pulse_button(widget, base_hex, target_hex, steps=20, interval=50):
    """Color-shift a button using a sine wave."""
    current_step = [0]
    direction = [1]

    def hex_to_rgb(hx):
        hx = hx.lstrip('#')
        return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb):
        return '#%02x%02x%02x' % rgb

    base_rgb = hex_to_rgb(base_hex)
    target_rgb = hex_to_rgb(target_hex)

    def do_pulse():
        try:
            state = widget.cget("state")
            if state != "disabled":
                current_step[0] += direction[0]
                if current_step[0] >= steps or current_step[0] <= 0:
                    direction[0] *= -1
                ratio = current_step[0] / steps
                eased = (math.sin(ratio * math.pi - math.pi / 2) + 1) / 2
                r = int(base_rgb[0] + (target_rgb[0] - base_rgb[0]) * eased)
                g = int(base_rgb[1] + (target_rgb[1] - base_rgb[1]) * eased)
                b = int(base_rgb[2] + (target_rgb[2] - base_rgb[2]) * eased)
                widget.configure(fg_color=rgb_to_hex((r, g, b)))
            widget.after(interval, do_pulse)
        except Exception:
            pass

    do_pulse()


def typewriter_text(widget, text, interval=25, callback=None):
    """Animate text appearing character by character."""
    def type_next(idx):
        try:
            if idx <= len(text):
                widget.configure(text=text[:idx])
                widget.after(interval, type_next, idx + 1)
            elif callback:
                callback()
        except Exception:
            pass
    type_next(0)


def glow_border(widget, color1, color2, interval=60):
    """Animate border_color of a CTkFrame between two colors."""
    step = [0]
    direction = [1]

    def hex_to_rgb(hx):
        hx = hx.lstrip('#')
        return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb):
        return '#%02x%02x%02x' % (max(0, min(255, rgb[0])),
                                   max(0, min(255, rgb[1])),
                                   max(0, min(255, rgb[2])))

    c1 = hex_to_rgb(color1)
    c2 = hex_to_rgb(color2)

    def tick():
        try:
            step[0] += direction[0]
            if step[0] >= 25 or step[0] <= 0:
                direction[0] *= -1
            ratio = step[0] / 25.0
            eased = (math.sin(ratio * math.pi - math.pi / 2) + 1) / 2
            r = int(c1[0] + (c2[0] - c1[0]) * eased)
            g = int(c1[1] + (c2[1] - c1[1]) * eased)
            b = int(c1[2] + (c2[2] - c1[2]) * eased)
            widget.configure(border_color=rgb_to_hex((r, g, b)))
            widget.after(interval, tick)
        except Exception:
            pass

    tick()
