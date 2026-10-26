"""Generate publication-quality harmonic-oscillator figures without network installs.

Matplotlib is not installed in this environment. This reproducible local fallback
uses the scientific plotting package PGFPlots via XeLaTeX, Poppler for SVG/PNG,
and Pillow only to composite a white comparison preview. The plotted formulas
are evaluated by PGFPlots with linear shared axes; no image-generation model is
used. Run this file with the bundled Python runtime. Existing outputs are never
overwritten; choose a new --revision if required.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image


PREAMBLE = r"""\documentclass[tikz,border=9pt]{standalone}
\usepackage{fontspec}
\setmainfont{TeX Gyre Heros}
\usepackage{amsmath}
\usepackage{unicode-math}
\setmathfont{TeX Gyre Termes Math}
\usepackage{pgfplots}
\usepgfplotslibrary{fillbetween,groupplots}
\usetikzlibrary{arrows.meta,calc}
\definecolor{maroon}{HTML}{780404}
\definecolor{orange}{HTML}{E37D00}
\definecolor{charcoal}{HTML}{303238}
\definecolor{muted}{HTML}{65686D}
\definecolor{gridgray}{HTML}{DDDFE2}
\pgfplotsset{compat=1.18,
  oscillator/.style={
    width=12.6cm,height=8.8cm,
    xmin=-3.5,xmax=3.5,ymin=0,ymax=5.35,
    axis lines=left,axis line style={charcoal,line width=.7pt,-{Stealth[length=4pt]}},
    xtick={-3,-2,-1,0,1,2,3},ytick={0,1,2,3,4,5},
    tick align=outside,tick style={charcoal},
    tick label style={font=\small,text=charcoal},
    xlabel={$q=x/\ell$},ylabel={$\varepsilon=E/(\hbar\omega)$},
    label style={font=\normalsize,text=charcoal},
    xlabel style={at={(axis description cs:.5,-.085)},anchor=north},
    ylabel style={at={(axis description cs:-.075,.5)},anchor=south},
    ymajorgrids=true,grid style={gridgray,dashed,line width=.35pt},
    clip=false,samples=251,
  },
}
\begin{document}
\begin{tikzpicture}[text=charcoal]
"""

ENDING = "\\end{tikzpicture}\n\\end{document}\n"


def heading(kind: str) -> str:
    if kind == "classical":
        title = "Classical harmonic oscillator"
        subtitle = r"Continuous energy: any $E\geq 0$"
    else:
        title = "Quantum harmonic oscillator"
        subtitle = r"Discrete energy: $E_n=\hbar\omega(n+\tfrac12)$"
    return rf"""
\node[anchor=west,font=\Large\bfseries,text=maroon]
  at (axis description cs:0,1.15) {{{title}}};
\node[anchor=west,font=\normalsize,text=muted]
  at (axis description cs:0,1.065) {{{subtitle}}};
"""


POTENTIAL = r"""
\addplot[maroon,line width=1.75pt,domain=-3.271085:3.271085] {.5*x^2};
\node[font=\normalsize,text=maroon,anchor=north]
  at (axis cs:0,5.21) {$V/(\hbar\omega)=\tfrac12q^2$};
"""


def panel(kind: str) -> str:
    content = heading(kind)
    if kind == "classical":
        content += r"""
% The full region above the potential is a continuum of (q,E) pairs.
\addplot[name path=potential,draw=none,domain=-3.271085:3.271085] {.5*x^2};
\addplot[name path=top,draw=none,domain=-3.271085:3.271085] {5.35};
\addplot[orange,fill opacity=.065,draw=none] fill between[of=potential and top];
% One sample total energy; the darker fill is its accessible K >= 0 region.
\addplot[name path=sampleV,draw=none,domain=-2.345208:2.345208] {.5*x^2};
\addplot[name path=sampleE,draw=none,domain=-2.345208:2.345208] {2.75};
\addplot[orange,fill opacity=.13,draw=none] fill between[of=sampleV and sampleE];
\addplot[orange,line width=1.5pt,domain=-2.345208:2.345208] {2.75};
\node[anchor=south,font=\normalsize,text=orange,yshift=4pt]
  at (axis cs:0,2.75) {$E_{\rm cl}=2.75\,\hbar\omega\quad\text{(example)}$};
\node[font=\normalsize,text=muted] at (axis cs:0,4.32) {$E\geq V(q)$};
\node[font=\small,text=muted] at (axis cs:0,3.82) {continuously allowed energies};
\node[font=\normalsize,text=orange!85!black]
  at (axis cs:0,1.7) {$K=E_{\rm cl}-V(q)\geq0$};
"""
    content += POTENTIAL
    if kind == "quantum":
        for n in range(5):
            energy = n + 0.5
            turn = (2 * energy) ** 0.5
            width = "1.8pt" if n == 0 else "1.25pt"
            content += rf"""
\addplot[orange,line width={width}] coordinates {{(-{turn:.10f},{energy}) ({turn:.10f},{energy})}};
\node[anchor=west,font=\small,text=charcoal,xshift=4pt]
  at (axis cs:{turn:.10f},{energy}) {{$n={n}$}};
"""
        content += r"""
\draw[maroon,line width=.9pt,{Stealth[length=4pt]}-{Stealth[length=4pt]}]
  (axis cs:.12,.54) -- (axis cs:.12,1.46);
\node[anchor=west,font=\normalsize,text=maroon,xshift=5pt]
  at (axis cs:.12,1) {$\Delta=\hbar\omega$};
\node[anchor=east,font=\normalsize,text=maroon]
  at (axis cs:-1.17,.49) {$E_0=\tfrac12\hbar\omega$};
\draw[maroon,line width=.55pt] (axis cs:-1.12,.49)--(axis cs:-1.01,.49);
"""
    return content


def footer(anchor: str = "current bounding box.south") -> str:
    return rf"""
\node[anchor=north,align=center,text=muted,font=\small,yshift=-30pt]
  at ({anchor}) {{Reference units: $\ell=\sqrt{{\hbar/(m\omega)}}$, $q=x/\ell$, $\varepsilon=E/(\hbar\omega)$.\\[3pt]
  $\hbar$ sets a shared plotting scale; it does not quantize the classical system.}};
"""


def single(kind: str) -> str:
    return PREAMBLE + "\\begin{axis}[oscillator]\n" + panel(kind) + "\\end{axis}\n" + footer() + ENDING


def comparison() -> str:
    body = r"""
\begin{groupplot}[oscillator,group style={group size=2 by 1,horizontal sep=1.7cm}]
\nextgroupplot
""" + panel("classical") + "\\nextgroupplot\n" + panel("quantum") + "\\end{groupplot}\n"
    body += r"""
\coordinate (footeranchor) at ($(group c1r1.south west)!.5!(group c2r1.south east)$);
"""
    return PREAMBLE + body + footer("footeranchor") + ENDING


def ladder() -> str:
    return PREAMBLE + r"""
\begin{axis}[
  width=6.2cm,height=9.2cm,
  xmin=0,xmax=1.1,ymin=0,ymax=4.95,
  axis x line=none,axis y line=left,
  axis line style={charcoal,line width=.7pt,-{Stealth[length=4pt]}},
  xtick=\empty,ytick={.5,1.5,2.5,3.5,4.5},
  yticklabels={$E_0$,$E_1$,$E_2$,$E_3$,$E_4$},
  tick align=outside,tick style={charcoal},
  tick label style={font=\normalsize,text=charcoal},
  ylabel={},
  clip=false,
]
\node[anchor=west,font=\large\bfseries,text=maroon]
  at (axis description cs:-.04,1.17) {Quantum spectrum};
\node[anchor=west,font=\normalsize,text=muted]
  at (axis description cs:-.04,1.075) {$E_n=\hbar\omega(n+\tfrac12)$};
\foreach \level in {.5,1.5,2.5,3.5,4.5}{
  \addplot[orange,line width=1.5pt] coordinates {(.12,\level) (.95,\level)};
}
\draw[maroon,line width=.9pt,{Stealth[length=4pt]}-{Stealth[length=4pt]}]
  (axis cs:.84,.54)--(axis cs:.84,1.46);
\node[anchor=east,text=maroon,font=\normalsize,xshift=-5pt]
  at (axis cs:.84,1) {$\Delta=\hbar\omega$};
\node[anchor=north,text=maroon,font=\normalsize,yshift=-9pt]
  at (axis cs:.53,.5) {$E_0=\tfrac12\hbar\omega$};
\end{axis}
""" + ENDING


def command(args: list[str], cwd: Path, log: Path | None = None) -> None:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if log:
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        print(result.stdout[-10000:])
        print(result.stderr[-2000:])
        raise RuntimeError(f"Command failed: {args[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="v1")
    parser.add_argument("--dpi", type=int, default=400)
    parser.add_argument("--only", choices=["classical_energy", "quantum_energy", "comparison", "energy_levels"])
    args = parser.parse_args()
    output = Path(__file__).resolve().parent
    build = output / f"build_{args.revision}"
    if build.exists():
        raise FileExistsError(f"Refusing to overwrite existing build: {build}")
    build.mkdir()
    xelatex = shutil.which("xelatex")
    pdftocairo = shutil.which("pdftocairo")
    if not xelatex or not pdftocairo:
        raise RuntimeError("Local XeLaTeX and pdftocairo are required; nothing will be installed.")
    figures = {
        "classical_energy": single("classical"),
        "quantum_energy": single("quantum"),
        "comparison": comparison(),
        "energy_levels": ladder(),
    }
    if args.only:
        figures = {args.only: figures[args.only]}
    generated = []
    for basename, source in figures.items():
        stem = f"{basename}_{args.revision}"
        png, svg = output / f"{stem}.png", output / f"{stem}.svg"
        if png.exists() or svg.exists():
            raise FileExistsError(f"Refusing to overwrite: {stem}")
        tex = build / f"{stem}.tex"
        tex.write_text(source, encoding="utf-8")
        command([xelatex, "-interaction=nonstopmode", "-halt-on-error", tex.name], build, build / f"{stem}_compile.txt")
        pdf = build / f"{stem}.pdf"
        command([pdftocairo, "-svg", str(pdf), str(svg)], build)
        command([pdftocairo, "-png", "-singlefile", "-transp", "-r", str(args.dpi), str(pdf), str(png.with_suffix(""))], build)
        with Image.open(png) as image:
            image.load()
            if image.mode != "RGBA":
                raise RuntimeError(f"Expected transparent RGBA PNG: {png}")
            alpha_extrema = image.getchannel("A").getextrema()
            if alpha_extrema != (0, 255):
                raise RuntimeError(f"Expected transparent background and opaque strokes: {png}")
            generated.append({"name": basename, "png": str(png), "svg": str(svg), "pixels": image.size, "alpha": alpha_extrema})
            if basename in {"comparison", "energy_levels"}:
                preview = output / f"{basename}_{args.revision}_white_preview.png"
                if preview.exists():
                    raise FileExistsError(f"Refusing to overwrite: {preview}")
                white = Image.new("RGBA", image.size, "white")
                white.alpha_composite(image)
                white.convert("RGB").save(preview, dpi=(args.dpi, args.dpi))
    manifest = {
        "renderer": "PGFPlots + XeLaTeX; SVG and transparent PNG exported with Poppler",
        "python": sys.executable,
        "note": "Matplotlib was unavailable; no packages installed and no network used.",
        "physics": {
            "dimensionless_position": "q=x/ell, ell=sqrt(hbar/(m*omega))",
            "dimensionless_energy": "epsilon=E/(hbar*omega)",
            "potential": "epsilon_V=q^2/2",
            "classical": "continuous E>=0; orange sample at E/(hbar*omega)=2.75",
            "quantum": "n=0..4, epsilon_n=n+0.5; E0=hbar*omega/2, gap=hbar*omega",
        },
        "figures": generated,
    }
    (output / f"manifest_{args.revision}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
