from collections.abc import Callable

import plotly.graph_objects as go

from src.theme import CHART_H, CHART_W, FONT, LIGHT


def figure(theme: dict) -> go.Figure:
    axis = dict(gridcolor=theme["line"], zeroline=False, linecolor=theme["line"], tickfont_color=theme["muted"])
    return go.Figure(
        layout=dict(
            paper_bgcolor=theme["bg"],
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT, size=20, color=theme["ink"]),
            colorway=theme["series"],
            margin=dict(l=40, r=20, t=40, b=50),
            xaxis=axis,
            yaxis=axis,
            legend=dict(orientation="h", x=0, y=1.1, xanchor="left"),
            hovermode=False,
        )
    )


def show(make_fig: Callable[[dict], go.Figure]) -> None:
    make_fig(LIGHT).show("png", width=CHART_W, height=CHART_H, scale=2)
