from nicegui import ui
from app.core.config import settings

def nav_link(label: str, link: str, icon: str, active: bool = False):
    """Helper to create consistent navigation links in the header."""
    base_classes = 'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors duration-200 no-underline'
    active_classes = 'text-blue-600 bg-blue-50 font-semibold dark:text-blue-400 dark:bg-blue-900'
    inactive_classes = 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white'
    
    classes = f"{base_classes} {active_classes if active else inactive_classes}"
    
    with ui.link(target=link).classes(classes):
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
    
    ui.add_css('.q-page-container { padding-top: 32px !important; }')
    
    # Header
    with ui.header().classes('bg-white border-b border-gray-200 text-gray-800 shadow-sm h-16 px-6 flex items-center justify-between sticky top-0 z-50 dark:bg-slate-900 dark:border-gray-700 dark:text-white'):
        # Logo / Title
        ### === INFO: NiceGui uses https://fonts.google.com/icons ===
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            ui.icon('credit_score', size='md', color='blue-600')
            ui.label('XpenseTracker').classes('text-xl font-bold text-gray-800 tracking-tight dark:text-white')

        # Navigation
        with ui.row().classes('items-center gap-2'):
            nav_link('Dashboard', '/', 'dashboard', active=(current_page == 'dashboard'))
            nav_link('Add Expense', '/add', 'add_circle', active=(current_page == 'add_expense'))
            nav_link('History', '/history', 'history', active=(current_page == 'history'))
            nav_link('Settings', '/settings', 'settings', active=(current_page == 'settings'))
    
    # Page background
    ui.query('body').classes('bg-gray-50 dark:bg-slate-800')
