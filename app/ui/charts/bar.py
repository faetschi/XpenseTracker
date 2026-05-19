from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

MONTH_NAMES = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]


def render_monthly_bar_chart(
    *,
    monthly_data: list[dict],
    format_currency: Callable[[Any], str],
) -> None:
    """Render a grouped bar chart: income vs expenses per month + balance trend line."""

    if not monthly_data or all(m['spent'] == 0 and m['income'] == 0 for m in monthly_data):
        ui.label('No data available for this year.').classes('text-gray-400 italic')
        return

    import plotly.graph_objects as go

    months = [MONTH_NAMES[m['month'] - 1] for m in monthly_data]
    incomes = [m['income'] for m in monthly_data]
    spent = [m['spent'] for m in monthly_data]
    balances = [m['balance'] for m in monthly_data]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=months, y=incomes, name='Income',
        marker_color='#2ecc71',
        hovertemplate='<b>%{x}</b><br>Income: %{y:.2f}<extra></extra>',
    ))

    fig.add_trace(go.Bar(
        x=months, y=spent, name='Expenses',
        marker_color='#e74c3c',
        hovertemplate='<b>%{x}</b><br>Expenses: %{y:.2f}<extra></extra>',
    ))

    fig.add_trace(go.Scatter(
        x=months, y=balances, name='Balance',
        mode='lines+markers',
        line=dict(color='#f39c12', width=2, dash='dash'),
        marker=dict(size=6),
        yaxis='y2',
        hovertemplate='<b>%{x}</b><br>Balance: %{y:.2f}<extra></extra>',
    ))

    fig.update_layout(
        barmode='group',
        height=380,
        margin=dict(t=10, b=40, l=50, r=50),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        xaxis=dict(title=None, tickangle=-45),
        yaxis=dict(title='Amount', side='left'),
        yaxis2=dict(
            title='Balance',
            overlaying='y',
            side='right',
            showgrid=False,
            tickformat='.2f',
        ),
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    ui.plotly(fig).classes('w-full h-96')


def render_monthly_bar_chart_lightweight(
    *,
    monthly_data: list[dict],
    format_currency: Callable[[Any], str],
) -> None:
    """Render a lightweight HTML/CSS grouped bar chart for monthly data."""

    if not monthly_data or all(m['spent'] == 0 and m['income'] == 0 for m in monthly_data):
        ui.label('No data available for this year.').classes('text-gray-400 italic')
        return

    max_val = max(max(m['income'], m['spent']) for m in monthly_data) or 1

    with ui.column().classes('w-full gap-2'):
        for entry in monthly_data:
            month_name = MONTH_NAMES[entry['month'] - 1]
            income_pct = (entry['income'] / max_val) * 100
            spent_pct = (entry['spent'] / max_val) * 100

            with ui.row().classes('w-full items-center gap-2'):
                ui.label(month_name).classes('text-sm text-gray-700 w-10 text-right font-medium')
                with ui.column().classes('flex-1 gap-0.5'):
                    with ui.row().classes('w-full items-center gap-1'):
                        ui.element('div').classes('h-1.5 bg-green-400 rounded').style(f'width: {income_pct:.1f}%')
                        with ui.row().classes('flex-1 items-center gap-1'):
                            ui.element('div').classes('h-1.5 bg-red-400 rounded').style(f'width: {spent_pct:.1f}%')
                ui.label(format_currency(entry['spent'])).classes('text-xs text-gray-500 w-20 text-right truncate')


def render_daily_bar_chart(
    *,
    daily_data: list[dict],
    format_currency: Callable[[Any], str],
    show_income: bool = False,
) -> None:
    """Render a bar chart: daily expenses for a month, with optional income bars."""

    if not daily_data or all(d['spent'] == 0 for d in daily_data):
        ui.label('No data available for this month.').classes('text-gray-400 italic')
        return

    import plotly.graph_objects as go

    days = [d['day'] for d in daily_data]
    spent = [d['spent'] for d in daily_data]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=days, y=spent, name='Expenses',
        marker_color='#e74c3c',
        hovertemplate='<b>Day %{x}</b><br>Expenses: %{y:.2f}<extra></extra>',
    ))

    if show_income:
        incomes = [d['income'] for d in daily_data]
        if any(i > 0 for i in incomes):
            fig.add_trace(go.Bar(
                x=days, y=incomes, name='Income',
                marker_color='#2ecc71',
                hovertemplate='<b>Day %{x}</b><br>Income: %{y:.2f}<extra></extra>',
            ))
            fig.update_layout(barmode='group')

    avg_spent = sum(spent) / len(spent) if spent else 0
    fig.add_hline(
        y=avg_spent,
        line_dash='dot',
        line_color='#95a5a6',
        annotation_text=f'Avg: {format_currency(avg_spent)}',
        annotation_position='top right',
    )

    fig.update_layout(
        height=300,
        margin=dict(t=30, b=40, l=50, r=20),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(title='Day', tickmode='linear', dtick=max(1, len(days) // 15)),
        yaxis=dict(title='Amount'),
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    ui.plotly(fig).classes('w-full h-72')


def render_daily_bar_chart_lightweight(
    *,
    daily_data: list[dict],
    format_currency: Callable[[Any], str],
    show_income: bool = False,
) -> None:
    """Render a lightweight HTML/CSS bar chart for daily data."""

    if not daily_data or all(d['spent'] == 0 for d in daily_data):
        ui.label('No data available for this month.').classes('text-gray-400 italic')
        return

    max_spent = max(d['spent'] for d in daily_data) or 1
    max_income = max(d['income'] for d in daily_data) if show_income else 0
    max_val = max(max_spent, max_income) or 1

    with ui.column().classes('w-full gap-1'):
        for entry in daily_data:
            if entry['spent'] == 0 and entry['income'] == 0:
                continue
            spent_pct = (entry['spent'] / max_val) * 100
            income_pct = (entry['income'] / max_val) * 100 if show_income else 0

            with ui.row().classes('w-full items-center gap-2'):
                ui.label(f"D{entry['day']}").classes('text-xs text-gray-600 w-8 text-right')
                with ui.column().classes('flex-1 gap-0.5'):
                    if show_income and entry['income'] > 0:
                        ui.element('div').classes('h-1.5 bg-green-400 rounded').style(f'width: {income_pct:.1f}%')
                    with ui.element('div').classes('flex-1 h-2 bg-gray-100 rounded').style('min-width: 0;'):
                        ui.element('div').classes('h-2 bg-red-400 rounded').style(f'width: {spent_pct:.1f}%')
                ui.label(format_currency(entry['spent'])).classes('text-xs text-gray-500 w-16 text-right truncate')
