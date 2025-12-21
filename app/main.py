from nicegui import ui, app
from app.core.database import Base, engine
from app.ui.dashboard import dashboard_page
from app.ui.add_expense import add_expense_page
from app.ui.history import history_page
from app.ui.settings_page import settings_page
import os

# Ensure data directory exists for SQLite and settings
os.makedirs('app/data', exist_ok=True)

# Initialize DB tables
Base.metadata.create_all(bind=engine)

# Serve uploads directory
os.makedirs('app/data/uploads', exist_ok=True)
app.add_static_files('/uploads', 'app/data/uploads')
app.add_static_files('/ui/static', 'app/ui/static')

@ui.page('/')
def index():
    dashboard_page()

@ui.page('/add')
def add():
    add_expense_page()

@ui.page('/history')
def history():
    history_page()

@ui.page('/settings')
def settings():
    settings_page()

ui.run(title='XpenseTracker', port=8501, favicon='💰')
