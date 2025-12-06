from nicegui import ui

def nav_link(label: str, link: str, icon: str, active: bool = False):
    """Helper to create consistent navigation links in the header."""
    base_classes = 'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors duration-200 no-underline'
    active_classes = 'text-blue-600 bg-blue-50 font-semibold'
    inactive_classes = 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    
    classes = f"{base_classes} {active_classes if active else inactive_classes}"
    
    with ui.link(target=link).classes(classes):
        ui.icon(icon)
        ui.label(label)

def theme(current_page: str = None):
    """Applies the common layout (Header) to the page."""
    
    ui.add_css('.q-page-container { padding-top: 32px !important; }')
    
    # Header
    with ui.header().classes('bg-white border-b border-gray-200 text-gray-800 shadow-sm h-16 px-6 flex items-center justify-between sticky top-0 z-50'):
        # Logo / Title
        ### === INFO: NiceGui uses https://fonts.google.com/icons ===
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            ui.icon('credit_score', size='md', color='blue-600')
            ui.label('XpenseTracker').classes('text-xl font-bold text-gray-800 tracking-tight')

        # Navigation
        with ui.row().classes('items-center gap-2'):
            nav_link('Dashboard', '/', 'dashboard', active=(current_page == 'dashboard'))
            nav_link('Add Expense', '/add', 'add_circle', active=(current_page == 'add_expense'))
            nav_link('History', '/history', 'history', active=(current_page == 'history'))
    
    # Page background
    ui.query('body').classes('bg-gray-50')
