# XpenseTracker - User Interface Design Document

## 1. Design Philosophy
The UI mimics the provided "Budget Lens" screenshots. It prioritizes clarity, whitespace, and large clickable elements.
* **Primary Color:** Blue (`#1E88E5`) - Used for buttons and active states.
* **Secondary Colors:** Pink (`#FF6F91`) and Yellow (`#FFD740`) - Used for charts.
* **Font:** Sans-serif (Streamlit default or Roboto).

## 2. Navigation Structure
We will use **NiceGUI's Routing** system (`@ui.page`).

*   **Dashboard (`/`)**: Overview of finances (Charts & Summaries).
*   **Add Expense (`/add`)**: The entry point for new expenses (Manual & AI).
*   **History (`/history`)**: Full transaction log with editing capabilities.

## 3. Page Specifications

### Page 1: The Dashboard (Home - `/`)
*Referencing Screenshot: `dashboard.jpg`*

*   **Header:** "XpenseTracker Dashboard".
*   **Visual 1 (Pie Chart):** "Expenses by Category".
    *   Interactive Pie chart showing distribution (Groceries, Dining Out, Clothing).
    *   *Library:* `ui.echart` or `ui.plotly`.
*   **Visual 2 (Summary Metrics):**
    *   Total Spent this Month.
    *   Top Spending Category.
*   **Visual 3 (Mini Table):** "Recent 5 Transactions" (Read-only preview).

### Page 2: Add Expense (`/add`)
*Referencing Screenshot: `image_bec000.png`*

This page will use a **Tabbed Interface** (`ui.tabs`) to switch between modes.

**Tab A: Upload Receipt (AI Mode)**
1.  **Header:** "Upload Receipt".
2.  **Input:** Drag-and-drop file uploader (`ui.upload`).
3.  **Action:** "Analyze Receipt" Button.
4.  **Result State (Post-Processing):**
    *   Shows the scanned image on the left (`ui.image`).
    *   Shows a pre-filled form on the right with data extracted by Gemini.
    *   **User Action:** User reviews the data and clicks "Save to Database".

**Tab B: Manual Input**
1.  **Header:** "Manual Entry".
2.  **Form:** Group inputs in a card.
    *   Date (`ui.date`).
    *   Category (`ui.select`: Groceries, Tech, Travel, etc.).
    *   Description (`ui.input`).
    *   Amount (`ui.number`).
    *   Currency (`ui.select`: EUR, USD, KRW, etc.).
3.  **Action:** "Add Expense" Button (`ui.button`).

### Page 3: History & Editing (`/history`)
*Referencing Screenshot: `image_bec2a8.png`*

This page replaces the "Edit Expense" modal and provides a full view of all data.

*   **Header:** "Transaction History".
*   **Filter Section:**
    *   Date Range Picker.
    *   Category Filter.
*   **Data Table (Interactive):**
    *   Use `ui.aggrid` or `ui.table` to allow **inline editing** of expenses directly in the table.
    *   Users can change Category, Amount, or Description directly.
    *   **Save Changes:** Detect changes and update the DB.
*   **Delete Action:** A column with a delete button.

## 4. UI Components & Styling Code Snippets
To achieve the specific "Budget Lens" look, we will use **Tailwind CSS** classes directly in NiceGUI.

**Button Style:**
```python
ui.button('Add Expense').classes('bg-blue-600 text-white rounded-lg px-6 py-2')
```

**Card Style (for Upload Box):**
```python
with ui.card().classes('border border-gray-200 rounded-xl shadow-sm p-6'):
    # content
```