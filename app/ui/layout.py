from nicegui import ui
from app.core.config import settings


def nav_link(label: str, link: str, icon: str, active: bool = False, on_click=None, extra_classes: str = ''):
    """Helper to create consistent navigation links in the header (desktop + drawer)."""
    base_classes = 'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors duration-200 no-underline'
    active_classes = 'text-blue-600 bg-blue-50 font-semibold dark:text-blue-400 dark:bg-blue-900'
    inactive_classes = 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white'

    classes = f"{base_classes} {active_classes if active else inactive_classes} {extra_classes}".strip()

    link_el = ui.link(target=link).classes(classes)
    if on_click:
        link_el.on('click', on_click)
    with link_el:
        ui.icon(icon)
        ui.label(label)

def theme(current_page: str = None):
    """Applies the common layout (Header) to the page."""
    
    # Apply Theme Mode
    dark = ui.dark_mode()
    if settings.THEME_MODE == 'dark':
        dark.enable()
    elif settings.THEME_MODE == 'light':
        dark.disable()
    else: # auto
        dark.auto()
    
    ui.add_head_html('<link rel="stylesheet" href="/ui/static/styles.css">')

    links = [
        ('Dashboard', '/', 'dashboard', 'dashboard'),
        ('Add Expense', '/add', 'add_circle', 'add_expense'),
        ('History', '/history', 'history', 'history'),
        ('Settings', '/settings', 'settings', 'settings'),
    ]

    # Mobile/desktop drawer
    drawer = ui.left_drawer(value=False, bordered=True, elevated=True) \
        .classes('bg-white dark:bg-slate-900 w-64 p-3')
    with drawer:
        ui.label('Navigation').classes('text-sm font-semibold text-gray-600 mb-2 dark:text-gray-200')
        for label, href, icon, key in links:
            nav_link(label, href, icon, active=(current_page == key), on_click=lambda _, d=drawer: d.toggle(), extra_classes='w-full')

    # Header
    with ui.header().classes(
        'bg-white border-b border-gray-200 text-gray-800 shadow-sm h-auto md:h-16 px-3 md:px-6 '
        'flex items-center justify-between flex-wrap gap-3 md:gap-6 sticky top-0 z-50 '
        'dark:bg-slate-900 dark:border-gray-700 dark:text-white'
    ):
        # Logo / Title
        ### === INFO: NiceGui uses https://fonts.google.com/icons ===
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            ui.icon('credit_score', size='md', color='blue-600')
            ui.label('XpenseTracker').classes('text-xl font-bold text-gray-800 tracking-tight dark:text-white')

        # Desktop navigation
        with ui.row().classes('desktop-nav items-center gap-2'):
            for label, href, icon, key in links:
                nav_link(label, href, icon, active=(current_page == key))

        # Mobile menu button
        ui.space().classes('flex-1 mobile-nav-button')
        ui.button(icon='menu', on_click=lambda: drawer.toggle()).props('flat round dense color=blue') \
            .classes('mobile-nav-button')
    
    # Page background
    ui.query('body').classes('bg-gray-50 dark:bg-slate-800')
