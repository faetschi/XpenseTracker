from nicegui import ui
from app.core.database import Base, engine
from app.ui.dashboard import dashboard_page
from app.ui.add_expense import add_expense_page
from app.ui.history import history_page

# Initialize DB tables
Base.metadata.create_all(bind=engine)

@ui.page('/')
def index():
    dashboard_page()

@ui.page('/add')
def add():
    add_expense_page()

@ui.page('/history')
def history():
    history_page()

ui.run(title='XpenseTracker', port=8501, favicon='💰')
