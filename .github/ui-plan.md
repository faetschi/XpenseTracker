# XpenseTracker - User Interface Design Document

## 1. Design Philosophy
The UI mimics the provided "Budget Lens" screenshots. It prioritizes clarity, whitespace, and large clickable elements.
* **Primary Color:** Blue (`#1E88E5`) - Used for buttons and active states.
* **Secondary Colors:** Pink (`#FF6F91`) and Yellow (`#FFD740`) - Used for charts.
* **Font:** Sans-serif (Streamlit default or Roboto).

## 2. Navigation Structure
We will use **Streamlit's Native Multipage App** support. This automatically generates a sidebar navigation based on the files in the `pages/` directory.

*   **Dashboard (`main.py`)**: Overview of finances (Charts & Summaries).
*   **Add Expense (`pages/1_Add_Expense.py`)**: The entry point for new expenses (Manual & AI).
*   **History (`pages/2_History.py`)**: Full transaction log with editing capabilities.

## 3. Page Specifications

### Page 1: The Dashboard (Home - `main.py`)
*Referencing Screenshot: `dashboard.jpg`*

*   **Header:** "XpenseTracker Dashboard".
*   **Visual 1 (Pie Chart):** "Expenses by Category".
    *   Interactive Pie chart showing distribution (Groceries, Dining Out, Clothing).
    *   *Library:* `plotly.express`.
*   **Visual 2 (Summary Metrics):**
    *   Total Spent this Month.
    *   Top Spending Category.
*   **Visual 3 (Mini Table):** "Recent 5 Transactions" (Read-only preview).

### Page 2: Add Expense (`pages/1_Add_Expense.py`)
*Referencing Screenshot: `image_bec000.png`*

This page will use a **Tabbed Interface** (`st.tabs`) to switch between modes.

**Tab A: Upload Receipt (AI Mode)**
1.  **Header:** "Upload Receipt".
2.  **Input:** Drag-and-drop file uploader (supports JPG, PNG).
3.  **Action:** "Analyze Receipt" Button.
4.  **Result State (Post-Processing):**
    *   *Note:* Use `st.session_state` to persist the extracted data between the "Analyze" click and the "Save" click.
    *   Shows the scanned image on the left (using `st.image`).
    *   Shows a pre-filled form on the right with data extracted by Gemini.
    *   **User Action:** User reviews the data and clicks "Save to Database".

**Tab B: Manual Input**
1.  **Header:** "Manual Entry".
2.  **Form:** `st.form` to group inputs and prevent premature submission.
    *   Date (`st.date_input`).
    *   Category (`st.selectbox`: Groceries, Tech, Travel, etc.).
    *   Description (`st.text_input`).
    *   Amount (`st.number_input`).
    *   Currency (`st.selectbox`: EUR, USD, KRW, etc.).
3.  **Action:** "Add Expense" Button (`st.form_submit_button`).

### Page 3: History & Editing (`pages/2_History.py`)
*Referencing Screenshot: `image_bec2a8.png`*

This page replaces the "Edit Expense" modal and provides a full view of all data.

*   **Header:** "Transaction History".
*   **Filter Section:**
    *   Date Range Picker.
    *   Category Filter.
*   **Data Table (Interactive):**
    *   Use `st.data_editor` to allow **inline editing** of expenses directly in the table.
    *   Users can change Category, Amount, or Description directly.
    *   **Save Changes:** `st.data_editor` returns the edited dataframe. We detect changes and update the DB.
*   **Delete Action:** A column with a checkbox or a dedicated "Delete Selected" button.

## 4. UI Components & Styling Code Snippets
To achieve the specific "Budget Lens" look in Streamlit, we will inject custom CSS.

**Button Style:**
```css
div.stButton > button {
    background-color: #1E88E5;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 10px 24px;
}
**Card Style (for Upload Box):**

```css
div.css-card {
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
```