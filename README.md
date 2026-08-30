# 🚀 Factorio Preview Toolkit

The Factorio Preview Toolkit is a Python-based, cross-platform utility 
that automatically generates preview images for map exchange strings in Factorio. 
It's built for speedrunners who need accurate previews across 
multiple planets and want to share them easily with their community.

## ✨ Features
- Auto-detects map exchange strings from clipboard or file  
- Generates high-resolution PNG previews using the Factorio CLI  
- Automatically uses the currently active Factorio instance
- Supports planets added by mods (your mod folder is detected automatically)
- Marks the spawn position (map center) with a red cross in the viewer
- Composite overview of all planets at once, with a scrollable side column
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
- It will now automatically detect Your **currently active Factorio instance** and trigger on Any **map exchange strings** copied to your clipboard
>  ⚠️ Don't want automatic clipboard monitoring or instance localization? You can fully customize this in the `config.ini` file. (See the config section below.)

### 3. 🪟 Open the Map Viewer
Open the included `factorio-preview-viewer.html` file in your browser. This local interface lets you explore your map previews easily.
- **Switch between planets** using the tab bar, and page through it with **‹ ›** when a
  modpack adds more planets than fit on one row
- **Compare planets** in the **Overview** tab: one planet large, the rest in a scrollable
  column beside it (it can auto-scroll for streaming, see `autoScrollSeconds`)
- **Zoom in and out** with your mouse wheel
- **Pan the map**:
  - Click and drag the image (left mouse button)
  - Or use **W/A/S/D** or **Arrow keys**
- **Reset the view** with a double-click
- The **red cross** marks map position `0, 0` - where you spawn

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

> 💡 **Have web hosting?** Then use `upload_method = ftp` instead of everything below.
> The toolkit uploads the previews *and* the viewer to the same folder, so
> `ftp_public_base_url` is the whole setup - nothing to fork, nothing to copy by hand.
> See the FTP section in `config.ini`.

Here’s how to do it using **GitHub Pages**:

### ✅ Step 1: Update the config.ini File
First, you must update the configuration file to choose your preferred upload method.
1. Open `config.ini` in the root of the project.
2. Find the following line:
`upload_method = skip`
3. Update it to one of the following:
- rclone (recommended) – Uploads the previews directly to a remote service (e.g., Dropbox) using the bundled rclone. The toolkit handles the upload automatically.
- local_sync – Only copies the previews to a local folder (e.g., OneDrive). You are responsible for setting up your own sync software to handle the actual cloud upload.

### ✅ Step 2: Fork This Repository
Make sure you’re logged in at [github.com](https://github.com).
- Visit **[https://github.com/AntiElitz/FactorioPreviewToolkit](https://github.com/AntiElitz/FactorioPreviewToolkit)**
- In the top-right corner, click **“Fork”**
- Choose your GitHub account to fork the repo into  
➡️ You now have your own copy of the toolkit!


### ✏️ Step 3: Update the Online Remote Viewer Config
> ⚠️ If you later **add new planets**, **delete uploaded files**, or if **Dropbox unexpectedly changes links**, you will need to **repeat this step**:  

🔵 **(Recommended) If you uploaded using `upload_method = rclone`:**

When using `upload_method = rclone`, the viewer_config.js content will be generated automatically:
1. **Run the Toolkit locally** with all your planets enabled
2. By default, on first launch, it will prompt you to **authorize Dropbox**
> ⚠️ Authentication failed? Configure rclone manually: <br>
> Open a terminal, navigate to third_party/rclone/&lt;platform&gt;/&lt;architecture&gt;/, and run `rclone config`.
4. This will generate a file at: `FactorioPreviewToolkit/previews/remote_viewer_config.txt` <br>
It contains permanent links to your uploaded preview files
4. In your **forked repository**, go to: `./viewer/viewer_config.js`
5. Click the ✏️ edit icon on GitHub
6. Replace the **entire file** with the contents of `remote_viewer_config.txt`
7. Commit the changes

🟠 **If you upload with `upload_method = local_sync` or manually (Dropbox Desktop, etc.)**

When using another method, the viewer_config.js content has to be configured manually:
1. Go to your hosting service (e.g., Dropbox website) and generate a permanent, static link for each image file in your remote `previews/` folder.
2. Edit your links:
   - If Dropbox gives you a non-fullscreen link like:
     ```
     https://www.dropbox.com/scl/fi/xxxxx/planet.png?...&dl=0
     ```
   - You must **transform it** to a fullscreen link:
     ```
     https://dl.dropboxusercontent.com/scl/fi/xxxxx/planet.png?...
     ```
     (replace `www.dropbox.com` → `dl.dropboxusercontent.com` and **remove** `&dl=0`)
3. In your **forked repository**, go to: `./viewer/viewer_config.js`
4. Click the ✏️ edit icon on GitHub
5. Update the links in the entire file manually
6. Commit the changes


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

### 🧩 Which mods are loaded  
Previews of planets added by mods require those mods to be loaded:
- **Automatic** – Uses the mod folder of the detected Factorio instance (default)
- **Fixed path** – Point `factorio_mod_directory` at the folder containing `mod-list.json`
- **none** – Load no mods at all (vanilla planets only, fastest)

### 🎲 How map exchange strings are received  
Choose how new map seeds are fed into the tool:
- **Clipboard monitoring** – Automatically detects when you copy a map string  
- **File monitoring** – Watches a text file for new content (useful for custom workflows)

### 🖼️ How previews are generated  
- Set the **output resolution** of your previews  
- Pick the **planets** to render via `planets`: `all` (default), `vanilla`, an explicit
  list like `nauvis, gleba, muluna`, or exclusions like `all, !aquilo`.
  Each planet costs a full Factorio startup (~45s with a large modpack), so limiting
  this is the most effective way to speed up generation
- Enable **sound feedback** for start/success/failure events

### ☁️ How the images are uploaded or shared  
You can choose to:
- **Skip uploading entirely** if you don’t want to host and share your previews with others
- **Automatically upload** via Dropbox or other cloud providers using `rclone`
- **Upload to your own web hosting over FTP**, which also puts the viewer itself next to
  the images - so the folder's address is a working page, with no fork and no GitHub Pages
- **Copy previews to a synced local folder** (e.g., OneDrive, Dropbox client)

Uploading happens **while** the previews are generated, one planet at a time, so your
audience sees each planet as soon as it is rendered instead of waiting for the whole run.

---
## 👩‍💻 Development
Want to contribute or explore how it works?
- [CONTRIBUTING.md](./CONTRIBUTING.md) – Setup, formatting, and dev tools
- [Architecture Overview](./docs/ARCHITECTURE.md) – Structure and core logic
