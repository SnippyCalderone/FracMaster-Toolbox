# 🛠️ FracMaster Toolbox – v1.2  
**Release Date:** June 11, 2025

## 📦 Description
FracMaster Toolbox is a field-engineering utility built with CustomTkinter that streamlines the generation of job folder structures and injects critical files into specific stage folders. This GUI-driven tool improves frac data organization by supporting custom naming logic, stage-specific targeting, and instant file preview — all within a clean two-tab layout.

---

## 🧑‍💻 Features

### ✅ Job Setup Tab
- Input fleet, customer, pad, and well/stage counts
- Auto-generate job folder structure with:
  - CSV
  - Post Job Report
  - SFT
  - Redacted FT (optional)
  - WITSML XML (optional)
  - Frac Loader (optional from template)

### ✅ Stage Dropper v2 Tab
- Inject any file type into selected stage ranges
- Dynamically rename output files with custom formatting
- “To Stage X” shortcut auto-fills stage range
- Live preview of all files that will be copied
- Manual input for Customer and Pad to ensure bulletproof naming

---

## 🚀 How to Use
1. Launch the executable (`FracMaster Toolbox.exe`)
2. Navigate to the **Job Setup** tab to generate job folders
3. Switch to **Stage Dropper v2** to:
   - Select the file to inject
   - Choose a file type or define a custom one
   - Pick a job folder and select wells/stage range
4. Review the preview output
5. Click **Copy File to Stage Ranges**

---

## 📋 Changelog (v1.2)
- ✅ Added **two-tab interface** (Job Setup + File Injector)
- ✅ Implemented **stage range selector** with “To Stage X” auto-fill
- ✅ Injected file preview display (horizontally scrollable)
- ✅ Cleaned file naming logic for custom file types
- ✅ Reorganized layout with docking, spacing, and scaling
- ✅ Packaged executable with PyInstaller and custom `.ico`

---

## 💾 Requirements
**None.**  
This app is fully packaged as a standalone `.exe` — no Python install needed.

---

## 🛠️ Built With
- [Python 3.11+](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [PyInstaller](https://pyinstaller.org/)
