# 🧠 Architecture Overview — Factorio Preview Toolkit

This document explains the high-level structure of the Factorio Preview Toolkit.

---

## 🔄 High-Level Workflow

### ✅ Startup

The `PreviewController` starts and registers two live providers:

- One for detecting the **Factorio executable path**
- Another for retrieving **map exchange strings**

These providers run in the background and notify the controller when a new value is available.

---

### ⚡ Triggering Preview Generation

When a new map exchange string is detected:

1. The controller **aborts any running preview job**
2. A new **preview generation worker subprocess** is launched

---

### 🧠 Inside the Worker

1. A **dummy save** is created from the exchange string.
2. **Lua code** is injected into the save file to dump:
   - `map-gen-settings.json`
   - A list of **available planets**
3. The dummy save is then **executed via the Factorio CLI** to generate the above data.

For each available planet:

- A **preview image** is rendered using the Factorio CLI
- Images are saved in the output folder

---

### ☁️ Upload Process

1. All planet preview images are **uploaded one-by-one**
2. A JSON file containing the list of planets is uploaded
3. A file is created with shareable links
