# FracMaster Toolbox

**Version:** v1.4
**Framework:** Python 3.x, [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) GUI, [pdfplumber](https://github.com/jsvine/pdfplumber) for PDF parsing

## 📦 Installation & Dependencies

This project relies on:

```text
altgraph==0.17.4
cffi==1.17.1
charset-normalizer==3.4.2
cryptography==45.0.4
customtkinter==5.2.2
darkdetect==0.8.0
et_xmlfile==2.0.0
openpyxl==3.1.5
packaging==25.0
pdfminer.six==20250327
pdfplumber==0.11.6
pefile==2023.2.7
pillow==11.2.1
pycparser==2.22
pyinstaller==6.14.1
pyinstaller-hooks-contrib==2025.5
PyMuPDF==1.26.0
pypdfium2==4.30.1
pywin32-ctypes==0.2.3
setuptools==80.9.0
```

1. **Clone the repo**

   ```bash
   git clone https://github.com/SnippyCalderone/FracMaster-Toolbox.git
   cd FracMaster-Toolbox
   ```

2. **Create & activate a virtual environment**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate       # Windows
   source .venv/bin/activate    # macOS/Linux
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**

   ```bash
   python "FracMaster Toolbox_v1.4.py"
   ```

#### Check out my most recent stable release for FracMaster Toolbox_v1.2 to download the .zip file and use the independent .exe file to run on any machine!



---

## 🎯 End Goal

FracMaster Toolbox streamlines frac-job setup, file injection, and perforation-data extraction in one GUI:

1. **Job Setup**: define job metadata, folder structure, and optionally copy master templates.
2. **File Injector**: push standard files (e.g., your Frac Loader) into specific wells/stages.
3. **Perf Converter**: parse completion procedure PDFs by well to extract stage-by-stage perf depths and plug depths, then export to Excel.

---

## 🔍 Code Structure

* **`FracMasterApp`**

  * Inherits from `ctk.CTk`.
  * Tabs:

    1. `create_job_setup_tab()`
    2. `create_stage_dropper_tab()`
    3. `create_perf_converter_tab()` (built on‐demand)
  * **Config routines**:

    * `save_config()` / `load_config_from_path()` save & load a JSON file named `<Customer>_<Pad>_job_config.json` inside the job folder.
    * `self.config_data` holds the loaded config for injector & perf tabs.
  * **Helpers**: `parse_pages()`, file-browsing, dynamic UI builders.

---

## 🚀 Usage

### 1. Job Setup Tab

1. **Browse Destination**

   * Click **Browse Destination**, select a parent folder (e.g. `C:/Jobs`).
2. **Enter Metadata**

   * **Fleet ID**: e.g. `NE07`
   * **Customer**: e.g. `Sunrise Energy`
   * **Pad Name**: e.g. `SunrisePad`
   * **# of Wells**: e.g. `3`
3. **Generate Well Fields**

   * Click **Generate Well Fields** → three rows appear.
   * Fill each:

     * **Well 1 Name**: `001H`
     * **# of Stages**: `22`
     * etc.
4. **Optional Files**

   * **Include Frac Loader** → browse to your `.xlsm` master loader.
   * **Include Redacted FT** → (tools will create blank PDFs).
   * **Include WITSML** → blank `.xml` if needed.
   * **Blank Master Packet** → browse to a master packet template.
5. **Save Config**

   * Click **Save Config** → writes `SunriseEnergy_SunrisePad_job_config.json` into the job folder.
6. **Generate Job Folder Structure**

   * Click **Generate Job Folder Structure** →

     * Creates `C:/Jobs/Sunrise Energy SunrisePad/`
     * Copies master files into the root and each `Stage 01`, `Stage 02`, … subfolder.
     * Auto-opens the job folder in Explorer.

> **Example:**
>
> ```
> Destination: C:/Users/You/Desktop
> Fleet ID: NE07
> Customer: Sunrise Energy
> Pad Name: SunrisePad
> # of Wells: 2
> Wells: 001H (20), 002H (18)
> Include Frac Loader: ✔  → browse to C:/Templates/FracLoader.xlsm
> Blank Master Packet: ✔  → browse to C:/Templates/Packet.docx
> ```

---

### 2. File Injector Tab

1. **Select File Type**

   * Dropdown: **Frac Loader**, **Primary Stage Files**, or **Other File**.
2. **Frac Loader Flow**

   * **Select Frac Loader to inject:** pre-filled from config, or click **Browse**.
   * **Stage range:** enter start/end (e.g. `5` to `12`).
   * **Select wells:** check the well boxes you want to inject (auto-populated from JSON).
   * **Inject Frac Loader**: distributes copies named `001H SunrisePad Frac Loader Stage 05.xlsm` into each chosen `Stage XX` folder.

> **Example:**
>
> ```
> File Type: Frac Loader
> Browse → select C:/Jobs/SunrisePad/FracLoader.xlsm
> Stage range: 3  to  8
> Select wells: ☑ 001H   ☐ 002H
> [Inject Frac Loader] → copies loader into Stage 03–08 for well 001H only.
> ```

---

### 3. Perf Converter Tab

1. **Ensure Config Loaded**

   * The tab auto-rebuilds after **Save Config** or **Generate Job**.
2. **Enter Page Ranges & Clusters**

   * One row per well (e.g. `001H`, `002H`, …).
   * **Page Ranges**: e.g. `21-22,24,26-27`
   * **# Clusters/Stage**: e.g. `14`
3. **Upload Completion Procedure PDF**

   * Click button → select your CP PDF.
   * Parser uses two methods per well:

     1. **Table scan** for headers containing “Stage” & “Plug”
     2. **Line-by-line regex** fallback (`Stage\s+(\d+)`)
   * Results appear in the textbox:

     ```
     === 001H: Parsed 20 stages ===
       Stage 01: plug=..., top=..., bot=...
       …
     ```
4. **Proceed to Next Well’s Perf Data**

   * Walk through each well’s output one at a time (enables review).
5. **Export to Excel**

   * After all wells are parsed, exports an `.xlsx` file summarizing:

     | Well | Stage | Plug Depth | Top Perf | Bottom Perf |
     | ---- | ----- | ---------- | -------- | ----------- |
     | 001H | 01    | 5900       | 5932     | 5951        |
     | …    | …     | …          | …        | …           |

> **Example:**
>
> ```
> Wells:
>  001H | 21-22   | 14
>  003H | 23-24   | 12
>  005H | 25-26   | 10
>
> [Upload Completion Procedure PDF]
> → Displays “Parsed 0 stages” or full details
> [Proceed to Next Well’s Perf Data]
> [Export to Excel]
> → Saves “Perf_001H.xlsx” in the job folder
> ```

---

## 🛠️ Customization & Troubleshooting

* **Filename sanitization**: spaces in Customer/Pad become underscores in JSON filename.
* **Config storage**: JSON lives in the job folder alongside stage subfolders.
* **Error display**: any I/O or parsing errors show in the status bar or result box.
* **Adding file-types**: extend `toggle_file_type_inputs()` and `inject_*` methods for new modes.
* **Regex tweaks**: adjust `parse_pages()` or `re.match(r"Stage\s+(\d+)",…)` to fit PDF variations.

---

## ✨ Future Enhancements

* **WF Generator** (Perf Converter)
  Add a “WF Generator” button that, based on your parsed perf data and cluster counts, will auto-generate a Petrix Stage File (`.wf`), ready for hydraulic modeling and fracture design.

* **FT Calculator**
  Upload a Proposal PDF to automatically extract and calculate Frac Tool pricing: costs, discounts, HHP brackets, mileage brackets, etc., then export a detailed cost summary.

* **Packet Assist**
  Use your Blank Master Packet `.xlsm` as a target for both WITSML (`.xml`) and manual inputs. In the Config Mapper you’ll define the destination cell addresses once (saved in a per-job `config_mapper.json`), so Packet Assist can:

  1. Inject WITSML outputs without corrupting VBA macros or formulas
  2. Overwrite only the named cells for each stage
  3. Remember your mappings across jobs
  4. Eventually tie into the FracPro OPS API for fully automated data uploads and maintain a local history of past stage data.

* **Primary Stage Files Injection**
  Extend the File Injector tab to handle PJR, SFT, Redacted FT, CSV, XML, and any other “per-stage” files in bulk—select file type, wells, stage range, and drop them into the right folders in one click.

* **FracPro / FracOps API Integration**
  Build a direct link to your fracturing software’s back-end API to pull job metadata, push packets, or sync historical data automatically.

* **Dark/Light Theme Toggle**
  Leverage CustomTkinter’s built-in themes so you can switch between dark and light modes on the fly.

* **Batch Perf Conversion**
  Allow processing of multiple Completion Procedure PDFs at once—ideal for pads with 10+ wells—queuing them through the Perf Converter and exporting a combined Excel report.

---

 
******If you have additional ideas or want to help implement any of these, please contribute on GitHub!*******

---

> **Enjoy streamlined frac workflows!**
> Report issues or contribute on [GitHub](https://github.com/SnippyCalderone/FracMaster-Toolbox).