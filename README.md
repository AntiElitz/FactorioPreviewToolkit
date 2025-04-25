# 🚀 Factorio Preview Toolkit

The Factorio Preview Toolkit is a Python-based, cross-platform utility 
that automatically generates preview images for map exchange strings in Factorio. 
It's built for speedrunners who need accurate previews across 
multiple planets and want to share them easily with their community.

## ✨ Features
- Auto-detects map exchange strings from clipboard or file  
- Generates high-resolution PNG previews using the Factorio CLI  
- Automatically uses the currently active Factorio instance
- Auto-upload to Dropbox or other rclone remotes  
- A built-in offline & online map viewer with zoom support  

---

## 🧭 Getting Started

The Factorio Preview Toolkit is designed to work out of the box and comes with everything you need:  
- A standalone executable (`factorio-preview-toolkit`)  
- A configuration file (`config.ini`)  
- A web-based viewer (`viewer.html`)  

### 1. ⬇️ Download the Toolkit
You can find the latest prebuilt release on the [GitHub Releases page](https://github.com/AntiElitz/FactorioPreviewToolkit/releases).
- Download the ZIP file for your operating system
- Extract it to a folder of your choice

### 2. 🟢 Start the Toolkit
Run the provided `factorio-preview-toolkit` executable (just double-click it or start it from a terminal window).
- By default on first launch, it will prompt you to **authorize Dropbox**, so previews can be automatically uploaded and shared with your audience. (See the [🌍 Host the Viewer for Your Audience](#🌍-host-the-viewer-for-your-audience) section.)
- It will now automatically detect Your **currently active Factorio instance** and trigger on Any **map exchange strings** copied to your clipboard
>  ⚠️ Don't want automatic uploads or clipboard monitoring? You can fully customize this in the `config.ini` file. (See the config section below.)

### 3. 🪟 Open the Map Viewer
Open the included `factorio-preview-viewer.html` file in your browser. This local interface lets you explore your map previews easily.
- **Switch between planets** using the tab bar
- **Zoom in and out** with your mouse wheel
- **Pan the map**:
  - Click and drag the image (left mouse button)
  - Or use **W/A/S/D** or **Arrow keys**
- **Reset the view** with a double-click

### 4. 🎲 Generate a Map
In Factorio, go to the map generation screen and create a world as usual.
When you're happy with it:
- Click **Export string**
- Copy the string to your clipboard
The toolkit will detect the copied string, play a confirmation sound, and begin generating previews automatically.

### 5. 🌐 View your Previews
Once the preview images are ready:
- **Refresh the viewer** in your browser
- You'll now see previews for all configured planets


---
## 🌍 Host the Viewer for Your Audience

You can host your own copy of the **Factorio Map Viewer** to share your map with others.  
Here’s how to do it using **GitHub Pages**:

### ✅ Step 1: Fork This Repository
Make sure you’re logged in at [github.com](https://github.com).
- Visit **[https://github.com/AntiElitz/FactorioPreviewToolkit](https://github.com/AntiElitz/FactorioPreviewToolkit)**
- In the top-right corner, click **“Fork”**
- Choose your GitHub account to fork the repo into  
➡️ You now have your own copy of the toolkit!

### 🧩 Step 2: Generate Remote Viewer Config
To make the online viewer work with your uploaded files:
1. **Run the Toolkit locally** with all your planets enabled.
2. This will generate a file at:
FactorioPreviewToolkit/previews/remote_viewer_config.txt
It contains permanent links to your uploaded preview files.

### ✏️ Step 3: Update the Online Viewer
1. In your **forked repository**, go to: `./viewer/viewer_config.js`
2. Click the ✏️ edit icon on GitHub
3. Replace the **entire file** with the contents of `remote_viewer_config.txt`
4. Commit the changes
> ⚠️ If you later **add new planets**, **delete uploaded files**, or if **Dropbox unexpectedly changes links**, you will need to **repeat this process**:  

### 🛠️ Step 4: Enable GitHub Pages
- Go to your new **forked repository**
- Click the **“Settings”** tab in the middle (not the settings for your profile)
- In the left sidebar, scroll down and click **“Pages”**
- Under **“Source”**, select:
  - **Branch:** `main`
  - **Folder:** `/ (root)`
- Click **“Save”**

After a few minutes and refreshing the site, GitHub will provide a link like: <br>
https://your-username.github.io/FactorioPreviewToolkit/

### 🎉 Done!
**Add `viewer/`** to the end of the URL to open your map viewer:  
https://your-username.github.io/FactorioPreviewToolkit/viewer/

You can now share the link to the viewer with your audience!

> ⚠️ **Note:** GitHub Pages only works with **public repositories**.  
Your fork is public by default unless you manually made it private.
---
## ⚙️ Configuration Overview

The toolkit is powered by a flexible `config.ini` file. You can tailor it to suit your workflow.<br>
This section gives you a **high-level overview** of the main options.
> ⚠️ **For a full breakdown of every option**, keep reading the section in the config.ini file.
> 
### 🧭 How Factorio is detected  
Choose between:
- **Automatic detection** – Based on the last focused Factorio window (default)
- **Fixed path** – Manually set the full path to your Factorio executable

### 🎲 How map exchange strings are received  
Choose how new map seeds are fed into the tool:
- **Clipboard monitoring** – Automatically detects when you copy a map string  
- **File monitoring** – Watches a text file for new content (useful for custom workflows)

### 🖼️ How previews are generated  
- Set the **output resolution** of your previews  
- Pick the **planets** to render (e.g. Nauvis, Vulcanus...)  
- Enable **sound feedback** for start/success/failure events

### ☁️ How the images are uploaded or shared  
You can choose to:
- **Skip uploading entirely** if you don’t want to host and share your previews with others
- **Automatically upload** via Dropbox or other cloud providers using `rclone`
- **Copy previews to a synced local folder** (e.g., OneDrive, Dropbox client)

---
## 👩‍💻 Development
Want to contribute or explore how it works?
- [CONTRIBUTING.md](./CONTRIBUTING.md) – Setup, formatting, and dev tools
- [Architecture Overview](./docs/ARCHITECTURE.md) – Structure and core logic
