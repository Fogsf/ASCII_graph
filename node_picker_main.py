# GRID SCHEMATIC EDITOR (CONTROL MODEL REWORK)
# -------------------------------------------------
# Управление:
# ЛКМ           → node
# Shift + ЛКМ   → junction
# Shift + ПКМ   → boundary (*)
# ПКМ A → ПКМ B → сегмент между точками
# W R C T       → выбор элемента (на 1 сегмент)
# -------------------------------------------------

import matplotlib.pyplot as plt
import matplotlib as mpl

# disable matplotlib default Ctrl+S (figure save)
mpl.rcParams['keymap.save'] = []

GRID_SIZE = 20
VIEW_W = 1500
VIEW_H = 900

# -------------------------------------------------
# ELEMENT COLORS
# -------------------------------------------------

ELEMENT_COLORS = {
    "wire": "blue",
    "resistor": "green",
    "capacitor": "purple",
    "transistor": "orange"
}

# -------------------------------------------------
# DATA
# -------------------------------------------------

points = []
# (gx, gy, type)
# type = node | junction | boundary

segments = []
# { start, end, element }

active_element = "wire"
pending_point = None

# -------------------------------------------------
# FIGURE
# -------------------------------------------------

fig, ax = plt.subplots()

# -------------------------------------------------
# SNAP
# -------------------------------------------------

def snap(px, py):
    return round(px / GRID_SIZE), round(py / GRID_SIZE)

# -------------------------------------------------
# FIND POINT
# -------------------------------------------------

def find_point(gx, gy):
    for i, (x, y, _) in enumerate(points):
        if x == gx and y == gy:
            return i
    return None

# -------------------------------------------------
# CHECK SEGMENT EXISTS
# -------------------------------------------------

def segment_exists(a, b):
    for s in segments:
        if (s["start"] == a and s["end"] == b) or (s["start"] == b and s["end"] == a):
            return True
    return False

# -------------------------------------------------
# CREATE SEGMENT
# -------------------------------------------------

def create_segment(a, b):

    global active_element

    pa = points[a]
    pb = points[b]

    # запрет диагоналей
    if pa[0] != pb[0] and pa[1] != pb[1]:
        return

    if segment_exists(a, b):
        return

    segments.append({
        "start": a,
        "end": b,
        "element": active_element
    })

    active_element = "wire"

# -------------------------------------------------
# DRAW GRID
# -------------------------------------------------

def draw_grid():

    for x in range(0, VIEW_W, GRID_SIZE):
        ax.plot([x, x], [0, VIEW_H], color="#222", linewidth=0.5)

    for y in range(0, VIEW_H, GRID_SIZE):
        ax.plot([0, VIEW_W], [y, y], color="#222", linewidth=0.5)

# -------------------------------------------------
# DRAW SEGMENTS
# -------------------------------------------------

def draw_segments():

    for s in segments:

        p1 = points[s["start"]]
        p2 = points[s["end"]]

        x1 = p1[0] * GRID_SIZE
        y1 = p1[1] * GRID_SIZE

        x2 = p2[0] * GRID_SIZE
        y2 = p2[1] * GRID_SIZE

        color = ELEMENT_COLORS.get(s["element"], "blue")

        ax.plot([x1, x2], [y1, y2], color=color, linewidth=3)

# -------------------------------------------------
# DRAW POINTS
# -------------------------------------------------

def draw_points():

    for gx, gy, t in points:

        x = gx * GRID_SIZE
        y = gy * GRID_SIZE

        if t == "node":
            ax.plot(x, y, "ro", markersize=6)

        elif t == "junction":
            ax.plot(x, y, "b+", markersize=10)

        elif t == "boundary":
            ax.plot(x, y, "yx", markersize=8)

# -------------------------------------------------
# REDRAW
# -------------------------------------------------

def redraw():

    ax.clear()

    ax.set_xlim(0, VIEW_W)
    ax.set_ylim(VIEW_H, 0)

    ax.set_aspect("equal")

    draw_grid()
    draw_segments()
    draw_points()

    ax.set_title(f"MODE: {active_element.upper()}")

    fig.canvas.draw_idle()

# -------------------------------------------------
# ADD POINT
# -------------------------------------------------

def add_point(gx, gy, ptype):

    idx = find_point(gx, gy)

    if idx is None:
        points.append((gx, gy, ptype))
        return len(points) - 1

    return idx

# -------------------------------------------------
# MOUSE
# -------------------------------------------------

def on_mouse(event):

    global pending_point

    if event.xdata is None:
        return

    gx, gy = snap(event.xdata, event.ydata)

    # LEFT CLICK
    if event.button == 1:

        if event.key == "shift":
            idx = add_point(gx, gy, "junction")
        else:
            idx = add_point(gx, gy, "node")

        redraw()
        return

    # RIGHT CLICK
    if event.button == 3:

        if event.key == "shift":

            add_point(gx, gy, "boundary")
            redraw()
            return

        idx = find_point(gx, gy)

        if idx is None:
            return

        if pending_point is None:
            pending_point = idx
        else:
            create_segment(pending_point, idx)
            pending_point = None

        redraw()

# -------------------------------------------------
# ASCII EXPORT
# -------------------------------------------------

def generate_ascii():

    grid = {}

    # draw wires first
    for s in segments:

        p1 = points[s["start"]]
        p2 = points[s["end"]]

        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]

        element = s["element"]

        if x1 == x2:

            y_start = min(y1, y2)
            y_end = max(y1, y2)

            for y in range(y_start + 1, y_end):
                grid[(x1, y)] = "|"

        elif y1 == y2:

            x_start = min(x1, x2)
            x_end = max(x1, x2)

            for x in range(x_start + 1, x_end):
                grid[(x, y1)] = "-"

        # place element if not wire
        if element != "wire":

            if x1 == x2:

                length = abs(y2 - y1)
                pos = min(y1, y2) + max(1, length // 2)

                grid[(x1, pos)] = element[0].upper()

            else:

                length = abs(x2 - x1)
                pos = min(x1, x2) + max(1, length // 2)

                grid[(pos, y1)] = element[0].upper()

    # draw nodes
    for gx, gy, t in points:

        if t == "node":
            grid[(gx, gy)] = "o"

        elif t == "junction":
            grid[(gx, gy)] = "+"

    if not grid:
        return ""

    xs = [p[0] for p in grid]
    ys = [p[1] for p in grid]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    lines = []

    for y in range(min_y, max_y + 1):

        row = ""

        for x in range(min_x, max_x + 1):

            row += grid.get((x, y), " ")

        lines.append(row)

    return "\n".join(lines)

# -------------------------------------------------
# SAVE
# -------------------------------------------------

def save_scheme():

    ascii_scheme = generate_ascii()

    with open("scheme.js", "w", encoding="utf-8") as f:
        f.write("export const scheme = `\n" + ascii_scheme + "\n`;\n")

    print("scheme.js updated")

# -------------------------------------------------
# KEYBOARD
# -------------------------------------------------

def on_key(event):

    global active_element

    k = event.key

    if k == "w":
        active_element = "wire"

    if k == "r":
        active_element = "resistor"

    if k == "c":
        active_element = "capacitor"

    if k == "t":
        active_element = "transistor"

    if k in ("ctrl+s","control+s","cmd+s"): 
        save_scheme()

    redraw()

# -------------------------------------------------
# EVENTS
# -------------------------------------------------

fig.canvas.mpl_connect("button_press_event", on_mouse)
fig.canvas.mpl_connect("key_press_event", on_key)

# -------------------------------------------------
# START
# -------------------------------------------------

redraw()

plt.show()
