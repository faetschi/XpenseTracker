from nicegui import ui

def nav_button(label: str, link: str, icon: str):
    """Helper to create consistent navigation buttons."""
    ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(link)) \
        .props('flat align=left') \
        .classes('w-full text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-r-full')

def theme():
    """Applies the common layout (Header, Sidebar) to the page."""
    
    # Header
    with ui.header().classes('bg-blue-600 text-white shadow-md items-center h-14'):
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white round')
        ui.label('XpenseTracker').classes('text-xl font-bold ml-2')

    # Sidebar (Drawer)
    with ui.left_drawer(value=True).classes('bg-gray-50 border-r border-gray-200') as left_drawer:
        ui.label('MENU').classes('text-gray-400 text-xs font-bold px-4 py-2 mt-2')
        with ui.column().classes('w-full gap-1'):
            nav_button('Dashboard', '/', 'dashboard')
            nav_button('Add Expense', '/add', 'add_circle')
            nav_button('History', '/history', 'history')
    
    # Main Content Container
    # We don't need to explicitly create a container here as the page content follows automatically,
    # but we can add some global styling to the page body if needed.
    # ui.query('body').classes('bg-gray-50')
