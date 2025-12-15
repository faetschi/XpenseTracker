from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import plotly.express as px
from nicegui import ui

from .plotly_utils import js_emit_visible_legend_labels


def render_expenses_by_category_pie(
    *,
    by_category: dict[str, float] | None,
    expenses_label: ui.label,
    format_currency: Callable[[Any], str],
) -> None:
    """Render an expenses-by-category pie chart and keep the Expenses card in sync.

    The Expenses card updates when the user hides/shows categories via the legend.
    """

    if not by_category:
        ui.label('No data available for this period.').classes('text-gray-400 italic')
        return

    df = pd.DataFrame(list(by_category.items()), columns=["Category", "Amount"])

    fig = px.pie(
        df,
        values="Amount",
        names="Category",
        hole=0.5,
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300, showlegend=True)

    chart = ui.plotly(fig).classes('w-full h-80')

    def update_expenses_for_visible_labels(visible_labels: set[str]) -> None:
        visible_total = df[df['Category'].astype(str).isin(visible_labels)]['Amount'].sum()
        expenses_label.text = format_currency(visible_total)
        expenses_label.update()

    def handle_visible_labels_update(e) -> None:
        # NiceGUI may provide e.args either as a dict (preferred)
        # or as a list/tuple of arguments. Be defensive.
        payload: Any = None
        if not e.args:
            payload = None
        elif isinstance(e.args, dict):
            payload = e.args
        elif isinstance(e.args, (list, tuple)):
            payload = e.args[0] if len(e.args) == 1 else list(e.args)
        else:
            payload = e.args

        visible: list[str] = []
        if isinstance(payload, dict):
            visible = payload.get('visible', []) or []
        elif isinstance(payload, (list, tuple, set)):
            visible = list(payload)

        visible_set = set(str(v) for v in visible)
        update_expenses_for_visible_labels(visible_set)

    # Bind to post-update events to avoid being one click behind.
    js_handler = js_emit_visible_legend_labels(element_html_id=chart.html_id)
    chart.on('plotly_relayout', handle_visible_labels_update, js_handler=js_handler)
    chart.on('plotly_restyle', handle_visible_labels_update, js_handler=js_handler)
    chart.on('plotly_afterplot', handle_visible_labels_update, js_handler=js_handler)
