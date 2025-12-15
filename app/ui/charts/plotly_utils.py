from __future__ import annotations


def js_emit_visible_legend_labels(*, element_html_id: str) -> str:
    """Return a NiceGUI js_handler which emits the currently *visible* category labels.

    Notes:
    - Plotly legend clicks often fire BEFORE the chart state is updated.
      To avoid being one click behind, consumers should bind this handler to
      post-update events like: plotly_relayout, plotly_restyle, plotly_afterplot.
    - This implementation supports Plotly pie charts by using labels + hiddenlabels.
      Future chart types can add additional branches (e.g. use x values for bar charts).
    """

    # IMPORTANT: This string is embedded into a Python f-string elsewhere.
    # Keep braces escaped for NiceGUI/Quasar emission.
    return f"""(eventData) => {{
        const root = document.getElementById('{element_html_id}');
        const gd = root ? (root.querySelector('.js-plotly-plot') || root) : null;

        // Pie charts: labels + hiddenlabels
        const labels =
            (gd && gd.data && gd.data[0] && gd.data[0].labels) ||
            (gd && gd._fullData && gd._fullData[0] && gd._fullData[0].labels) ||
            [];
        const hidden =
            (gd && gd.layout && gd.layout.hiddenlabels) ||
            (gd && gd._fullLayout && gd._fullLayout.hiddenlabels) ||
            [];

        const hiddenSet = new Set(hidden || []);
        const visible = (labels || []).filter(l => !hiddenSet.has(l));
        emit({{visible: visible}});
        return true;
    }}"""
