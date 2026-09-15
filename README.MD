# Modern Notes App (iOS-Style for Python)

A sleek, modern desktop notes application built with **Python** and **PyQt6**. Inspired by the design aesthetics of iOS Notes and the tabbed workflow of Windows 11 Notepad, this app offers localized rich-text formatting, session persistence (ability to access aved and unsaved files from previou sessions), .

---

## 1. Setting Up the Project Environment

### Prerequisites

* **Python 3.8+** and **pip** installed on your system.

2. **Install Dependencies:**
Create a `requirements.txt` file (or use the one provided) containing:
```text
PyQt6
```

Then run:
```bash
pip install -r requirements.txt
```


4. **Run the Application:**
```bash
python main.py
```

---

## 2. User Features

* **iOS-Style Collapsible Sidebar:** Easily toggle your notes list open or closed using the top-left `☰` button or `Ctrl+B`.
* **Multi-Tab Workspace:** Open multiple note files or scratchpads simultaneously in one unified window. Close tabs with a hoverable `✕` button.
* **Granular Rich-Text Formatting:** Apply custom colors, fonts, and font sizes to selected words or future typing without altering the rest of your document.
* **Custom Canvas Styles:** Change the background color of your editor canvas to suit your preference.
* **Session Auto-Persistence:**
* Open tabs and active file references automatically restore when you re-open the app.
* Unsaved drafts across tabs are preserved in the background session file so you never lose work.


* **Smart File Handling:** Prompts you if an opened file was moved or deleted on disk, allowing you to gracefully remove or update the tab reference.
* **Find & Replace:** Full-featured dialog (`Ctrl+F`) supporting `Find Next`, `Replace`, and `Replace All` across the active note.
* **System Shortcuts:** Built-in support for standard keyboard shortcuts (`Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `Ctrl+W`, `Ctrl+Z`, `Ctrl+F`, etc.).

---

## 3. Technical Overview

### Architecture & UI Stack

* **GUI Framework:** Developed using **PyQt6** for native cross-platform rendering and GPU-accelerated UI controls.
* **Layout Structure:**
* `QSplitter`: Provides a resizable layout between the sidebar container and the editor stage.
* `QStackedWidget`: Hosts individual `QTextEdit` instances per tab for fast context switching.
* `QListWidget`: Renders custom item widgets (`TabItemWidget`) representing active open notes.



### Rich-Text Engine

* **Character Formatting (`QTextCharFormat`):** Formatting actions (font family, point size, text color) are applied via `cursor.mergeCharFormat()` and `editor.mergeCurrentCharFormat()`. This decouples text styling from container stylesheets (`QSS`), ensuring localized inline formatting rather than global document overrides.
* **Canvas Styling:** Container background changes are isolated to stylesheet rules (`QTextEdit { background-color: ... }`), leaving inline character formatting intact.

### State & Persistence Mechanism

* **Session Storage (`session.json`):** On application close (`closeEvent`), open tab metadata, active index, current file paths, and raw unsaved text buffers are serialized to JSON. On startup, `loadSession()` dynamically re-creates tabs and restores text state seamlessly.

---

## 4. Future Developments

* **Markdown Support:** Live preview and parsing for Markdown syntax (`# Headers`, `**bold**`, lists, code blocks).
* **Search Across All Notes:** Global search bar in the sidebar to search text content across all currently open tabs and saved files.
* **IOS Notes Style Checkboxes** Add text theme based check boxes (technically circles but not exactly radio buttons since its a check)
* **Light Weight Spellcheck** Underlining potentially misspelled words. Add common false flags to ignore dictionary
* **UI customization** Add more settings for UI customisation
## 5. Future QOL Updates
* Unsaved note tabs will be named first n characters of the note excluding spaces (win notes feature)
* Make top most menu more professional rather then the current beta version
