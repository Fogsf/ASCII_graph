# GRID SCHEMATIC EDITOR (ASCII GRID SCHEMATIC EDITOR — VERSION 1.1)
# -------------------------------------------------
# PATCH-28
# Connection Direction Hint — после выбора точки показываются доступные направления соединения, занятые направления скрываются
# Убран Smart Snap — find_point снова ищет только точное совпадение координат
# -------------------------------------------------
# Управление:
# ЛКМ           → node
# Shift + ЛКМ   → boundary (*)
# Alt + ПКМ     → center
# Ctrl + ЛКМ    → corner_fwd
# Ctrl + ПКМ    → corner_back
# ПКМ A → ПКМ B → сегмент между точками
# клавиши выбора элемента задаются в таблице ELEMENTS (поле "key")
# -------------------------------------------------

import matplotlib.pyplot as plt
import matplotlib as mpl
import json

background_image = None

mpl.rcParams['keymap.save'] = []

GRID_SIZE = 20
VIEW_W = 1500
VIEW_H = 900

GRID_OFFSET_X = 0
GRID_OFFSET_Y = 0

# -------------------------------------------------
# ELEMENT TABLE
# -------------------------------------------------

ELEMENTS = {
    "wire": {"key":"w","ru":"ц","symbol":"-","color":"blue","label":"провод"},
    "resistor": {"key":"r","ru":"к","symbol":"R","color":"green","label":"резистор"},
    "capacitor": {"key":"c","ru":"с","symbol":"C","color":"purple","label":"конденсатор"},
    "transistor": {"key":"t","ru":"е","symbol":"T","color":"orange","label":"транзистор"},
    "diode": {"key":"d","ru":"в","symbol":"D","color":"yellow","label":"диод"},
    "inductor": {"key":"l","ru":"д","symbol":"L","color":"brown","label":"индуктивность"},
    "vsource": {"key":"v","ru":"м","symbol":"V","color":"red","label":"источник"},
    "ground": {"key":"g","ru":"п","symbol":"G","color":"black","label":"земля"}
}

# -------------------------------------------------
# DATA
# -------------------------------------------------

points = []
center_elements = {}
segments = []

# -------------------------------------------------
# UNDO / REDO
# -------------------------------------------------

history_undo = []
history_redo = []

active_element = "wire"
pending_point = None
hover_point = None
editor_mode = "draw"


def snapshot_state():
    return {
        "points": [tuple(p) for p in points],
        "segments": [dict(s) for s in segments],
        "center_elements": dict(center_elements),
        "active_element": active_element
    }


def restore_state(state):
    global points, segments, center_elements, active_element
    points = [tuple(p) for p in state["points"]]
    segments = [dict(s) for s in state["segments"]]
    center_elements = dict(state.get("center_elements", {}))
    active_element = state.get("active_element", "wire")


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

# -------------------------------------------------
# FIGURE
# -------------------------------------------------

fig, ax = plt.subplots()
manager = plt.get_current_fig_manager()
root = manager.window
root.geometry("1233x839+680+0")

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

    global active_element

    pa = points[a]
    pb = points[b]

    # topology protection: center cannot connect to another center
    if pa[2] == "center" and pb[2] == "center":
        return

    # запрет диагоналей
    if pa[0] != pb[0] and pa[1] != pb[1]:
        return

    # forbid placing element over existing element
    for s in segments:
        if (s["start"] == a and s["end"] == b) or (s["start"] == b and s["end"] == a):
            if s.get("element") != "wire":
                return

    if segment_exists(a, b):
        return

    # block segments that pass through boundary
    for gx, gy, t in points:
        if t != "boundary":
            continue

        if pa[0] == pb[0] and gx == pa[0]:
            if min(pa[1], pb[1]) < gy < max(pa[1], pb[1]):
                return

        if pa[1] == pb[1] and gy == pa[1]:
            if min(pa[0], pb[0]) < gx < max(pa[0], pb[0]):
                return

    element_to_use = active_element

    element_types = {"center","vertex","corner_fwd","corner_back"}

    if points[a][2] in element_types or points[b][2] in element_types:
        search_start = a if points[a][2] in element_types else b
        visited_pts = set()
        stack = [search_start]

        while stack:
            p = stack.pop()

            if p in visited_pts:
                continue

            visited_pts.add(p)

            if points[p][2] == "center" and p in center_elements:
                element_to_use = center_elements[p]
                break

            for s in segments:
                if s["start"] == p or s["end"] == p:
                    other = s["end"] if s["start"] == p else s["start"]

                    if other not in visited_pts:
                        stack.append(other)

    if (points[a][2] == "center" or points[b][2] == "center") and element_to_use == "wire":
        return

    if points[a][2] == "center":
        element_to_use = center_elements.get(a, active_element)
    elif points[b][2] == "center":
        element_to_use = center_elements.get(b, active_element)

    push_state()

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

    for i,(gx, gy, t) in enumerate(points):

        x = gx * GRID_SIZE
        y = gy * GRID_SIZE

        if t == "node":
            if i == hover_point:
                ax.text(x, y, "O", ha="center", va="center", fontsize=12, fontweight="bold")
            else:
                ax.plot(x, y, "ro", markersize=6)

        elif t == "center":
            ax.plot(x, y, "b+", markersize=12, markeredgewidth=2)

        elif t == "vertex":
            ax.text(x, y, "~", ha="center", va="center", fontsize=12, fontweight="bold")

        elif t == "corner_fwd":
            ax.text(x, y, "/", ha="center", va="center", fontsize=12, fontweight="bold")

        elif t == "corner_back":
            ax.text(x, y, "\\", ha="center", va="center", fontsize=12, fontweight="bold")

        elif t == "boundary":
            ax.plot(x, y, "yx", markersize=12, markeredgewidth=2)

# -------------------------------------------------
# CONNECTION HINT
# -------------------------------------------------

def draw_connection_hint():

    if pending_point is None:
        return

    gx, gy, _ = points[pending_point]

    x = gx * GRID_SIZE
    y = gy * GRID_SIZE

    occupied = {"up":False,"down":False,"left":False,"right":False}

    for s in segments:
        if s["start"] == pending_point or s["end"] == pending_point:
            other = s["end"] if s["start"] == pending_point else s["start"]
            ox, oy, _ = points[other]

            if ox == gx:
                if oy < gy:
                    occupied["up"] = True
                if oy > gy:
                    occupied["down"] = True

            if oy == gy:
                if ox < gx:
                    occupied["left"] = True
                if ox > gx:
                    occupied["right"] = True

    offset = GRID_SIZE * 1.2

    if not occupied["up"]:
        ax.text(x, y-offset, "↑", ha="center", va="center", color="gray")

    if not occupied["down"]:
        ax.text(x, y+offset, "↓", ha="center", va="center", color="gray")

    if not occupied["left"]:
        ax.text(x-offset, y, "←", ha="center", va="center", color="gray")

    if not occupied["right"]:
        ax.text(x+offset, y, "→", ha="center", va="center", color="gray")

# -------------------------------------------------
# REDRAW
# -------------------------------------------------

def redraw():

    ax.clear()

    ax.set_xlim(0, VIEW_W)
    ax.set_ylim(VIEW_H, 0)

    ax.set_aspect("equal")

    if background_image is not None:
        ax.imshow(background_image, extent=[0, VIEW_W, VIEW_H, 0], alpha=0.35)

    draw_grid()
    draw_segments()
    draw_points()
    draw_connection_hint()

    if editor_mode == "delete":
        ax.set_title("MODE: DELETE")
    else:
        label = ELEMENTS.get(active_element, {}).get("label", active_element)
        ax.set_title(f"MODE: {label}")

    fig.canvas.draw_idle()

# -------------------------------------------------
# DELETE UTILITIES
# -------------------------------------------------

def swap_delete_point(idx):

    last = len(points) - 1

    # remove segments connected to point
    remove_segments = [i for i,s in enumerate(segments) if s["start"] == idx or s["end"] == idx]

    for i in reversed(remove_segments):
        segments.pop(i)

    # center deletion handled separately

    if idx != last:
        moved = points[last]
        points[idx] = moved

        # update segments referencing last
        for s in segments:
            if s["start"] == last:
                s["start"] = idx
            if s["end"] == last:
                s["end"] = idx

        # update center_elements
        if last in center_elements:
            center_elements[idx] = center_elements[last]
            del center_elements[last]

    points.pop()

    if idx in center_elements:
        del center_elements[idx]


def delete_segment_near(gx, gy):

    for i,s in enumerate(segments):

        p1 = points[s["start"]]
        p2 = points[s["end"]]

        x1,y1 = p1[0],p1[1]
        x2,y2 = p2[0],p2[1]

        if x1 == x2 == gx and min(y1,y2) <= gy <= max(y1,y2):
            push_state()
            segments.pop(i)
            return True

        if y1 == y2 == gy and min(x1,x2) <= gx <= max(x1,x2):
            push_state()
            segments.pop(i)
            return True

    return False


def delete_center_chain(center_idx):

    adj = {i: [] for i,_ in enumerate(points)}
    for s in segments:
        adj[s["start"]].append(s["end"])
        adj[s["end"]].append(s["start"])

    stack = [center_idx]
    chain = set()

    while stack:
        p = stack.pop()
        if p in chain:
            continue

        px,py,ptype = points[p]

        if ptype == "node" and p != center_idx:
            continue

        chain.add(p)

        for nb in adj[p]:
            if nb not in chain:
                stack.append(nb)

    # delete segments inside chain
    for i in reversed(range(len(segments))):
        s = segments[i]
        if s["start"] in chain or s["end"] in chain:
            segments.pop(i)

    # delete points except nodes
    for idx in sorted(chain, reverse=True):
        if idx < len(points) and points[idx][2] != "node":
            swap_delete_point(idx)

# -------------------------------------------------
# ADD POINT
# -------------------------------------------------

def add_point(gx, gy, ptype):

    # forbid placing point directly on existing segment
    for s in segments:
        p1 = points[s["start"]]
        p2 = points[s["end"]]

        x1,y1 = p1[0],p1[1]
        x2,y2 = p2[0],p2[1]

        # vertical segment
        if x1 == x2 == gx and min(y1,y2) < gy < max(y1,y2):
            return None

        # horizontal segment
        if y1 == y2 == gy and min(x1,x2) < gx < max(x1,x2):
            return None

    idx = find_point(gx, gy)

    if idx is not None:
        return idx

    push_state()

    points.append((gx, gy, ptype))
    idx_new = len(points) - 1

    if ptype == "center":
        center_elements[idx_new] = active_element

    return idx_new

# -------------------------------------------------
# MOUSE
# -------------------------------------------------

def on_move(event):

    global hover_point

    if event.xdata is None:
        hover_point = None
        return

    gx, gy = snap(event.xdata, event.ydata)

    hover_point = find_point(gx, gy)

    redraw()


def on_mouse(event):

    global pending_point

    if event.xdata is None:
        return

    gx, gy = snap(event.xdata, event.ydata)

    # DELETE MODE
    if editor_mode == "delete" and event.button == 1:

        idx = find_point(gx, gy)

        if idx is not None:

            push_state()

            if points[idx][2] == "center":
                delete_center_chain(idx)
            else:
                swap_delete_point(idx)

            redraw()
            return

        if delete_segment_near(gx, gy):
            redraw()
            return

        return

    if event.button == 1:

        if event.key in ("control","ctrl"):
            idx = add_point(gx, gy, "corner_fwd")
        elif event.key == "shift":
            idx = add_point(gx, gy, "boundary")
        elif event.key in ("alt","alt+graph"):
            idx = add_point(gx, gy, "vertex")
        else:
            idx = add_point(gx, gy, "node")

        redraw()
        return

    if event.button == 3:

        if event.key in ("control","ctrl"):

            add_point(gx, gy, "corner_back")
            redraw()
            return

        if event.key in ("alt","alt+graph"):

            add_point(gx, gy, "center")
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

    adj = {i: [] for i,_ in enumerate(points)}
    for s in segments:
        a = s["start"]
        b = s["end"]
        adj[a].append(b)
        adj[b].append(a)

    visited = set()

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

        element = center_elements.get(center_idx,"wire")

        cx,cy,_ = points[center_idx]

        horiz = False
        vert = False

        for nb in adj[center_idx]:
            x,y,_ = points[nb]
            if y == cy:
                horiz = True
            if x == cx:
                vert = True

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

        visited |= {p for p in chain if points[p][2] != "node"}

    for s in segments:

        if s["start"] in visited or s["end"] in visited:
            continue

        p1 = points[s["start"]]
        p2 = points[s["end"]]

        x1,y1 = p1[0],p1[1]
        x2,y2 = p2[0],p2[1]

        element = s.get("element","wire")

        # draw base wire first
        if x1 == x2:
            for y in range(min(y1,y2)+1,max(y1,y2)):
                grid[(x1,y)] = "|"

        elif y1 == y2:
            for x in range(min(x1,x2)+1,max(x1,x2)):
                grid[(x,y1)] = "-"

        # overlay element on top of wire
        if element != "wire":
            orientation = "horizontal" if y1 == y2 else "vertical"
            sym = element_symbol(element, orientation)

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            if sym.startswith("["):
                grid[(cx-1,cy)] = "["
                grid[(cx,cy)] = sym[1]
                grid[(cx+1,cy)] = "]"
            elif len(sym) == 3:
                # protect node position
                if grid.get((cx,cy)) == "o":
                    continue
                if x1 == x2:
                    grid[(cx,cy-1)] = "-"
                    grid[(cx,cy)] = sym[1]
                    grid[(cx,cy+1)] = "-"
                else:
                    grid[(cx-1,cy)] = "-"
                    grid[(cx,cy)] = sym[1]
                    grid[(cx+1,cy)] = "-"
            else:
                grid[(cx,cy)] = sym

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
            vert = (gx,gy-1) in grid or (gx,gy+1) in grid
            horiz = (gx-1,gy) in grid or (gx+1,gy) in grid
            if vert and not horiz:
                grid[(gx,gy)] = "|"
            else:
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
# SAVE ASCII
# -------------------------------------------------

def save_scheme():

    ascii_scheme = generate_ascii()

    with open("scheme.js", "w", encoding="utf-8") as f:
        f.write("export const scheme = `\n" + ascii_scheme + "\n`;\n")

    print("scheme.js updated")

# -------------------------------------------------
# KEYBOARD
# -------------------------------------------------

def save_project():

    data = {
        "points": points,
        "segments": segments,
        "center_elements": center_elements
    }

    with open("project.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("project.json saved")


def load_project():

    global points, segments, center_elements

    try:
        with open("project.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        points = [tuple(p) for p in data.get("points", [])]
        segments = [dict(s) for s in data.get("segments", [])]
        center_elements = {int(k): v for k,v in data.get("center_elements", {}).items()}

        redraw()
        print("project.json loaded")
    except FileNotFoundError:
        print("project.json not found")


def load_background():

    global background_image

    try:
        background_image = plt.imread("schematic.png")
        redraw()
        print("schematic.png loaded")
    except FileNotFoundError:
        print("schematic.png not found")


def clear_background():

    global background_image

    background_image = None
    redraw()


def on_key(event):

    global active_element, pending_point, editor_mode

    k = event.key

    if k in ("x","ч"):
        editor_mode = "delete" if editor_mode != "delete" else "draw"
        redraw()
        return

    # Functional hotkeys
    if k == "f1":
        save_scheme()
        return

    if k == "f2":
        editor_mode = "draw"
        undo()
        return

    if k == "f3":
        editor_mode = "draw"
        redo()
        return

    if k == "f4":
        save_project()
        return

    if k == "f5":
        load_project()
        return

    if k == "f6":
        load_background()
        return

    if k == "f7":
        clear_background()
        return

    # Cancel pending connection
    if k == "escape":
        pending_point = None
        return

    # Element selection
    for name, data in ELEMENTS.items():
        if k in (data.get("key"), data.get("ru")):
            active_element = name
            break

    redraw()

fig.canvas.mpl_connect("motion_notify_event", on_move)
fig.canvas.mpl_connect("button_press_event", on_mouse)
fig.canvas.mpl_connect("key_press_event", on_key)

# -------------------------------------------------
# START
# -------------------------------------------------

redraw()

plt.show()
