# Terminal Monitoring Architecture

This document outlines the architectural approach to identifying, tracking, and capturing real-time terminal data across multiple windows and tabs.

---

### **1. Identification of Terminals and Tabs**
Identification is a two-stage process using **Native Discovery** via the operating system's UI Automation (UIA) layer.

*   **Window Filtering**: The system first scans all top-level windows for specific **OS Class Names**. 
    *   *Legacy (CMD):* `ConsoleWindowClass`
    *   *Modern (Windows Terminal):* `CASCADIA_HOSTING_WINDOW_CLASS`
*   **Tab Discovery**: For modern tabbed terminals, the system performs a recursive search within the identified window to find nodes of type `TabItemControl` or `ListItemControl`. 
*   **Identity Anchors**: Every discovered entity is assigned a persistent identity based on two data points:
    1.  **HWND**: The numeric window handle assigned by the OS (e.g., `131234`).
    2.  **RuntimeID**: A unique, stable integer array (e.g., `[42, 67024, 4, 68]`) that identifies a specific tab even if titles change or tabs are reordered.

---

### **2. Text Capture Mechanism**
The system treats the terminal not as a stream of text, but as a **Live UI View**. 

*   **Polling Frequency**: The system interrogates all active terminals at a fixed interval (default: 1000ms).
*   **Buffer Extraction**: On every tick, the system locates the active text container within the tab's hierarchy—usually a `DocumentControl` or `PaneControl`—and requests its full text content through the **TextPattern** interface. 
*   **Change Detection**: Captured text is cached locally. Updates to the UI are only triggered if the new capture differs from the previous one.

---

### **3. Operational Costs**
The primary bottleneck is **Cross-Process Context Switching**. 

Every time the system "looks" for a terminal or "asks" for text, the operating system must pause the monitoring process, query the internal state of the Terminal application, and marshal that data back across process boundaries. 
*   **Tree Walking**: This is the most expensive operation. Navigating from the "Main Window" down through "Tabs" to the "Text Pane" requires dozens of small, synchronous requests to the terminal’s internal UI tree.

---

### **4. Key Terms & Specific Values**
*   **UIA Tree**: The hierarchical map of a program's interface. 
    *   *Root:* `Window`
    *   *Target:* `DocumentControl` (where the text actually lives).
*   **TextPattern**: A specialized automation interface that allows the system to treat a UI node like a text document.
*   **HWND (Handle to a Window)**: A unique ID for a top-level window (e.g., `0x000204A2`).
*   **PaneControl**: A specific node type in the UIA tree. In Windows Terminal, the text area is often a `PaneControl` nested deep inside a `TerminalControl`.

---

### **5. Potential Optimizations**

#### **Direct Node Caching**
*   **Concept**: Instead of "Walking the Tree" from the top down every second, the system retains a direct reference to the specific `AutomationElement` node that contains the text.
*   **Gain**: **~90% reduction in capture latency.** This bypasses the recursive search, reducing the operation from a "Tree Walk" to a "Direct Query."

#### **Window List Sharing**
*   **Concept**: Fetch the list of all open windows once per global sync cycle and share it among all worker resolution logic, rather than each worker scanning the OS windows independently.
*   **Gain**: **Significant CPU reduction**, as the full-system window scan is a high-overhead OS operation that currently scales linearly with the number of workers.

#### **Hashed Change Detection**
*   **Concept**: Compute a lightweight hash of the captured text before performing string operations or UI updates.
*   **Gain**: **Reduced memory and UI overhead**, especially for terminals with large buffers that remain static for long periods.
