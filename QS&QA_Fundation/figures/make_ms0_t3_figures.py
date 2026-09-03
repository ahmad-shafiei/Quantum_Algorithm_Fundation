#!/usr/bin/env python3
"""Generate the MS0-T3 layout / epipolar schematics as TikZ code.

Every coordinate in the emitted figures is computed from the design parameters
below with a real pinhole model, so image planes are exactly perpendicular to
their optical axis, FOV cross-sections are true frustum slices, and the epipoles
are the actual intersections of the baseline with each image plane.

Usage (from the report directory):

    python figures/make_ms0_t3_figures.py

Outputs (same directory):
    ms0_t3_stereo_3d.tikz     3D layout + epipolar geometry
    ms0_t3_elevation.tikz     vertical section along one optical axis (VFOV)
    ms0_t3_topview.tikz       horizontal slice of both FOVs at SLICE_Z (HFOV)
    ms0_t3_image_planes.tikz  the two sensor views (pixels, epipolar lines)
    ms0_t3_values.tex         computed numbers as LaTeX macros
    ms0_t3_values.json        the same numbers for docs / reuse
"""

from __future__ import annotations

import json
import math
from pathlib import Path

# ---------------------------------------------------------------------------
# design parameters (keep in sync with docs/architecture.md)
# ---------------------------------------------------------------------------
BASELINE = 60.0             # Cam A <-> Cam B distance [m]
MOUNT_H = 6.0               # optical-center height above ground [m]
AIM = (0.0, 70.0, 45.0)     # both optical axes are aimed at this point [m]
HFOV_DEG = 70.0             # horizontal field of view [deg]
VFOV_DEG = 40.0             # vertical field of view [deg]
TARGET = (9.0, 58.0, 48.0)  # 3D target X used in the schematics [m]
F_DRAW = 12.0               # image-plane distance in the drawing [m] (exaggerated)
CORE_RANGE = 200.0          # design core range used for the top view [m]
SLICE_Z = 45.0              # altitude of the exact FOV-overlap slice [m]
PIX_W, PIX_H = 1920, 1080   # sensor size used to report pixel coordinates
ALT_BAND = (20.0, 150.0)    # MS0-T2 altitude envelope [m]
RANGE_MARKS = (50.0, 100.0, 200.0)
# LaTeX macro names cannot contain digits, so each range mark gets a word tag.
RANGE_TAGS = {50: "Fifty", 100: "Hundred", 200: "TwoHundred"}

OUT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# minimal vector helpers (stdlib only on purpose: no numpy dependency)
# ---------------------------------------------------------------------------


def add(a, b):
    return tuple(ai + bi for ai, bi in zip(a, b))


def sub(a, b):
    return tuple(ai - bi for ai, bi in zip(a, b))


def mul(a, s):
    return tuple(ai * s for ai in a)


def dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    return mul(a, 1.0 / norm(a))


def lerp(a, b, t):
    return add(mul(a, 1.0 - t), mul(b, t))


# ---------------------------------------------------------------------------
# camera model
# ---------------------------------------------------------------------------


class Camera:
    """Pinhole camera with an orthonormal frame (right, up, forward)."""

    def __init__(self, name, center, aim, hfov_deg=HFOV_DEG, vfov_deg=VFOV_DEG):
        self.name = name
        self.O = center
        self.z = unit(sub(aim, center))                 # optical axis
        self.x = unit((self.z[1], -self.z[0], 0.0))     # image right (horizontal)
        self.y = cross(self.x, self.z)                  # image up
        self.ta = math.tan(math.radians(hfov_deg / 2.0))
        self.tb = math.tan(math.radians(vfov_deg / 2.0))

    # -- angles -------------------------------------------------------------
    @property
    def pitch_deg(self):
        return math.degrees(math.atan2(self.z[2], math.hypot(self.z[0], self.z[1])))

    @property
    def toe_in_deg(self):
        """Azimuth of the optical axis measured from +Y (the inward direction)."""
        return math.degrees(math.atan2(abs(self.z[0]), self.z[1]))

    # -- projection ---------------------------------------------------------
    def half_sizes(self, f=F_DRAW):
        return f * self.ta, f * self.tb

    def project(self, P, f=F_DRAW):
        """Metric image coordinates (u, v) on the plane at distance f."""
        return self.project_dir(sub(P, self.O), f)

    def project_dir(self, direction, f=F_DRAW):
        w = dot(direction, self.z)
        return f * dot(direction, self.x) / w, f * dot(direction, self.y) / w, w

    def image_point(self, u, v, f=F_DRAW):
        """Back to 3D: the point (u, v) of the image plane at distance f."""
        return add(add(self.O, mul(self.z, f)), add(mul(self.x, u), mul(self.y, v)))

    def pixels(self, u, v, f=F_DRAW):
        """Metric image coordinates -> pixel coordinates (origin top-left)."""
        hw, hh = self.half_sizes(f)
        return PIX_W / 2.0 * (1.0 + u / hw), PIX_H / 2.0 * (1.0 - v / hh)

    def frustum_corners(self, rng):
        """Corners of the frustum cross-section at axial distance rng."""
        out = []
        for su, sv in ((+1, +1), (+1, -1), (-1, -1), (-1, +1)):
            d = add(self.z, add(mul(self.x, su * self.ta), mul(self.y, sv * self.tb)))
            out.append(add(self.O, mul(d, rng)))
        return out

    def halfspaces(self, max_range=None):
        """Inward half-spaces (n, d) with dot(n, P) + d >= 0 inside the frustum."""
        planes = [
            add(mul(self.z, self.ta), mul(self.x, -1.0)),
            add(mul(self.z, self.ta), self.x),
            add(mul(self.z, self.tb), mul(self.y, -1.0)),
            add(mul(self.z, self.tb), self.y),
        ]
        hs = [(n, -dot(n, self.O)) for n in planes]
        if max_range is not None:
            hs.append((mul(self.z, -1.0), dot(self.z, self.O) + max_range))
        return hs

    def epipole_3d(self, other, f=F_DRAW):
        """Where the line O_self -> O_other pierces this image plane."""
        d = sub(other.O, self.O)
        return add(self.O, mul(d, f / dot(d, self.z)))


CAM_A = Camera("A", (-BASELINE / 2.0, 0.0, MOUNT_H), AIM)
CAM_B = Camera("B", (+BASELINE / 2.0, 0.0, MOUNT_H), AIM)


# ---------------------------------------------------------------------------
# geometry utilities
# ---------------------------------------------------------------------------


def clip_polygon(poly, halfplanes):
    """Sutherland-Hodgman clip of a 2D polygon by lines a*x + b*y + c >= 0."""
    for a, b, c in halfplanes:
        if not poly:
            return []
        out = []
        n = len(poly)
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]
            fp = a * p[0] + b * p[1] + c
            fq = a * q[0] + b * q[1] + c
            if fp >= 0.0:
                out.append(p)
            if (fp > 0.0 > fq) or (fp < 0.0 < fq):
                t = fp / (fp - fq)
                out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
        poly = out
    return poly


def slice_halfplanes(halfspaces, z_level):
    """Restrict 3D half-spaces to the horizontal plane Z = z_level."""
    return [(n[0], n[1], n[2] * z_level + d) for n, d in halfspaces]


def polygon_area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def centroid(poly):
    return (
        sum(p[0] for p in poly) / len(poly),
        sum(p[1] for p in poly) / len(poly),
    )


def clip_segment_to_box(p, q, half_w, half_h):
    """Clip the 2D segment p->q to the rectangle [-hw, hw] x [-hh, hh]."""
    x0, y0 = p
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for num, den in (
        (half_w - x0, dx), (x0 + half_w, -dx),
        (half_h - y0, dy), (y0 + half_h, -dy),
    ):
        if abs(den) < 1e-12:
            if num < 0.0:
                return None
            continue
        t = num / den
        if den > 0.0:
            t1 = min(t1, t)
        else:
            t0 = max(t0, t)
        if t0 > t1:
            return None
    return ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))


def clip_line_to_box(p, q, half_w, half_h):
    """Clip the infinite 2D line through p and q to the sensor rectangle."""
    d = sub(q, p)
    if norm(d) < 1e-12:
        return None
    d = mul(d, 4.0 * (half_w + half_h) / norm(d))
    return clip_segment_to_box(sub(p, d), add(p, d), half_w, half_h)


def arc_points(origin, v_from, v_to, radius, n=16):
    """Points of the great-circle arc between two directions, at given radius."""
    a, b = unit(v_from), unit(v_to)
    return [add(origin, mul(unit(lerp(a, b, i / n)), radius)) for i in range(n + 1)]


# ---------------------------------------------------------------------------
# TikZ canvas
# ---------------------------------------------------------------------------

COLORS = """\\definecolor{pmCamA}{RGB}{21,101,192}
\\definecolor{pmCamB}{RGB}{216,110,20}
\\definecolor{pmOvl}{RGB}{27,132,72}
\\definecolor{pmEpi}{RGB}{123,62,166}
\\definecolor{pmGround}{RGB}{120,120,120}
\\definecolor{pmTarget}{RGB}{25,25,25}"""


class Canvas:
    """Collects TikZ commands with an explicit painting order."""

    def __init__(self, project, unit_cm, depth=None):
        self.project = project
        self.unit_cm = unit_cm
        self.depth = depth or (lambda P: 0.0)
        self.items = []
        self._seq = 0

    # -- coordinates --------------------------------------------------------
    def xy(self, P):
        sx, sy = self.project(P)
        return sx * self.unit_cm, sy * self.unit_cm

    def c(self, P):
        x, y = self.xy(P)
        return f"({x:.3f},{y:.3f})"

    # -- primitives ---------------------------------------------------------
    def raw(self, z, code):
        self._seq += 1
        self.items.append((z, self._seq, code))

    def line(self, z, pts, opts="", close=False):
        path = " -- ".join(self.c(p) for p in pts)
        if close:
            path += " -- cycle"
        self.raw(z, f"\\draw[{opts}] {path};")

    def fill(self, z, pts, opts=""):
        if len(pts) < 3:
            return
        path = " -- ".join(self.c(p) for p in pts) + " -- cycle"
        self.raw(z, f"\\fill[{opts}] {path};")

    def dot(self, z, P, opts="fill=black", r=1.7):
        self.raw(z, f"\\node[circle,inner sep={r}pt,{opts}] at {self.c(P)} {{}};")

    def text(self, z, P, label, opts="anchor=center,font=\\scriptsize"):
        self.raw(z, f"\\node[{opts}] at {self.c(P)} {{{label}}};")

    def arrow(self, z, p, q, opts=""):
        self.raw(z, f"\\draw[-{{Latex[length=2mm]}},{opts}] {self.c(p)} -- {self.c(q)};")

    def dim(self, z, p, q, label, opts="", label_opts="font=\\scriptsize"):
        self.raw(
            z,
            f"\\draw[{{Latex[length=1.8mm]}}-{{Latex[length=1.8mm]}},{opts}] "
            f"{self.c(p)} -- node[midway,fill=white,inner sep=1pt,{label_opts}] "
            f"{{{label}}} {self.c(q)};",
        )

    def box(self, z, center, axes, halfs, opts_dark, opts_light):
        """Draw a small 3D box, back faces first (painter's algorithm)."""
        faces = []
        for axis in range(3):
            for sign in (-1, +1):
                other = [i for i in range(3) if i != axis]
                corners = []
                for su, sv in ((-1, -1), (+1, -1), (+1, +1), (-1, +1)):
                    off = mul(axes[axis], sign * halfs[axis])
                    off = add(off, mul(axes[other[0]], su * halfs[other[0]]))
                    off = add(off, mul(axes[other[1]], sv * halfs[other[1]]))
                    corners.append(add(center, off))
                cen = mul(add(add(corners[0], corners[1]), add(corners[2], corners[3])), 0.25)
                faces.append((self.depth(cen), corners))
        faces.sort(key=lambda f: f[0])
        for i, (_, corners) in enumerate(faces):
            self.fill(z, corners, opts_light if i >= 3 else opts_dark)
            self.line(z, corners, "black!70,line width=0.25pt", close=True)

    # -- output -------------------------------------------------------------
    def emit(self, pic_opts=""):
        body = "\n".join(
            code for _, _, code in sorted(self.items, key=lambda t: (t[0], t[1]))
        )
        return (
            "% AUTO-GENERATED by figures/make_ms0_t3_figures.py -- do not edit by hand.\n"
            f"{COLORS}\n"
            f"\\begin{{tikzpicture}}[{pic_opts}]\n{body}\n\\end{{tikzpicture}}\n"
        )


def lr(text):
    return f"\\lr{{{text}}}"


def deg(value):
    return lr(f"{value:.1f}$^\\circ$")


# ---------------------------------------------------------------------------
# figure 1: 3D layout + epipolar geometry
# ---------------------------------------------------------------------------

VIEW_AZ, VIEW_EL = -80.0, 26.0


def make_view(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    view_dir = (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))
    right = (-math.sin(a), math.cos(a), 0.0)
    up = cross(view_dir, right)

    def project(P):
        return dot(P, right), dot(P, up)

    def depth(P):
        return -dot(P, view_dir)

    return project, depth


def figure_3d():
    project, depth = make_view(VIEW_AZ, VIEW_EL)
    cv = Canvas(project, 0.138, depth)
    cams = (CAM_A, CAM_B)
    color = {"A": "pmCamA", "B": "pmCamB"}

    # ground plane + grid ---------------------------------------------------
    g_x0, g_x1, g_y0, g_y1 = -46.0, 46.0, -14.0, 72.0
    ground = [(g_x0, g_y0, 0.0), (g_x1, g_y0, 0.0), (g_x1, g_y1, 0.0), (g_x0, g_y1, 0.0)]
    cv.fill(5, ground, "black!4")
    cv.line(5, ground, "pmGround!45,line width=0.3pt", close=True)
    for gx in range(int(g_x0) + 6, int(g_x1), 10):
        cv.line(6, [(gx, g_y0, 0.0), (gx, g_y1, 0.0)], "pmGround!20,line width=0.2pt")
    for gy in range(int(g_y0) + 4, int(g_y1), 10):
        cv.line(6, [(g_x0, gy, 0.0), (g_x1, gy, 0.0)], "pmGround!20,line width=0.2pt")

    # world origin + axis triad (offset so it never collides with the epipoles)
    cv.line(7, [(-2.5, 0.0, 0.0), (2.5, 0.0, 0.0)], "black!70,line width=0.4pt")
    cv.line(7, [(0.0, -2.5, 0.0), (0.0, 2.5, 0.0)], "black!70,line width=0.4pt")
    cv.text(7, (-5.0, 0.0, 0.0), "$O$", "anchor=east,font=\\scriptsize")
    triad = (-52.0, -16.0, 0.0)
    for vec, name in (((9.0, 0, 0), "X"), ((0, 9.0, 0), "Y"), ((0, 0, 9.0), "Z")):
        cv.arrow(8, triad, add(triad, vec), "black,line width=0.5pt")
        cv.text(8, add(triad, mul(vec, 1.34)), f"$+{name}$", "font=\\tiny")
    cv.text(8, add(triad, (0.0, -5.0, 0.0)), lr("world frame [m]"), "font=\\tiny,anchor=north")

    # epipolar plane O_A O_B X ---------------------------------------------
    tri = [CAM_A.O, CAM_B.O, TARGET]
    cv.fill(10, tri, "pmEpi,opacity=0.13")
    cv.line(10, tri, "pmEpi!75,line width=0.4pt", close=True)
    cv.text(
        11,
        lerp(lerp(CAM_A.O, CAM_B.O, 0.72), TARGET, 0.42),
        lr("epipolar plane") + " $O_A O_B X$",
        "anchor=west,font=\\scriptsize,text=pmEpi!85!black",
    )

    # target ground drop line ----------------------------------------------
    tgt_ground = (TARGET[0], TARGET[1], 0.0)
    cv.line(12, [TARGET, tgt_ground], "black!45,dotted,line width=0.4pt")
    cv.line(12, [add(tgt_ground, (-2.0, 0, 0)), add(tgt_ground, (2.0, 0, 0))],
            "black!45,line width=0.3pt")
    cv.line(12, [add(tgt_ground, (0, -2.0, 0)), add(tgt_ground, (0, 2.0, 0))],
            "black!45,line width=0.3pt")

    # masts + mount height --------------------------------------------------
    for cam in cams:
        base = (cam.O[0], cam.O[1], 0.0)
        cv.line(20, [base, cam.O], "black!65,line width=1.2pt")
        cv.fill(
            20,
            [add(base, (-1.6, -1.6, 0.0)), add(base, (1.6, -1.6, 0.0)),
             add(base, (1.6, 1.6, 0.0)), add(base, (-1.6, 1.6, 0.0))],
            "black!35",
        )
    h_top = add(CAM_A.O, (-8.0, 0.0, 0.0))
    h_bot = (CAM_A.O[0] - 8.0, CAM_A.O[1], 0.0)
    cv.line(20, [h_bot, (CAM_A.O[0], CAM_A.O[1], 0.0)], "black!45,dotted,line width=0.3pt")
    cv.line(20, [h_top, CAM_A.O], "black!45,dotted,line width=0.3pt")
    cv.dim(21, h_bot, h_top, f"$h={MOUNT_H:.0f}$ m")

    # baseline (= epipolar axis) + epipoles on it ---------------------------
    cv.line(22, [CAM_A.O, CAM_B.O], "black,line width=0.6pt")
    for cam in cams:
        cv.line(22, [(cam.O[0], cam.O[1], 0.0), (cam.O[0], -14.0, 0.0)],
                "black!40,dotted,line width=0.3pt")
    cv.dim(22, (CAM_A.O[0], -14.0, 0.0), (CAM_B.O[0], -14.0, 0.0),
           f"$B={BASELINE:.0f}$ m", "black!70,line width=0.4pt")
    cv.text(
        22, lerp(CAM_A.O, CAM_B.O, 0.24), lr("baseline = epipolar axis"),
        "anchor=south,yshift=2pt,font=\\tiny,text=black!65",
    )
    for cam, other in ((CAM_A, CAM_B), (CAM_B, CAM_A)):
        e3 = cam.epipole_3d(other)
        cv.dot(24, e3, "fill=pmEpi", 1.6)
        # both labels above the baseline: the two epipoles sit only ~8 m apart
        off = (0.0, 0.0, 5.0)
        anchor = "south west" if cam.name == "A" else "south east"
        cv.line(24, [e3, add(e3, off)], "pmEpi!55,line width=0.3pt")
        cv.text(
            24, add(e3, off), f"$e_{cam.name}$",
            f"anchor={anchor},font=\\scriptsize,text=pmEpi!85!black",
        )

    # optical axes (pitch arc only on Cam A: Cam B is mirrored) -------------
    for cam in cams:
        col = color[cam.name]
        cv.arrow(30, cam.O, add(cam.O, mul(cam.z, 44.0)),
                 f"{col}!80,dash pattern=on 3pt off 2pt,line width=0.5pt")
        cv.text(
            31, add(cam.O, mul(cam.z, 46.0)), lr(f"optical axis {cam.name}"),
            f"anchor=south,font=\\tiny,text={col}",
        )
    horiz = unit((CAM_A.z[0], CAM_A.z[1], 0.0))
    cv.line(30, [CAM_A.O, add(CAM_A.O, mul(horiz, 30.0))], "black!45,dotted,line width=0.4pt")
    cv.line(30, arc_points(CAM_A.O, horiz, CAM_A.z, 23.0), "black!60,line width=0.4pt")
    cv.text(
        30, arc_points(CAM_A.O, horiz, CAM_A.z, 30.0)[4],
        lr("pitch ") + deg(CAM_A.pitch_deg),
        "anchor=north west,font=\\tiny",
    )

    # image planes, epipolar lines, image points ----------------------------
    for cam, other in ((CAM_A, CAM_B), (CAM_B, CAM_A)):
        col = color[cam.name]
        hw, hh = cam.half_sizes()
        rect = [cam.image_point(u, v) for u, v in
                ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        cv.fill(40, rect, f"{col},opacity=0.20")
        cv.line(40, rect, f"{col}!80,line width=0.5pt", close=True)
        side = -1.0 if cam.name == "A" else 1.0
        cv.text(
            41, cam.image_point(side * hw * 1.06, -hh * 0.75),
            lr(f"image plane {cam.name}"),
            f"anchor={'east' if side < 0 else 'west'},font=\\tiny,text={col}",
        )
        cv.dot(42, cam.image_point(0.0, 0.0), f"fill={col}!60!black", 1.0)
        cv.text(
            42, cam.image_point(hw * 0.16, -hh * 0.28), f"$c_{cam.name}$",
            "anchor=north west,font=\\tiny",
        )

        # epipolar line: intersection of plane O_A O_B X with this image plane
        ue, ve, _ = cam.project_dir(sub(other.O, cam.O))
        ux, vx, _ = cam.project(TARGET)
        seg = clip_line_to_box((ux, vx), (ue, ve), hw, hh)
        if seg:
            cv.line(43, [cam.image_point(*seg[0]), cam.image_point(*seg[1])],
                    "pmEpi,line width=0.7pt")
            exit_uv = min(seg, key=lambda s: norm(sub((ue, ve), s)))
            cv.line(43, [cam.image_point(*exit_uv), cam.epipole_3d(other)],
                    "pmEpi!60,dash pattern=on 2pt off 1.5pt,line width=0.4pt")
        cv.dot(44, cam.image_point(ux, vx), "fill=red!80!black", 1.4)
        cv.text(
            44, cam.image_point(ux - hw * 0.30, vx + hh * 0.62), f"$x_{cam.name}$",
            "anchor=center,font=\\scriptsize",
        )

        # viewing ray O -> x -> X
        cv.line(50, [cam.O, TARGET], f"{col}!85!black,line width=0.6pt")

    # camera bodies + optical centres --------------------------------------
    for cam in cams:
        cv.box(52, add(cam.O, mul(cam.z, -2.0)), (cam.x, cam.y, cam.z),
               (1.8, 1.3, 2.0), "black!55", "black!30")
        cv.line(53, [cam.O, add(cam.O, mul(cam.z, 1.6))], "black!75,line width=1.4pt")
        cv.dot(54, cam.O, "fill=black", 1.5)
        anchor = "east" if cam.name == "A" else "west"
        dx = -5.0 if cam.name == "A" else 5.0
        cv.text(
            54, add(cam.O, (dx, -6.0, 7.0)),
            f"$O_{cam.name}$ " + lr(f"(Cam {cam.name})"), f"anchor={anchor},font=\\scriptsize",
        )

    # target glyph ---------------------------------------------------------
    r = 2.6
    for su, sv in ((+1, +1), (+1, -1), (-1, +1), (-1, -1)):
        arm = add(TARGET, (su * r, sv * r, 0.0))
        cv.line(58, [TARGET, arm], "pmTarget,line width=0.7pt")
        cv.raw(
            58,
            f"\\draw[pmTarget,line width=0.5pt] {cv.c(arm)} circle "
            f"[x radius={r * 0.60 * cv.unit_cm:.3f}cm, y radius={r * 0.26 * cv.unit_cm:.3f}cm];",
        )
    cv.dot(59, TARGET, "fill=pmTarget", 2.0)
    cv.text(
        59, add(TARGET, (0.0, 0.0, 6.0)), lr("target") + " $X$",
        "anchor=south,font=\\scriptsize",
    )

    return cv.emit("x=1cm,y=1cm,line cap=round,line join=round")


# ---------------------------------------------------------------------------
# figure 2: vertical section along the optical axis of Cam A (VFOV coverage)
# ---------------------------------------------------------------------------


def figure_elevation():
    cv = Canvas(lambda P: (P[0], P[1]), 0.052)
    pitch = CAM_A.pitch_deg
    lo = math.radians(pitch - VFOV_DEG / 2.0)
    hi = math.radians(pitch + VFOV_DEG / 2.0)
    r_max, z_max = 250.0, 175.0

    def alt(r, ang):
        return MOUNT_H + r * math.tan(ang)

    # FOV band clipped to the drawing window
    wedge = clip_polygon(
        [(0.0, 0.0), (r_max, 0.0), (r_max, z_max), (0.0, z_max)],
        [
            (-math.tan(lo), 1.0, -MOUNT_H),   # above the lower FOV edge
            (math.tan(hi), -1.0, MOUNT_H),    # below the upper FOV edge
        ],
    )
    cv.fill(10, wedge, "pmCamA,opacity=0.15")
    cv.line(10, wedge, "pmCamA!70,line width=0.4pt", close=True)

    # MS0-T2 altitude envelope
    z0, z1 = ALT_BAND
    cv.fill(6, [(0.0, z0), (r_max, z0), (r_max, z1), (0.0, z1)], "pmOvl,opacity=0.09")
    for zz, anch in ((z0, "south"), (z1, "north")):
        cv.line(7, [(0.0, zz), (r_max, zz)], "pmOvl!70!black,dashed,line width=0.35pt")
        cv.text(
            7, (r_max - 3.0, zz), lr(f"{zz:.0f} m AGL"),
            f"anchor={anch} east,font=\\tiny,text=pmOvl!55!black",
        )

    # ground hatch
    cv.raw(
        5,
        "\\fill[pattern=north east lines,pattern color=black!30] "
        f"{cv.c((-18.0, -7.0))} rectangle {cv.c((r_max, 0.0))};",
    )

    # axes
    cv.arrow(30, (-18.0, 0.0), (r_max + 10.0, 0.0), "black,line width=0.5pt")
    cv.arrow(30, (0.0, -7.0), (0.0, z_max + 10.0), "black,line width=0.5pt")
    cv.text(30, (r_max + 12.0, 0.0), lr("ground range $r$ [m]"), "anchor=west,font=\\scriptsize")
    cv.text(30, (0.0, z_max + 13.0), lr("altitude $Z$ [m]"), "anchor=south,font=\\scriptsize")
    for rr in RANGE_MARKS:
        cv.line(30, [(rr, -3.0), (rr, 3.0)], "black,line width=0.4pt")
        cv.text(30, (rr, -6.0), lr(f"{rr:.0f}"), "anchor=north,font=\\tiny")
    for zz in (50.0, 100.0, 150.0):
        cv.line(30, [(-3.0, zz), (3.0, zz)], "black,line width=0.4pt")
        cv.text(30, (-5.0, zz), lr(f"{zz:.0f}"), "anchor=east,font=\\tiny")

    # camera + mount height
    cv.line(31, [(0.0, 0.0), (0.0, MOUNT_H)], "black!65,line width=1.2pt")
    cv.raw(
        32,
        f"\\fill[black!55,rotate around={{{pitch:.2f}:{cv.c((0.0, MOUNT_H))}}}] "
        f"{cv.c((-4.0, MOUNT_H - 2.4))} rectangle {cv.c((2.0, MOUNT_H + 2.4))};",
    )
    cv.dot(33, (0.0, MOUNT_H), "fill=black", 1.4)
    cv.text(33, (-6.0, MOUNT_H + 11.0), "$O_A$", "anchor=east,font=\\scriptsize")
    # the dimension line is short at this scale, so keep the label beside it
    cv.dim(
        33, (-12.0, 0.0), (-12.0, MOUNT_H), f"$h={MOUNT_H:.0f}$",
        label_opts="font=\\scriptsize,anchor=east,fill=none,xshift=-2pt",
    )

    # optical axis + pitch arc + VFOV arc
    axis_r = 228.0
    cv.line(
        20, [(0.0, MOUNT_H), (axis_r, alt(axis_r, math.radians(pitch)))],
        "pmCamA!80!black,dash pattern=on 3pt off 2pt,line width=0.5pt",
    )
    cv.text(
        20, (axis_r - 26.0, alt(axis_r - 26.0, math.radians(pitch)) + 3.0),
        lr("optical axis"), "anchor=south,font=\\tiny,text=pmCamA!70!black",
    )
    cv.line(21, [(0.0, MOUNT_H), (46.0, MOUNT_H)], "black!45,dotted,line width=0.4pt")
    cv.raw(
        21,
        f"\\draw[black!70,line width=0.4pt] {cv.c((34.0, MOUNT_H))} arc"
        f"[start angle=0, end angle={pitch:.2f}, radius={34.0 * cv.unit_cm:.3f}cm];",
    )
    cv.text(
        21, (37.0, MOUNT_H + 3.0), lr("pitch ") + deg(pitch),
        "anchor=west,font=\\tiny,fill=white,inner sep=0.5pt",
    )
    cv.raw(
        21,
        "\\draw[pmCamA!80!black,line width=0.4pt] "
        f"{cv.c((132.0 * math.cos(lo), MOUNT_H + 132.0 * math.sin(lo)))} arc"
        f"[start angle={math.degrees(lo):.2f}, end angle={math.degrees(hi):.2f}, "
        f"radius={132.0 * cv.unit_cm:.3f}cm];",
    )
    # sit the label just outside the arc, below the optical axis, so the two
    # lines never cross the text
    lab_ang = lo + math.radians(5.0)
    cv.text(
        21, (146.0 * math.cos(lab_ang), MOUNT_H + 146.0 * math.sin(lab_ang)),
        lr(
            f"VFOV {VFOV_DEG:.0f}$^\\circ$ "
            f"({math.degrees(lo):.1f}$^\\circ$ to {math.degrees(hi):.1f}$^\\circ$)"
        ),
        "anchor=west,font=\\tiny,text=pmCamA!70!black,fill=white,inner sep=0.5pt",
    )

    # where the FOV edges cross the altitude envelope
    r_low = (z0 - MOUNT_H) / math.tan(lo)
    r_high = (z1 - MOUNT_H) / math.tan(hi)
    cv.dot(25, (r_low, z0), "fill=pmEpi", 1.4)
    cv.text(
        25, (r_low + 7.0, z0 - 13.0),
        lr(f"$Z=20$ m enters the FOV at $r\\approx${r_low:.0f} m"),
        "anchor=west,font=\\tiny,text=pmEpi!85!black,fill=white,inner sep=0.5pt",
    )
    cv.dot(25, (r_high, z1), "fill=pmEpi", 1.4)
    cv.text(
        25, (r_high - 6.0, z1 + 10.0),
        lr(f"$Z=150$ m enters the FOV at $r\\approx${r_high:.0f} m"),
        "anchor=east,font=\\tiny,text=pmEpi!85!black,fill=white,inner sep=0.5pt",
    )

    # covered altitude interval at the core ranges
    for rr in RANGE_MARKS:
        a0, a1 = alt(rr, lo), min(alt(rr, hi), z_max)
        cv.line(26, [(rr, a0), (rr, a1)], "pmCamA!85!black,line width=1.2pt")
        cv.text(
            26, (rr + 4.0, (a0 + a1) / 2.0),
            lr(f"{a0:.0f} to {alt(rr, hi):.0f} m"),
            "anchor=west,font=\\tiny,text=pmCamA!70!black,fill=white,inner sep=0.5pt",
        )

    return cv.emit("x=1cm,y=1cm,line cap=round,line join=round")


# ---------------------------------------------------------------------------
# figure 3: horizontal slice of both FOVs at SLICE_Z (HFOV + overlap)
# ---------------------------------------------------------------------------


def figure_topview():
    cv = Canvas(lambda P: (P[0], P[1]), 0.054)
    window = [(-104.0, -26.0), (104.0, -26.0), (104.0, 232.0), (-104.0, 232.0)]

    cuts = {}
    for cam, col in ((CAM_A, "pmCamA"), (CAM_B, "pmCamB")):
        poly = clip_polygon(window, slice_halfplanes(cam.halfspaces(CORE_RANGE), SLICE_Z))
        cuts[cam.name] = poly
        cv.fill(10, poly, f"{col},opacity=0.18")
        cv.line(10, poly, f"{col}!75,line width=0.4pt", close=True)

    hp = []
    for cam in (CAM_A, CAM_B):
        hp += slice_halfplanes(cam.halfspaces(CORE_RANGE), SLICE_Z)
    overlap = clip_polygon(window, hp)
    cv.fill(14, overlap, "pmOvl,opacity=0.30")
    cv.line(14, overlap, "pmOvl!80,dashed,line width=0.5pt", close=True)

    # FOV labels on the outer corner of each cross-section
    for cam, col in ((CAM_A, "pmCamA"), (CAM_B, "pmCamB")):
        poly = cuts[cam.name]
        sign = 1.0 if cam.name == "A" else -1.0   # Cam A looks toward +X
        outer = max(poly, key=lambda p: sign * p[0] + 0.35 * p[1])
        cx, cy = centroid(poly)
        anchor = (outer[0] * 0.86 + cx * 0.14, outer[1] * 0.86 + cy * 0.14)
        cv.text(
            12, anchor, f"$\\mathrm{{FOV}}_{cam.name}$",
            f"font=\\scriptsize,text={col},fill=white,fill opacity=0.7,text opacity=1,inner sep=1pt",
        )

    # overlap labels
    if overlap:
        y_far = max(p[1] for p in overlap)
        cv.text(
            16, (0.0, y_far - 30.0),
            lr(f"FOV overlap @ $Z={SLICE_Z:.0f}$ m")
            + f"\\\\{lr(f'axial range $\\leq$ {CORE_RANGE:.0f} m')}",
            "align=center,font=\\scriptsize,text=pmOvl!55!black",
        )
        y_near = min(p[1] for p in overlap)
        near_pt = min(overlap, key=lambda p: p[1])
        cv.line(16, [near_pt, (-58.0, y_near - 8.0)], "pmOvl!60,line width=0.3pt")
        cv.text(
            16, (-60.0, y_near - 8.0),
            lr(f"near edge of overlap: $Y\\approx${y_near:.0f} m"),
            "anchor=east,font=\\tiny,text=pmOvl!55!black",
        )

    # window border
    cv.line(4, window, "black!25,dotted,line width=0.4pt", close=True)

    # cameras, optical-axis azimuth, toe-in arcs
    for cam, col in ((CAM_A, "pmCamA"), (CAM_B, "pmCamB")):
        Oxy = (cam.O[0], cam.O[1])
        cv.line(20, [Oxy, (Oxy[0] + cam.z[0] * 195.0, Oxy[1] + cam.z[1] * 195.0)],
                f"{col}!80!black,dash pattern=on 3pt off 2pt,line width=0.5pt")
        a1 = math.degrees(math.atan2(cam.z[1], cam.z[0]))
        # toe-in arc only on Cam A: Cam B is mirrored
        if cam.name == "A":
            cv.line(20, [Oxy, (Oxy[0], Oxy[1] + 62.0)], "black!45,dotted,line width=0.4pt")
            rad = 50.0
            cv.raw(
                21,
                f"\\draw[black!70,line width=0.4pt] {cv.c((Oxy[0], Oxy[1] + rad))} arc"
                f"[start angle=90, end angle={a1:.2f}, radius={rad * cv.unit_cm:.3f}cm];",
            )
            cv.text(
                21, (Oxy[0] - 4.0, Oxy[1] + rad + 4.0),
                lr("toe-in ") + deg(cam.toe_in_deg),
                "anchor=east,font=\\tiny,fill=white,inner sep=0.5pt",
            )
        cv.raw(
            24,
            f"\\fill[black!55,rotate around={{{a1 - 90.0:.2f}:{cv.c(Oxy)}}}] "
            f"{cv.c((Oxy[0] - 4.2, Oxy[1] - 3.0))} rectangle {cv.c((Oxy[0] + 4.2, Oxy[1] + 3.0))};",
        )
        cv.dot(25, Oxy, "fill=black", 1.5)
        cv.text(
            25, (Oxy[0], Oxy[1] - 5.0),
            f"$O_{cam.name}$ " + lr(f"(Cam {cam.name})"),
            "anchor=north,font=\\scriptsize",
        )

    # baseline + target + axes
    cv.dim(26, (CAM_A.O[0], -21.0), (CAM_B.O[0], -21.0), f"$B={BASELINE:.0f}$ m",
           "black,line width=0.5pt")
    for cam in (CAM_A, CAM_B):
        cv.line(26, [(cam.O[0], -6.0), (cam.O[0], -21.0)], "black!35,dotted,line width=0.3pt")
    cv.dot(28, (TARGET[0], TARGET[1]), "fill=pmTarget", 2.0)
    cv.text(
        28, (TARGET[0] + 4.0, TARGET[1] + 4.0),
        "$X$ " + lr(f"($Z={TARGET[2]:.0f}$ m)"),
        "anchor=south west,font=\\scriptsize,fill=white,fill opacity=0.7,"
        "text opacity=1,inner sep=1pt",
    )
    cv.arrow(30, (0.0, 0.0), (116.0, 0.0), "black,line width=0.5pt")
    cv.arrow(30, (0.0, -20.0), (0.0, 222.0), "black,line width=0.5pt")
    cv.text(30, (118.0, 0.0), "$+X$", "anchor=west,font=\\scriptsize")
    cv.text(30, (0.0, 226.0), "$+Y$", "anchor=south,font=\\scriptsize")
    for xx in (-100.0, -50.0, 50.0, 100.0):
        cv.line(30, [(xx, -3.0), (xx, 3.0)], "black,line width=0.4pt")
        # a tick close to a camera gets its label pushed outward, away from the
        # "$O_A$ (Cam A)" caption that hangs below the same axis
        crowded = min(abs(xx - c.O[0]) for c in (CAM_A, CAM_B)) < 30.0
        anchor = "north" if not crowded else ("north east" if xx < 0 else "north west")
        cv.text(30, (xx, -5.0), lr(f"{xx:.0f}"), f"anchor={anchor},font=\\tiny")
    for yy in (50.0, 100.0, 150.0, 200.0):
        cv.line(30, [(-3.0, yy), (3.0, yy)], "black,line width=0.4pt")
        cv.text(30, (-5.0, yy), lr(f"{yy:.0f}"), "anchor=east,font=\\tiny")

    return cv.emit("x=1cm,y=1cm,line cap=round,line join=round"), overlap


# ---------------------------------------------------------------------------
# figure 4: the two sensor views (pixels, epipolar lines, off-frame epipoles)
# ---------------------------------------------------------------------------


def figure_image_planes():
    cv = Canvas(lambda P: (P[0], P[1]), 0.0035)
    gap = 620.0
    # two extra world points, only to show that all epipolar lines share one pencil
    extra_targets = [(0.0, 44.0, 26.0), (-16.0, 92.0, 74.0)]

    for idx, (cam, other) in enumerate(((CAM_A, CAM_B), (CAM_B, CAM_A))):
        ox = idx * (PIX_W + gap)
        col = "pmCamA" if cam.name == "A" else "pmCamB"
        hw, hh = cam.half_sizes()

        def px(u, v, ox=ox, cam=cam):
            a, b = cam.pixels(u, v)
            return (ox + a, b)

        frame = [(ox, 0.0), (ox + PIX_W, 0.0), (ox + PIX_W, PIX_H), (ox, PIX_H)]
        cv.fill(5, frame, f"{col},opacity=0.05")
        cv.line(6, frame, f"{col}!80,line width=0.5pt", close=True)
        cv.text(
            6, (ox + PIX_W / 2.0, -105.0),
            lr(f"image {cam.name} --- Cam {cam.name} sensor {PIX_W}$\\times${PIX_H} px, ")
            + lr(f"HFOV {HFOV_DEG:.0f}$^\\circ$ / VFOV {VFOV_DEG:.0f}$^\\circ$"),
            "anchor=south,font=\\scriptsize",
        )
        # pixel axes
        cv.arrow(6, (ox + 40.0, -40.0), (ox + 300.0, -40.0), "black!60,line width=0.4pt")
        cv.text(6, (ox + 310.0, -40.0), "$u$", "anchor=west,font=\\tiny")
        cv.arrow(6, (ox - 40.0, 40.0), (ox - 40.0, 300.0), "black!60,line width=0.4pt")
        cv.text(6, (ox - 50.0, 310.0), "$v$", "anchor=east,font=\\tiny")

        # principal point
        cv.line(8, [px(-hw * 0.09, 0.0), px(hw * 0.09, 0.0)], "black!60,line width=0.4pt")
        cv.line(8, [px(0.0, -hh * 0.09), px(0.0, hh * 0.09)], "black!60,line width=0.4pt")
        cv.text(8, px(hw * 0.09, -hh * 0.09), f"$c_{cam.name}$",
                "anchor=north west,font=\\tiny")

        ue, ve, _ = cam.project_dir(sub(other.O, cam.O))
        side = 1.0 if ue > 0 else -1.0

        # pencil of epipolar lines: every one of them aims at the same epipole
        for extra in extra_targets:
            u2, v2, _ = cam.project(extra)
            seg = clip_line_to_box((u2, v2), (ue, ve), hw, hh)
            if seg:
                cv.line(9, [px(*seg[0]), px(*seg[1])], "pmEpi!30,line width=0.4pt")

        ux, vx, _ = cam.project(TARGET)
        seg = clip_line_to_box((ux, vx), (ue, ve), hw, hh)
        if seg:
            cv.line(10, [px(*seg[0]), px(*seg[1])], "pmEpi,line width=0.7pt")
            exit_uv = min(seg, key=lambda s: norm(sub((ue, ve), s)))
            exit_px = px(*exit_uv)
            slope = (ve - exit_uv[1]) / max(1e-9, abs(ue - exit_uv[0]))
            cv.arrow(
                10, exit_px,
                (exit_px[0] + side * 130.0, exit_px[1] - slope * 130.0),
                "pmEpi,line width=0.6pt",
            )
            cv.text(
                11, (exit_px[0] - side * 30.0, exit_px[1] - 100.0),
                f"$\\ell_{cam.name} \\to e_{cam.name}$",
                f"anchor={'south east' if side > 0 else 'south west'},font=\\tiny,"
                "text=pmEpi!85!black,fill=white,fill opacity=0.75,text opacity=1,inner sep=1pt",
            )

        u_px, v_px = cam.pixels(ux, vx)
        cv.dot(12, (ox + u_px, v_px), "fill=red!80!black", 1.6)
        cv.text(
            12, (ox + u_px - 40.0, v_px - 60.0),
            f"$x_{cam.name}$", "anchor=south east,font=\\scriptsize",
        )

        ue_px, ve_px = cam.pixels(ue, ve)
        cv.text(
            13, (ox + PIX_W / 2.0, PIX_H + 80.0),
            lr(f"$x_{cam.name}$ = ({u_px:.0f}, {v_px:.0f}) px")
            + "\\\\" + lr(f"$e_{cam.name}$ = ({ue_px:.0f}, {ve_px:.0f}) px")
            + "\\\\" + lr("(outside the sensor)"),
            "anchor=north,align=center,font=\\scriptsize,text=black!75",
        )

    return cv.emit("x=1cm,y=-1cm,line cap=round,line join=round")


# ---------------------------------------------------------------------------
# numbers used in the report text
# ---------------------------------------------------------------------------


def computed_values(overlap_top):
    pitch = CAM_A.pitch_deg
    lo = math.radians(pitch - VFOV_DEG / 2.0)
    hi = math.radians(pitch + VFOV_DEG / 2.0)

    ue, ve, _ = CAM_A.project_dir(sub(CAM_B.O, CAM_A.O))
    hw, hh = CAM_A.half_sizes()
    ue_px, ve_px = CAM_A.pixels(ue, ve)
    uxa, vxa, _ = CAM_A.project(TARGET)
    uxb, vxb, _ = CAM_B.project(TARGET)
    xa_px = CAM_A.pixels(uxa, vxa)
    xb_px = CAM_B.pixels(uxb, vxb)

    # tilt of the epipolar line in image A, relative to a pixel row
    tilt = math.degrees(math.atan2(abs(ve_px - xa_px[1]), abs(ue_px - xa_px[0])))

    conv = math.degrees(math.acos(max(-1.0, min(1.0, dot(CAM_A.z, CAM_B.z)))))
    parallax = math.degrees(
        math.acos(max(-1.0, min(1.0, dot(unit(sub(CAM_A.O, TARGET)), unit(sub(CAM_B.O, TARGET))))))
    )

    epi_a = CAM_A.epipole_3d(CAM_B)
    cov = {str(int(r)): [MOUNT_H + r * math.tan(lo), MOUNT_H + r * math.tan(hi)]
           for r in RANGE_MARKS}

    return {
        "baseline_m": BASELINE,
        "mount_h_m": MOUNT_H,
        "aim_point": list(AIM),
        "target": list(TARGET),
        "hfov_deg": HFOV_DEG,
        "vfov_deg": VFOV_DEG,
        "pitch_deg": pitch,
        "toe_in_deg": CAM_A.toe_in_deg,
        "aim_distance_m": norm(sub(AIM, CAM_A.O)),
        "convergence_deg": conv,
        "parallax_deg": parallax,
        "target_range_a_m": norm(sub(TARGET, CAM_A.O)),
        "target_range_b_m": norm(sub(TARGET, CAM_B.O)),
        "epipole_a_px": [ue_px, ve_px],
        "epipole_a_halfwidths": ue / hw,
        "epipole_a_halfheights": ve / hh,
        "epipole_a_world": list(epi_a),
        "epipole_a_baseline_offset_m": norm(sub(epi_a, CAM_A.O)),
        "epipolar_tilt_deg": tilt,
        "xa_px": list(xa_px),
        "xb_px": list(xb_px),
        "cover_low_deg": math.degrees(lo),
        "cover_high_deg": math.degrees(hi),
        "cover_at_range": cov,
        "r_lower_edge_20m": (ALT_BAND[0] - MOUNT_H) / math.tan(lo),
        "r_upper_edge_150m": (ALT_BAND[1] - MOUNT_H) / math.tan(hi),
        "slice_z_m": SLICE_Z,
        "overlap_area_top_m2": polygon_area(overlap_top),
        "overlap_y_min_m": min(p[1] for p in overlap_top),
        "overlap_y_max_m": max(p[1] for p in overlap_top),
        "core_range_m": CORE_RANGE,
        "f_draw_m": F_DRAW,
    }


def values_tex(v):
    def m(name, value, digits=1):
        return (
            f"\\providecommand{{\\{name}}}{{}}"
            f"\\renewcommand{{\\{name}}}{{{value:.{digits}f}}}"
        )

    lines = [
        "% AUTO-GENERATED by figures/make_ms0_t3_figures.py -- do not edit by hand.",
        m("mstBaseline", v["baseline_m"], 0),
        m("mstMountH", v["mount_h_m"], 0),
        m("mstPitch", v["pitch_deg"], 1),
        m("mstToeIn", v["toe_in_deg"], 1),
        m("mstAimDist", v["aim_distance_m"], 0),
        m("mstConvergence", v["convergence_deg"], 1),
        m("mstParallax", v["parallax_deg"], 1),
        m("mstRangeA", v["target_range_a_m"], 0),
        m("mstRangeB", v["target_range_b_m"], 0),
        m("mstEpiAu", v["epipole_a_px"][0], 0),
        m("mstEpiAv", v["epipole_a_px"][1], 0),
        m("mstEpiWidths", v["epipole_a_halfwidths"], 2),
        m("mstEpiOffset", v["epipole_a_baseline_offset_m"], 1),
        m("mstEpiTilt", v["epipolar_tilt_deg"], 1),
        m("mstXAu", v["xa_px"][0], 0),
        m("mstXAv", v["xa_px"][1], 0),
        m("mstXBu", v["xb_px"][0], 0),
        m("mstXBv", v["xb_px"][1], 0),
        m("mstCoverLow", v["cover_low_deg"], 1),
        m("mstCoverHigh", v["cover_high_deg"], 1),
        m("mstRlowTwenty", v["r_lower_edge_20m"], 0),
        m("mstRhighOneFifty", v["r_upper_edge_150m"], 0),
        m("mstSliceZ", v["slice_z_m"], 0),
        m("mstOverlapArea", v["overlap_area_top_m2"] / 1000.0, 1),
        m("mstOverlapNear", v["overlap_y_min_m"], 0),
        m("mstOverlapFar", v["overlap_y_max_m"], 0),
        m("mstFdraw", v["f_draw_m"], 0),
    ]
    for rr in RANGE_MARKS:
        a0, a1 = v["cover_at_range"][str(int(rr))]
        tag = RANGE_TAGS[int(rr)]
        lines.append(m(f"mstCovLo{tag}", a0, 0))
        lines.append(m(f"mstCovHi{tag}", a1, 0))
    return "\n".join(lines) + "\n"


def main():
    tikz_top, overlap_top = figure_topview()
    outputs = {
        "ms0_t3_stereo_3d.tikz": figure_3d(),
        "ms0_t3_elevation.tikz": figure_elevation(),
        "ms0_t3_topview.tikz": tikz_top,
        "ms0_t3_image_planes.tikz": figure_image_planes(),
    }
    vals = computed_values(overlap_top)
    outputs["ms0_t3_values.tex"] = values_tex(vals)
    outputs["ms0_t3_values.json"] = json.dumps(vals, indent=2) + "\n"

    for name, text in outputs.items():
        (OUT_DIR / name).write_text(text, encoding="utf-8")
        print(f"wrote {name} ({len(text)} chars)")

    print("\n--- geometry check ---")
    print(f"pitch            = {vals['pitch_deg']:.2f} deg")
    print(f"toe-in           = {vals['toe_in_deg']:.2f} deg")
    print(f"convergence      = {vals['convergence_deg']:.2f} deg")
    print(f"parallax at X    = {vals['parallax_deg']:.2f} deg")
    print(f"x_A              = ({vals['xa_px'][0]:.0f}, {vals['xa_px'][1]:.0f}) px")
    print(f"x_B              = ({vals['xb_px'][0]:.0f}, {vals['xb_px'][1]:.0f}) px")
    print(
        f"e_A              = ({vals['epipole_a_px'][0]:.0f}, {vals['epipole_a_px'][1]:.0f}) px"
        f" = {vals['epipole_a_halfwidths']:.2f} half-widths (off-sensor)"
    )
    print(
        "e_A on baseline  = "
        f"{tuple(round(c, 1) for c in vals['epipole_a_world'])} m, "
        f"{vals['epipole_a_baseline_offset_m']:.1f} m from O_A"
    )
    print(f"epipolar tilt    = {vals['epipolar_tilt_deg']:.2f} deg")
    print(
        f"overlap @ Z={vals['slice_z_m']:.0f} m: Y in "
        f"[{vals['overlap_y_min_m']:.0f}, {vals['overlap_y_max_m']:.0f}] m, "
        f"area {vals['overlap_area_top_m2'] / 1000.0:.1f} k m^2"
    )
    for rr in RANGE_MARKS:
        a0, a1 = vals["cover_at_range"][str(int(rr))]
        print(f"r={rr:5.0f} m   -> altitudes {a0:6.1f} .. {a1:6.1f} m")


if __name__ == "__main__":
    main()
