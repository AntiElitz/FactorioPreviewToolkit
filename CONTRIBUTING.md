# 🛠️ Contributing to Factorio Preview Toolkit

Thank you for your interest in contributing! This toolkit helps automate the generation of map previews for Factorio speedrunners. Whether you're fixing bugs, improving the UI, adding features, or updating documentation — we welcome all contributions.

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/AntiElitz/FactorioPreviewToolkit.git
cd FactorioPreviewToolkit
```

### 2. Set Up a Virtual Environment

We recommend using a virtual environment to isolate dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Development Dependencies

Install everything needed for development, testing, and building:

```bash
pip install .[dev]
```

If you're on **Linux** and want to use GUI features (like tkinter popups), you may also need to install `tkinter` manually:

- On **Debian/Ubuntu**:
  ```bash
  sudo apt install python3-tk
  ```
- On **Arch Linux**:
  ```bash
  sudo pacman -S tk
  ```
- On **Fedora / RHEL / CentOS**:
  ```bash
  sudo dnf install python3-tkinter
  ```
- On **openSUSE**:
  ```bash
  sudo zypper install python3-tk
  ```



---

## 💻 Running the Toolkit Locally

To launch the main tool, use the following command **from the project root**:

```bash
python -m src.FactorioPreviewToolkit
```

This ensures Python locates the main module correctly inside the `src` directory.

---

## 🧪 Formatting, Linting, and Type Checking

This project uses:

- [`black`](https://black.readthedocs.io/) for auto-formatting
- [`mypy`](http://mypy-lang.org/) for static type checking
- [`pre-commit`](https://pre-commit.com/) for running checks before each commit

### Set up the pre-commit hooks:

```bash
pre-commit install
```

### Run `black` Manually

Auto-format your code with:

```bash
black .
```


### Run `mypy` in Strict Mode

This project uses `mypy` in strict mode for full static type checking:

```bash
mypy --strict .
```

### Run all checks manually:

```bash
pre-commit run --all-files
```

---

## 🛠️ Building a Standalone Executable

You can generate a one-file executable using PyInstaller by running:

```bash
python -m toolkit_build.build
```

This creates a zipped bundle with platform-specific binaries, configurations, and a viewer UI, ready to distribute.

---
## 🚢 Releasing

Use the release command to:

- Bump the version
- Build the executable
- Tag the release
- Push to GitHub (which triggers the cross-platform build pipeline)

```bash
python -m toolkit_build.release
```

This triggers GitHub Actions to build the toolkit for Windows, Linux, and macOS and (if configured) attach the zip files to a GitHub release.

---

## ❤️ How to Contribute

1. Fork this repository
2. Create a new branch: `git checkout -b my-fix`
3. Make your changes
4. Run lint/type checks
5. Push to your fork and open a Pull Request

---

## 🧩 Need Help?

- Open an [Issue](https://github.com/AntiElitz/FactorioPreviewToolkit/issues)
- Or ping @AntiElitz on Discord

Thanks for making this toolkit better!
