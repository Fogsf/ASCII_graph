# GRID SCHEMATIC EDITOR (FINAL PROD BASELINE — ASCII FIXED CELL MODEL v1.0)
# -------------------------------------------------
# Управление:
# ЛКМ           → node
# Shift + ЛКМ   → center
# Shift + ПКМ   → boundary (*)
# ПКМ A → ПКМ B → сегмент между точками
# клавиши выбора элемента задаются в таблице ELEMENTS (поле "key")
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
    "transistor": {"key":"t","symbol":"T","color":"orange"},
    "diode": {"key":"d","symbol":"D","color":"yellow"},
    "inductor": {"key":"l","symbol":"L","color":"brown"},
    "vsource": {"key":"v","symbol":"V","color":"red"},
    "ground": {"key":"g","symbol":"G","color":"black"}
}

# -------------------------------------------------
# DATA
# -------------------------------------------------

points = []
center_elements = {}  # center point index -> element type
# (gx, gy, type)
# type = node | center | vertex | boundary | corner_fwd | corner_back
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

        # determine element source (center defines element)
    element_to_use = active_element

    # propagate element through element-chain geometry (inherit only from connected center)
    element_types = {"center","vertex","corner_fwd","corner_back"}

    if points[a][2] in element_types or points[b][2] in element_types:
        # direct center
        if points[a][2] == "center" and a in center_elements:
            element_to_use = center_elements[a]
        elif points[b][2] == "center" and b in center_elements:
            element_to_use = center_elements[b]
        else:
            # check if either endpoint already connected to a center via segments
            for s in segments:
                if s["start"] == a or s["end"] == a:
                    other = s["end"] if s["start"] == a else s["start"]
                    if points[other][2] == "center" and other in center_elements:
                        element_to_use = center_elements[other]
                        break
                if s["start"] == b or s["end"] == b:
                    other = s["end"] if s["start"] == b else s["start"]
                    if points[other][2] == "center" and other in center_elements:
                        element_to_use = center_elements[other]
                        break

    # wire cannot originate from center; block wire segments touching center
    if (points[a][2] == "center" or points[b][2] == "center") and element_to_use == "wire":
        return

    if points[a][2] == "center":
        element_to_use = center_elements.get(a, active_element)
    elif points[b][2] == "center":
        element_to_use = center_elements.get(b, active_element)

    segments.append({
        "start": a,
        "end": b,
        "element": element_to_use
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

        elif t == "vertex":
            ax.text(x, y, "~", ha="center", va="center")

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
        idx_new = len(points) - 1
        if ptype == "center":
            center_elements[idx_new] = active_element
        return idx_new

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
        elif event.key in ("alt","alt+graph"):
            idx = add_point(gx, gy, "vertex")
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

    # adjacency list
    adj = {i: [] for i,_ in enumerate(points)}
    for s in segments:
        a = s["start"]
        b = s["end"]
        adj[a].append(b)
        adj[b].append(a)

    visited = set()

    # ---------- ELEMENT CHAINS (center driven) ----------

    for center_idx,(gx,gy,t) in enumerate(points):

        if t != "center":
            continue

        stack = [center_idx]
        chain = set()

        while stack:
            p = stack.pop()
            if p in chain:
                continue

            chain.add(p)

            px,py,ptype = points[p]

            if ptype == "node" and p != center_idx:
                continue

            for nb in adj[p]:
                if nb not in chain:
                    stack.append(nb)

        # determine element
        element = center_elements.get(center_idx,"wire")

        cx,cy,_ = points[center_idx]

        # detect orientation
        horiz = False
        vert = False

        for nb in adj[center_idx]:
            x,y,_ = points[nb]
            if y == cy:
                horiz = True
            if x == cx:
                vert = True

        # draw wires
        for s in segments:

            if s["start"] not in chain or s["end"] not in chain:
                continue

            p1 = points[s["start"]]
            p2 = points[s["end"]]

            x1,y1 = p1[0],p1[1]
            x2,y2 = p2[0],p2[1]

            if x1 == x2:
                for y in range(min(y1,y2)+1,max(y1,y2)):
                    grid[(x1,y)] = "·"

            elif y1 == y2:
                for x in range(min(x1,x2)+1,max(x1,x2)):
                    grid[(x,y1)] = "·"

        sym = element_symbol(element, "horizontal" if horiz else "vertical")

        if sym.startswith("["):
            grid[(cx-1,cy)] = "["
            grid[(cx,cy)] = sym[1]
            grid[(cx+1,cy)] = "]"

        elif len(sym) == 3:
            grid[(cx,cy-1)] = "-"
            grid[(cx,cy)] = sym[1]
            grid[(cx,cy+1)] = "-"

        else:
            grid[(cx,cy)] = sym

        visited |= chain

    # ---------- NORMAL WIRES ----------

    for s in segments:

        if s["start"] in visited or s["end"] in visited:
            continue

        p1 = points[s["start"]]
        p2 = points[s["end"]]

        x1,y1 = p1[0],p1[1]
        x2,y2 = p2[0],p2[1]

        if x1 == x2:
            for y in range(min(y1,y2)+1,max(y1,y2)):
                grid[(x1,y)] = "|"

        elif y1 == y2:
            for x in range(min(x1,x2)+1,max(x1,x2)):
                grid[(x,y1)] = "-"

    # ---------- DRAW POINTS ----------

    for i,(gx,gy,t) in enumerate(points):

        if t == "node":
            grid[(gx,gy)] = "o"

        elif t == "vertex":
            grid[(gx,gy)] = "·"

        elif t == "corner_fwd":
            grid[(gx,gy)] = "/"

        elif t == "corner_back":
            grid[(gx,gy)] = "\\"

        elif t == "boundary":
            grid[(gx,gy)] = "-"

    if not grid:
        return ""

    xs = [p[0] for p in grid]
    ys = [p[1] for p in grid]

    min_x,max_x = min(xs),max(xs)
    min_y,max_y = min(ys),max(ys)

    lines = []

    for y in range(min_y,max_y+1):
        row = ""
        for x in range(min_x,max_x+1):
            row += grid.get((x,y)," ")
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
