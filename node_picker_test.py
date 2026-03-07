# GRID SCHEMATIC EDITOR (FINAL PROD BASELINE — ASCII FIXED CELL MODEL v1.0)
# -------------------------------------------------
# Управление:
# ЛКМ           → node
# Shift + ЛКМ   → center
# Shift + ПКМ   → boundary (*)
# ПКМ A → ПКМ B → сегмент между точками
# W R C T       → выбор элемента (на 1 сегмент)
# -------------------------------------------------

import matplotlib.pyplot as plt
import matplotlib as mpl
import json

# background image for real schematic overlay
background_image = None


# disable matplotlib default Ctrl+S (figure save)
mpl.rcParams['keymap.save'] = []

GRID_SIZE = 20
VIEW_W = 1500
VIEW_H = 900

# grid alignment offsets
GRID_OFFSET_X = 0
GRID_OFFSET_Y = 0

# -------------------------------------------------
# ELEMENT TABLE
# -------------------------------------------------

ELEMENTS = {
    "wire": {"key":"w","symbol":"-","color":"blue"},
    "resistor": {"key":"r","symbol":"R","color":"green"},
    "capacitor": {"key":"c","symbol":"C","color":"purple"},
    "transistor": {"key":"t","symbol":"T","color":"orange"}
}

# -------------------------------------------------
# DATA
# -------------------------------------------------

points = []
# (gx, gy, type)
# type = node | center | boundary | corner_fwd | corner_back
# corner_fwd  = visual corner marker "/"
# corner_back = visual corner marker "\\"

segments = []  # { start, end, element }

# -------------------------------------------------
# UNDO / REDO
# -------------------------------------------------

history_undo = []
history_redo = []


def snapshot_state():
    return {
        "points": [tuple(p) for p in points],
        "segments": [dict(s) for s in segments]
    }


def restore_state(state):
    global points, segments
    points = [tuple(p) for p in state["points"]]
    segments = [dict(s) for s in state["segments"]]


def push_state():
    history_undo.append(snapshot_state())
    history_redo.clear()


def undo():
    if not history_undo:
        return

    history_redo.append(snapshot_state())

    state = history_undo.pop()
    restore_state(state)

    redraw()


def redo():
    if not history_redo:
        return

    history_undo.append(snapshot_state())

    state = history_redo.pop()
    restore_state(state)

    redraw()
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
    return round((px - GRID_OFFSET_X) / GRID_SIZE), round((py - GRID_OFFSET_Y) / GRID_SIZE)

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

    push_state()

    global active_element

    pa = points[a]
    pb = points[b]

    # запрет диагоналей
    if pa[0] != pb[0] and pa[1] != pb[1]:
        return

    if segment_exists(a, b):
        return

    # block segments that pass through boundary (*)
    for i,(gx,gy,t) in enumerate(points):
        if t != "boundary":
            continue

        # vertical segment
        if pa[0] == pb[0] and gx == pa[0]:
            if min(pa[1],pb[1]) < gy < max(pa[1],pb[1]):
                return

        # horizontal segment
        if pa[1] == pb[1] and gy == pa[1]:
            if min(pa[0],pb[0]) < gx < max(pa[0],pb[0]):
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

    for x in range(-GRID_OFFSET_X, VIEW_W, GRID_SIZE):
        ax.plot([x + GRID_OFFSET_X, x + GRID_OFFSET_X], [0, VIEW_H], color="#222", linewidth=0.5)

    for y in range(-GRID_OFFSET_Y, VIEW_H, GRID_SIZE):
        ax.plot([0, VIEW_W], [y + GRID_OFFSET_Y, y + GRID_OFFSET_Y], color="#222", linewidth=0.5)

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

        color = ELEMENTS.get(s["element"], {}).get("color", "blue")

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

        elif t == "center":
            ax.plot(x, y, "b+", markersize=10)

        elif t == "corner_fwd":
            ax.text(x, y, "/", ha="center", va="center")

        elif t == "corner_back":
            ax.text(x, y, "\\", ha="center", va="center")

        elif t == "boundary":
            ax.plot(x, y, "yx", markersize=8)

# -------------------------------------------------
# REDRAW
# -------------------------------------------------

def load_background(path="schematic.png"):

    push_state()

    global background_image, VIEW_W, VIEW_H

    try:
        background_image = plt.imread(path)

        h, w = background_image.shape[:2]
        VIEW_W = w
        VIEW_H = h

        print("background loaded:", path, w, h)

    except Exception as e:
        print("background load error:", e)

    redraw()

# -------------------------------------------------
# REDRAW
# -------------------------------------------------

def redraw():

    ax.clear()

    ax.set_xlim(0, VIEW_W)
    ax.set_ylim(VIEW_H, 0)

    ax.set_aspect("equal")

    if background_image is not None:
        ax.imshow(background_image, extent=[0, VIEW_W, VIEW_H, 0])

    draw_grid()
    draw_segments()
    draw_points()

    ax.set_title(f"MODE: {active_element.upper()}")

    fig.canvas.draw_idle()

# -------------------------------------------------
# ADD POINT
# -------------------------------------------------

def add_point(gx, gy, ptype):

    push_state()

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

        if event.key in ("control","ctrl"):
            idx = add_point(gx, gy, "corner_fwd")
        elif event.key == "shift":
            idx = add_point(gx, gy, "center")
        else:
            idx = add_point(gx, gy, "node")

        redraw()
        return

    # RIGHT CLICK
    if event.button == 3:

        if event.key in ("control","ctrl"):

            add_point(gx, gy, "corner_back")
            redraw()
            return

        if event.key == "shift":

            add_point(gx, gy, "boundary")
            redraw()
            return

        idx = find_point(gx, gy)

        if idx is None:
            pending_point = None
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

def element_symbol(element, orientation):

    symbol = ELEMENTS.get(element, {}).get("symbol", "-")

    if orientation == "horizontal":
        return f"[{symbol}]" if symbol != "-" else "-"

    return f"-{symbol}-" if symbol != "-" else "-"



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
                if (x1, y) not in grid:
                    grid[(x1, y)] = "|"

        elif y1 == y2:

            x_start = min(x1, x2)
            x_end = max(x1, x2)

            for x in range(x_start + 1, x_end):
                if (x, y1) not in grid:
                    grid[(x, y1)] = "-"

        # place element if not wire
        if element != "wire":

            sym = element_symbol(element, "vertical" if x1 == x2 else "horizontal")

            seg_len = abs(y2 - y1) if x1 == x2 else abs(x2 - x1)
            if seg_len < len(sym):
                core = next((c for c in sym if c.isalpha()), None)
                sym = core if core else sym[0]

            if x1 == x2:

                length = abs(y2 - y1)
                pos = min(y1, y2) + max(1, length // 2)
                start = pos - (len(sym)//2)

                for i, ch in enumerate(sym):
                    y = start + i
                    if (x1, y) not in grid or grid[(x1, y)] in "-|":
                        grid[(x1, y)] = ch
                        

            else:

                length = abs(x2 - x1)
                pos = min(x1, x2) + max(1, length // 2)
                start = pos - (len(sym)//2)

                for i, ch in enumerate(sym):
                    x = start + i
                    if (x, y1) not in grid or grid[(x, y1)] in "-|":
                        grid[(x, y1)] = ch
                        

    # draw nodes
    for i,(gx, gy, t) in enumerate(points):

        if t == "node":
            if (gx, gy) not in grid or grid[(gx, gy)] in "-|":
                grid[(gx, gy)] = "o"

        elif t == "corner_fwd":
            grid[(gx, gy)] = "/"

        elif t == "corner_back":
            grid[(gx, gy)] = "\\"        

        elif t == "boundary":

            horiz = False
            vert = False

            for s in segments:
                if s["start"] == i or s["end"] == i:

                    p1 = points[s["start"]]
                    p2 = points[s["end"]]

                    if p1[0] == p2[0]:
                        vert = True

                    if p1[1] == p2[1]:
                        horiz = True

            if horiz and not vert:
                grid[(gx, gy)] = "-"
            elif vert and not horiz:
                grid[(gx, gy)] = "|"
            elif horiz and vert:
                # crossing without junction: prefer horizontal representation
                grid[(gx, gy)] = "-"

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

            cell = grid.get((x, y), " ")
            row += cell

        lines.append(row)

    return "\n".join(lines)

# -------------------------------------------------
# PROJECT SAVE / LOAD
# -------------------------------------------------

def save_project(path="project.json"):

    data = {
        "points": points,
        "segments": segments
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    print("project saved", path)


def load_project(path="project.json"):

    push_state()

    global points, segments

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = [tuple(p) for p in data.get("points", [])]
    segments = data.get("segments", [])

    redraw()

    print("project loaded", path)

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

    global active_element, pending_point

    k = event.key

    if k in ("ctrl+i","control+i"):
        load_background()
        return

    if k in ("ctrl+z","control+z"):
        undo()
        return

    if k in ("ctrl+y","control+y"):
        redo()
        return

    if k == "escape":
        pending_point = None
        return

    for name, data in ELEMENTS.items():
        if k == data["key"]:
            active_element = name
            break

    if k in ("ctrl+s","control+s","cmd+s"):
        save_scheme()

    if k in ("ctrl+p","control+p"):
        save_project()

    if k in ("ctrl+l","control+l"):
        load_project()

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
