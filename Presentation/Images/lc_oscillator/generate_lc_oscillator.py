"""Draw a scientifically labelled ideal LC circuit using local vector tools.

Run with the bundled Python runtime. Requires local XeLaTeX, TikZ, Poppler
and Pillow; nothing is downloaded or installed. Each revision is immutable.
The PDF is the vector master; SVG and transparent 400 dpi PNG are exported
with pdftocairo. Pillow is used only for the white-background preview.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image


SOURCE = r"""\documentclass[tikz,border=8pt]{standalone}
\usepackage{fontspec}
\setmainfont{TeX Gyre Heros}
\usepackage{amsmath}
\usepackage{unicode-math}
\setmathfont{TeX Gyre Termes Math}
\usetikzlibrary{arrows.meta}
\definecolor{maroon}{HTML}{780404}
\definecolor{orange}{HTML}{E37D00}
\definecolor{charcoal}{HTML}{303238}
\begin{document}
\begin{tikzpicture}[
  x=1.45cm,y=1.45cm,
  line cap=round,line join=round,
  wire/.style={draw=charcoal,line width=1.45pt},
  component/.style={draw=maroon,line width=2.05pt},
  annotation/.style={text=orange,font=\fontsize{15}{18}\selectfont},
  partlabel/.style={text=maroon,font=\fontsize{18}{21}\selectfont},
  text=charcoal
]
% Transparent canvas with balanced margins. No background rectangle is drawn.
\path[use as bounding box] (-1.24,-.90) rectangle (5.15,4.52);

% Both components share exactly two nodes: the upper node and reference ground.
\draw[wire] (0,1.95) -- (0,3.6) -- (4,3.6) -- (4,2.725);
\draw[wire] (0,1.70) -- (0,0) -- (4,0) -- (4,.925);

% Capacitor: upper and lower conducting plates, separated by a real gap.
\draw[component] (-.43,1.95) -- (.43,1.95);
\draw[component] (-.43,1.70) -- (.43,1.70);
\node[partlabel,anchor=west] at (.60,1.825) {$C$};
\node[annotation,anchor=east] at (-.58,2.00) {$+Q$};
\node[annotation,anchor=east] at (-.58,1.65) {$-Q$};

% American inductor symbol: four connected, equally spaced semicircular lobes.
% Each lobe begins and ends at x=4; adjoining lobes are electrically continuous.
\draw[component] (4,2.725)
  arc[start angle=90,end angle=-90,x radius=.26,y radius=.225]
  arc[start angle=90,end angle=-90,x radius=.26,y radius=.225]
  arc[start angle=90,end angle=-90,x radius=.26,y radius=.225]
  arc[start angle=90,end angle=-90,x radius=.26,y radius=.225];
\node[partlabel,anchor=west] at (4.52,1.825) {$L$};

% Current reference enters the positive terminal of L: passive sign convention.
\draw[draw=orange,line width=1.55pt,-{Stealth[length=7pt,width=5.2pt]}]
  (4,3.35) -- (4,2.91);
\node[annotation,anchor=west] at (4.19,3.13) {$I_L(t)$};

% Node flux is an electrical node coordinate, not magnetic flux through the loop.
\fill[charcoal] (2,3.6) circle[radius=2.5pt];
\node[partlabel,anchor=south] at (2,3.83) {$\Phi(t)$};

% Voltage annotation has no connecting line and cannot be mistaken for a branch.
\node[annotation] at (2.10,2.83) {$+$};
\node[annotation] at (2.10,1.825) {$V(t)=\dot{\Phi}(t)$};
\node[annotation] at (2.10,.80) {$-$};

% Common reference node and the conventional three-bar ground symbol.
\fill[charcoal] (2,0) circle[radius=2.5pt];
\draw[wire] (2,0) -- (2,-.35);
\draw[wire] (1.65,-.35) -- (2.35,-.35);
\draw[wire] (1.77,-.48) -- (2.23,-.48);
\draw[wire] (1.89,-.61) -- (2.11,-.61);
\end{tikzpicture}
\end{document}
"""


def run(args: list[str], cwd: Path, log: Path | None = None) -> None:
    completed = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if log is not None:
        log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {args[0]}\n"
            + completed.stdout[-5000:] + completed.stderr[-2000:]
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="v1")
    parser.add_argument("--dpi", type=int, default=400)
    args = parser.parse_args()
    if not args.revision.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Revision must contain only letters, numbers, - or _.")
    output = Path(__file__).resolve().parent
    build = output / f"build_{args.revision}"
    stem = f"lc_circuit_{args.revision}"
    png = output / f"{stem}.png"
    svg = output / f"{stem}.svg"
    preview = output / f"{stem}_white_preview.png"
    manifest_path = output / f"manifest_{args.revision}.json"
    if any(path.exists() for path in (build, png, svg, preview, manifest_path)):
        raise FileExistsError("Revision already exists; choose a new --revision.")
    xelatex, pdftocairo = shutil.which("xelatex"), shutil.which("pdftocairo")
    if not xelatex or not pdftocairo:
        raise RuntimeError("Local XeLaTeX and pdftocairo are required.")
    build.mkdir()
    tex = build / f"{stem}.tex"
    tex.write_text(SOURCE, encoding="utf-8")
    run([xelatex, "-interaction=nonstopmode", "-halt-on-error", tex.name],
        build, build / "compile_log.txt")
    pdf = build / f"{stem}.pdf"
    run([pdftocairo, "-svg", str(pdf), str(svg)], build)
    run([pdftocairo, "-png", "-singlefile", "-transp", "-r", str(args.dpi),
         str(pdf), str(png.with_suffix(""))], build)
    with Image.open(png) as img:
        img.load()
        if img.mode != "RGBA" or img.getchannel("A").getextrema() != (0, 255):
            raise RuntimeError("Expected a transparent PNG with opaque strokes.")
        pixels = img.size
        white = Image.new("RGBA", pixels, "white")
        white.alpha_composite(img)
        white.convert("RGB").save(preview, dpi=(args.dpi, args.dpi))
    svg_text = svg.read_text(encoding="utf-8")
    if "<image" in svg_text:
        raise RuntimeError("Unexpected raster image embedded in SVG.")
    manifest = {
        "renderer": "TikZ + XeLaTeX; Poppler PDF-to-SVG and transparent PNG",
        "python": sys.executable,
        "dpi": args.dpi,
        "pixels": pixels,
        "outputs": {"png": str(png), "svg": str(svg),
                    "white_preview": str(preview), "pdf": str(pdf), "tex": str(tex)},
        "palette": {"wires": "#303238", "components": "#780404",
                    "annotations": "#E37D00"},
        "physics": {
            "topology": "Ideal parallel LC; common bottom reference ground; no source or loss.",
            "coordinates": "Phi is upper-node flux relative to ground; V=dPhi/dt.",
            "charge": "Upper capacitor plate +Q; lower capacitor plate -Q; Q=C*V.",
            "current": "I_L reference direction downward; V=L*dI_L/dt.",
            "flux_reference": "Phi=L*I_L when their integration constants are matched to zero.",
        },
        "qa": {"png_transparent": True, "svg_embedded_rasters": False},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
