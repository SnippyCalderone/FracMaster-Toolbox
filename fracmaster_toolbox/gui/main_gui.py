import customtkinter as ctk
import os
import shutil
import json
from tkinter import filedialog
import re
import subprocess
import sys
from fracmaster_toolbox.utils import perf_parser, file_utils

# Dark mode and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FracMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = {}
        self.title("FracMaster Toolbox - v1.4")
        self.geometry("1300x800")

        # Tab view
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(expand=True, fill="both")
        self.create_job_setup_tab()
        self.create_stage_dropper_tab()
        self.create_perf_converter_tab()

    def refresh_tabs_for_config(self):
        """Rebuild tabs that rely on loaded configuration."""
        if "File Injector" in self.tabs.tab_names():
            self.tabs.remove("File Injector")
        if "Perf Converter" in self.tabs.tab_names():
            self.tabs.remove("Perf Converter")
        self.create_stage_dropper_tab()
        self.create_perf_converter_tab()

    # -- Helpers --------------------------------------------------------------
    def _extract_number(self, cell):
        """Return the first numeric value found in a table cell, or None."""
        if not cell:
            return None
        m = re.search(r"\d+(?:\.\d+)?", str(cell).replace(',', ''))
        return float(m.group()) if m else None

    def _extract_numbers(self, text):
        """Return list of numeric values from arbitrary text."""
        return [float(n.replace(',', '')) for n in re.findall(r"\d+(?:\.\d+)?", text)]

    # -- JSON Config Save/Load -------------------------------------------------
    def save_config(self):
        # 1) Determine where to save: prefer the current job path if set, 
        #    otherwise use whatever is in the Destination entry.
        destination = getattr(self, "current_job_path", None)
        if not destination:
            destination = self.destination_entry.get().strip()

        if not destination:
            self.status_label.configure(text="⚠️ Select destination first.")
            return

        # 2) Gather well names & stage counts
        wells = []
        for entry, count in self.well_entries:
            name = entry.get().strip()
            try:
                stages = int(count.get().strip())
            except ValueError:
                stages = 0
            if name and stages > 0:
                wells.append({"name": name, "stages": stages})

        # 3) Gather the checkbox options and file paths
        opts = {
            "include_frac_loader":      bool(self.frac_loader_checkbox.get()),
            "master_frac_loader_path":  self.file_paths["Master Frac Loader"].get().strip(),
            "include_redacted_ft":      bool(self.redacted_checkbox.get()),
            "include_witsml":           bool(self.witsml_checkbox.get()),
            "blank_master_packet_path": self.file_paths["Blank Master Packet"].get().strip()
        }

        # 4) Core fields
        cust  = self.customer_entry.get().strip()
        pad   = self.pad_entry.get().strip()
        fleet = self.fleet_entry.get().strip()

        # 5) Build the config dict to serialize
        cfg = {
            "destination": destination,
            "fleet":       fleet,
            "customer":    cust,
            "pad":         pad,
            "wells":       wells,
            "options":     opts
        }

        # 6) Create a filesystem-safe filename
        safe_cust = cust.replace(" ", "_")
        safe_pad  = pad.replace(" ", "_")
        filename  = f"{safe_cust}_{safe_pad}_job_config.json"
        path      = os.path.join(destination, filename)

        # 7) Write it out (and stash in memory)
        try:
            with open(path, "w") as f:
                json.dump(cfg, f, indent=4)

            # keep a copy around for the injector tab
            self.config_data = cfg

            # show forward-slashes in status for readability
            display_path = path.replace("\\", "/")
            self.status_label.configure(text=f"✅ Config saved to {display_path}")
        except Exception as e:
            self.status_label.configure(text=f"⚠️ Save error: {e}")
        else:
            # update other tabs with the new configuration
            self.refresh_tabs_for_config()
            self._build_perf_converter_rows()

    def load_config(self):
        file = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file:
            self.load_config_from_path(file)

    def load_config_from_path(self, path):
        try:
            with open(path) as f:
                cfg = json.load(f)
        except Exception as e:
            self.status_label.configure(text=f"⚠️ Load error: {e}")
            return
        # Populate UI fields
        self.destination_entry.delete(0, 'end')
        self.destination_entry.insert(0, cfg.get("destination", ""))
        self.fleet_entry.delete(0, 'end')
        self.fleet_entry.insert(0, cfg.get("fleet", ""))
        self.customer_entry.delete(0, 'end')
        self.customer_entry.insert(0, cfg.get("customer", ""))
        self.pad_entry.delete(0, 'end')
        self.pad_entry.insert(0, cfg.get("pad", ""))
        wells = cfg.get("wells", [])
        self.num_wells_entry.delete(0, 'end')
        self.num_wells_entry.insert(0, str(len(wells)))
        self.generate_well_name_fields()
        for i, well in enumerate(wells):
            if i < len(self.well_entries):
                entry, count = self.well_entries[i]
                entry.delete(0, 'end')
                entry.insert(0, well.get("name", ""))
                count.delete(0, 'end')
                count.insert(0, str(well.get("stages", "")))
        opts = cfg.get("options", {})
        # Frac Loader
        if opts.get("include_frac_loader"):
            self.frac_loader_checkbox.select()
        else:
            self.frac_loader_checkbox.deselect()
        self.toggle_frac_loader_picker()
        self.file_paths["Master Frac Loader"].delete(0, 'end')
        self.file_paths["Master Frac Loader"].insert(0, opts.get("master_frac_loader_path", ""))
        # Redacted FT
        if opts.get("include_redacted_ft"):
            self.redacted_checkbox.select()
        else:
            self.redacted_checkbox.deselect()
        # WITSML
        if opts.get("include_witsml"):
            self.witsml_checkbox.select()
        else:
            self.witsml_checkbox.deselect()
        # Blank Packet
        if opts.get("blank_master_packet_path"):
            self.blank_packet_checkbox.select()
        else:
            self.blank_packet_checkbox.deselect()
        self.toggle_blank_packet_picker()
        self.file_paths["Blank Master Packet"].delete(0, 'end')
        self.file_paths["Blank Master Packet"].insert(0, opts.get("blank_master_packet_path", ""))
        self.status_label.configure(text=f"✅ Config loaded from {path}")
        self.config_data = cfg

        # Rebuild tabs that rely on this configuration
        self.refresh_tabs_for_config()
        self._build_perf_converter_rows()



    # -- Job Setup Tab ----------------------------------------------------------
    def create_job_setup_tab(self):
        tab = self.tabs.add("Job Setup")
        # Destination
        self.destination_entry = ctk.CTkEntry(tab, width=400, placeholder_text="Select Destination Folder for Job")
        self.destination_entry.grid(row=0, column=0, padx=10, pady=10)
        dest_button = ctk.CTkButton(tab, text="Browse Destination", command=self.browse_destination_folder)
        dest_button.grid(row=0, column=1, padx=10, pady=10)
        # Load/Save
        load_button = ctk.CTkButton(tab, text="Load Config", command=self.load_config)
        load_button.grid(row=0, column=2, padx=5, pady=10)
        save_button = ctk.CTkButton(tab, text="Save Config", command=self.save_config)
        save_button.grid(row=0, column=3, padx=5, pady=10)
        # Fleet, Customer, Pad, # Wells
        self.fleet_entry = ctk.CTkEntry(tab, width=150, placeholder_text="Fleet ID (e.g. NE07)")
        self.fleet_entry.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.customer_entry = ctk.CTkEntry(tab, width=300, placeholder_text="Customer Name")
        self.customer_entry.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.pad_entry = ctk.CTkEntry(tab, width=300, placeholder_text="Pad Name")
        self.pad_entry.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.num_wells_entry = ctk.CTkEntry(tab, width=100, placeholder_text="# of Wells")
        self.num_wells_entry.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        # Generate Well Fields Button
        gen_fields_btn = ctk.CTkButton(tab, text="Generate Well Fields", command=self.generate_well_name_fields)
        gen_fields_btn.grid(row=4, column=1, padx=10, pady=5)

        # list that generate_well_name_fields will populate
        self.well_entries = []

        # Optional files
        opt_frame = ctk.CTkFrame(tab)
        opt_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="nw")
        self.frac_loader_checkbox = ctk.CTkCheckBox(opt_frame, text="Include Frac Loader", command=self.toggle_frac_loader_picker)
        self.frac_loader_checkbox.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.redacted_checkbox = ctk.CTkCheckBox(opt_frame, text="Include Redacted FT")
        self.redacted_checkbox.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.witsml_checkbox = ctk.CTkCheckBox(opt_frame, text="Include WITSML")
        self.witsml_checkbox.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.blank_packet_checkbox = ctk.CTkCheckBox(opt_frame, text="Blank Master Packet", command=self.toggle_blank_packet_picker)
        self.blank_packet_checkbox.grid(row=3, column=0, sticky="w", padx=5, pady=2)
        # Pickers
        self.frac_loader_picker_frame = ctk.CTkFrame(tab)
        self.frac_loader_picker_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.frac_loader_picker_frame.grid_remove()
        self.blank_packet_picker_frame = ctk.CTkFrame(tab)
        self.blank_packet_picker_frame.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.blank_packet_picker_frame.grid_remove()
        self.file_paths = {}
        self.create_file_picker(self.frac_loader_picker_frame, "Master Frac Loader")
        self.create_file_picker(self.blank_packet_picker_frame, "Blank Master Packet")
        # Wells container
        self.well_name_frame = ctk.CTkFrame(tab)
        self.well_name_frame.grid(row=8, column=0, columnspan=2, padx=10, pady=10, sticky="nw")
        # Status & generate
        self.status_label = ctk.CTkLabel(tab, text="")
        self.status_label.grid(row=99, column=0, columnspan=2, pady=10)
        gen_btn = ctk.CTkButton(tab, text="Generate Job Folder Structure", command=self.generate_job_structure)
        gen_btn.grid(row=100, column=0, columnspan=2, pady=30)

    def toggle_frac_loader_picker(self):
        if self.frac_loader_checkbox.get():
            self.frac_loader_picker_frame.grid()
        else:
            self.frac_loader_picker_frame.grid_remove()

    def toggle_blank_packet_picker(self):
        if self.blank_packet_checkbox.get():
            self.blank_packet_picker_frame.grid()
        else:
            self.blank_packet_picker_frame.grid_remove()

    def create_file_picker(self, parent, label):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=0, pady=2)
        entry = ctk.CTkEntry(frame, width=400, placeholder_text=f"Select {label} File")
        entry.pack(side="left", padx=5)
        button = ctk.CTkButton(frame, text="Browse", command=lambda: self.browse_and_assign_file(label, entry))
        button.pack(side="left")
        self.file_paths[label] = entry

    def browse_and_assign_file(self, label, entry_field):
        filepath = filedialog.askopenfilename()
        if filepath:
            entry_field.delete(0, "end")
            entry_field.insert(0, filepath)

    def browse_destination_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination_entry.delete(0, "end")
            self.destination_entry.insert(0, folder)
            # auto-load config if present
            for fname in os.listdir(folder):
                if fname.endswith("_job_config.json"):
                    self.load_config_from_path(os.path.join(folder, fname))
                    break

    def generate_well_name_fields(self):
        for widget in self.well_name_frame.winfo_children():
            widget.destroy()
        self.well_entries.clear()
        try:
            num = int(self.num_wells_entry.get())
            for i in range(num):
                row = ctk.CTkFrame(self.well_name_frame)
                row.pack(fill="x", pady=2)
                name_ent = ctk.CTkEntry(row, width=200, placeholder_text=f"Well {i+1} Name")
                name_ent.pack(side="left", padx=5)
                cnt_ent = ctk.CTkEntry(row, width=100, placeholder_text="# of Stages")
                cnt_ent.pack(side="left", padx=5)
                self.well_entries.append((name_ent, cnt_ent))
        except ValueError:
            pass

    def generate_job_structure(self):
        base = self.destination_entry.get().strip()
        fleet = self.fleet_entry.get().strip()
        cust = self.customer_entry.get().strip()
        pad = self.pad_entry.get().strip()
        use_frac = bool(self.frac_loader_checkbox.get())
        include_red = bool(self.redacted_checkbox.get())
        include_wit = bool(self.witsml_checkbox.get())
        use_blank = bool(self.blank_packet_checkbox.get())
        master_loader = self.file_paths["Master Frac Loader"].get().strip() if use_frac else None
        blank_pkt = self.file_paths["Blank Master Packet"].get().strip() if use_blank else None
        folder_name = f"{cust} {pad}"
        full_path = os.path.join(base, folder_name)
        os.makedirs(full_path, exist_ok=True)
        self.current_job_path = full_path
        if use_frac and os.path.exists(master_loader):
            ext = os.path.splitext(master_loader)[1]
            out_name = f"{cust} {pad} Master Frac Loader{ext}"
            shutil.copy(master_loader, os.path.join(full_path, out_name))
        if use_blank and os.path.exists(blank_pkt):
            ext = os.path.splitext(blank_pkt)[1]
            out_name = f"{cust} {pad} Blank Master Packet{ext}"
            shutil.copy(blank_pkt, os.path.join(full_path, out_name))
        for entry, cnt in self.well_entries:
            well = entry.get().strip()
            try:
                stages = int(cnt.get().strip())
            except ValueError:
                continue
            well_path = os.path.join(full_path, well)
            os.makedirs(well_path, exist_ok=True)
            for s in range(1, stages + 1):
                stage_str = f"Stage {s:02}"
                spath = os.path.join(well_path, stage_str)
                os.makedirs(spath, exist_ok=True)
                if use_frac and os.path.exists(master_loader):
                    loader_name = f"{well} {pad} Frac Loader {stage_str}.xlsm"
                    shutil.copy(master_loader, os.path.join(spath, loader_name))
                open(os.path.join(spath, f"{fleet}_{cust}_{pad}_{well}_CSV_{stage_str}.csv"), 'a').close()
                open(os.path.join(spath, f"{fleet}_{cust}_{pad}_{well}_Post Job Report_{stage_str}.pdf"), 'a').close()
                open(os.path.join(spath, f"{fleet}_{cust}_{pad}_{well}_SFT_{stage_str}.pdf"), 'a').close()
                open(os.path.join(spath, "PJR.csv"), 'a').close()
                open(os.path.join(spath, "PJR.rtf"), 'a').close()
                if include_red:
                    open(os.path.join(spath, f"{fleet}_{cust}_{pad}_{well}_Redacted FT_{stage_str}.pdf"), 'a').close()
                if include_wit:
                    open(os.path.join(spath, f"{fleet}_{cust}_{pad}_{well}_Job File_{stage_str}.xml"), 'a').close()
        try:
            real = os.path.realpath(full_path)
            if sys.platform.startswith("win"):
                os.startfile(real)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", real])
            else:
                subprocess.run(["xdg-open", real])
        except Exception:
            pass
        self.status_label.configure(text="✅ Successful File Folder Generation!")
        self.save_config()
        # refresh tabs now that config and folders are created
        self.refresh_tabs_for_config()

    # -- File Injector Tab ------------------------------------------------------
        # -- File Injector Tab ------------------------------------------------------
    def create_stage_dropper_tab(self):
        tab = self.tabs.add("File Injector")

        # 1) File-type selector
        self.file_type_var = ctk.StringVar(value="")
        self.file_type_dropdown = ctk.CTkOptionMenu(
            tab,
            values=["Frac Loader", "Primary Stage Files", "Other File"],
            variable=self.file_type_var,
            command=self.toggle_file_type_inputs
        )
        self.file_type_dropdown.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.file_type_dropdown.set("")

        # 2) Container for the dynamic injector UI
        self.injector_frame = ctk.CTkFrame(tab)
        self.injector_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nw")

    def clear_injector_frame(self):
        for widget in self.injector_frame.winfo_children():
            widget.destroy()

    def toggle_file_type_inputs(self, value):
        self.clear_injector_frame()

        if value == "Frac Loader":
            cfg = getattr(self, "config_data", {})
            if not cfg:
                return self.status_label.configure(text="⚠️ Load a config first!")

            # file picker
            ctk.CTkLabel(self.injector_frame, text="Select Frac Loader to inject:")\
                .pack(anchor="w", pady=(0,5))
            self.inject_frac_entry = ctk.CTkEntry(self.injector_frame, width=400)
            self.inject_frac_entry.insert(0, cfg["options"].get("master_frac_loader_path",""))
            self.inject_frac_entry.pack(side="left", pady=2)
            ctk.CTkButton(
                self.injector_frame, text="Browse",
                command=lambda: self.browse_and_assign_file("inject_frac_loader", self.inject_frac_entry)
            ).pack(side="left", padx=5)

            # stage-range inputs
            range_frame = ctk.CTkFrame(self.injector_frame)
            range_frame.pack(fill="x", pady=(5,10))
            ctk.CTkLabel(range_frame, text="Stage range:").pack(side="left", padx=(0,5))
            self.start_stage_entry = ctk.CTkEntry(range_frame, width=50, placeholder_text="Start")
            self.start_stage_entry.pack(side="left", padx=(0,5))
            ctk.CTkLabel(range_frame, text="to").pack(side="left", padx=(0,5))
            self.end_stage_entry = ctk.CTkEntry(range_frame, width=50, placeholder_text="End")
            self.end_stage_entry.pack(side="left", padx=(0,5))

            # well checkboxes
            box = ctk.CTkFrame(self.injector_frame)
            box.pack(fill="x", pady=10)
            self.inject_well_vars = {}
            ctk.CTkLabel(box, text="Select wells:").grid(row=0, column=0, sticky="w")
            for i, wname in enumerate([w["name"] for w in cfg["wells"]], start=1):
                var = ctk.BooleanVar(value=True)
                chk = ctk.CTkCheckBox(box, text=wname, variable=var)
                chk.grid(row=(i//5)+1, column=(i-1)%5, padx=5, pady=2, sticky="w")
                self.inject_well_vars[wname] = var

            # inject button
            ctk.CTkButton(
                self.injector_frame, text="Inject Frac Loader",
                command=self.inject_frac_loader
            ).pack(pady=(10,0))

        else:
            ctk.CTkLabel(
                self.injector_frame,
                text=f"⚙️ “{value}” injector coming soon."
            ).pack()

    def inject_frac_loader(self):
        cfg = self.config_data
        src = self.inject_frac_entry.get().strip()
        if not os.path.isfile(src):
            return self.status_label.configure(text="⚠️ Pick a valid Frac Loader file first.")

        # parse stage range
        try:
            start = max(1, int(self.start_stage_entry.get().strip()))
        except:
            start = 1
        try:
            end = max(start, int(self.end_stage_entry.get().strip()))
        except:
            end = None

        base      = cfg["destination"]
        cust      = cfg["customer"]
        pad       = cfg["pad"]
        wells_cfg = {w["name"]: w["stages"] for w in cfg["wells"]}

        for well, max_stage in wells_cfg.items():
            if not self.inject_well_vars[well].get():
                continue
            real_end = end if end and end <= max_stage else max_stage

            for s in range(start, real_end + 1):
                stage_str = f"Stage {s:02}"
                dst = os.path.join(base, f"{cust} {pad}", well, stage_str)
                if os.path.isdir(dst):
                    ext = os.path.splitext(src)[1]
                    fname = f"{well} {pad} Frac Loader {stage_str}{ext}"
                    shutil.copy(src, os.path.join(dst, fname))

        self.status_label.configure(text="✅ Frac Loader injected!")


    # -- Perf Converter Tab -----------------------------------------------------
    def create_perf_converter_tab(self):
        tab = self.tabs.add("Perf Converter")

        # Instructions
        instr = (
            "Upload a Completion Procedure PDF. The tool will extract:\n\n"
            " - Top/Bottom Perf Depths\n"
            " - Plug Depths\n\n"
            "Enter only Page Ranges and # Clusters/Stage for each well below,\n"
            "then click “Proceed to Next Well’s Perf Data”."
        )
        ctk.CTkLabel(tab, text=instr, justify="left").grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")

        # Scrollable frame for well inputs
        self.perf_well_data = []  # list of tuples (well_name, start_entry, end_entry, cluster_entry)
        self.perf_data = {}       # store parsed results
        self.current_well_index = 0

        self.perf_rows_frame = ctk.CTkScrollableFrame(tab, width=1200, height=200)
        self.perf_rows_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="w")

        # Build rows based on current config
        self._build_perf_converter_rows()

        # Upload button
        upload_btn = ctk.CTkButton(tab, text="Upload Completion Procedure PDF", command=self.upload_pdf)
        upload_btn.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        # Manual config loader in case Job Setup tab didn't propagate
        load_cfg_btn = ctk.CTkButton(tab, text="Load Config", command=self.load_config)
        load_cfg_btn.grid(row=2, column=2, padx=10, pady=10, sticky="w")

        # Result box + Next/Export button
        self.next_button = ctk.CTkButton(tab, text="Proceed to Next Well’s Perf Data",
                                        command=self.show_next_well, state="disabled")
        self.next_button.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        scroll = ctk.CTkScrollableFrame(tab, width=925, height=400)
        scroll.grid(row=3, column=0, columnspan=4, padx=10, pady=5, sticky="w")
        self.result_box = ctk.CTkTextbox(scroll, wrap="none", width=900, height=380)
        self.result_box.pack(padx=5, pady=5, fill="both", expand=True)
        self._render_perf_results()


    def _build_perf_converter_rows(self):
        """Create per-well page range and cluster entry rows."""
        if not hasattr(self, "perf_rows_frame"):
            return
        for widget in self.perf_rows_frame.winfo_children():
            widget.destroy()
        self.perf_well_data = []
        wells = self.config_data.get("wells") or []
        if not wells:
            ctk.CTkLabel(self.perf_rows_frame, text="⚠️ Load a job config first!").pack(pady=20)
            return
        for i, w in enumerate(wells):
            name = w["name"]
            start = ctk.CTkEntry(self.perf_rows_frame, placeholder_text=f"{name}: Start Pg")
            end = ctk.CTkEntry(self.perf_rows_frame, placeholder_text="End Pg")
            cl = ctk.CTkEntry(self.perf_rows_frame, placeholder_text="# Clusters/Stage")
            start.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            end.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            cl.grid(row=i, column=2, padx=5, pady=2, sticky="w")
            self.perf_well_data.append((name, start, end, cl))

    def _render_perf_results(self):
        """Render self.perf_data into the results textbox."""
        self.result_box.delete("1.0", "end")
        for well, stages in self.perf_data.items():
            self.result_box.insert("end", f"\n=== {well}: Parsed {len(stages)} stages ===\n")
            for stg, plug, top, bot in stages:
                self.result_box.insert(
                    "end", f"  Stage {stg}: plug={plug}, top={top}, bot={bot}\n"
                )
        if self.perf_data:
            self.next_button.configure(state="normal")

    def upload_pdf(self):
        pdf = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not pdf:
            return

        # reset state
        self.perf_data.clear()
        self.result_box.delete("1.0", "end")
        self.current_well_index = 0

        # Build well_map from entry rows
        well_map = {}
        for well_name, start_e, end_e, cl_e in self.perf_well_data:
            try:
                start = int(start_e.get())
            except Exception:
                start = 0
            try:
                end = int(end_e.get())
            except Exception:
                end = 0
            try:
                ncl = int(cl_e.get())
            except Exception:
                ncl = 0
            well_map[well_name] = {
                "start_page": start,
                "end_page": end,
                "n_clusters": ncl,
            }

        payload = {"job_config": self.config_data, "well_map": well_map}

        try:
            from fracmaster_toolbox.ob_agent import call_ob_agent
            result = call_ob_agent("perf_converter_parser", {"pdf_path": pdf, **payload})
            perf_data = result["perf_data"]
        except Exception:
            perf_data = perf_parser.parse_pdf(pdf, well_map)

        self.perf_data = perf_data
        self._render_perf_results()

    def show_next_well(self):
        wells = list(self.perf_data)
        if self.current_well_index < len(wells):
            w = wells[self.current_well_index]
            self.result_box.insert("end", f"\n>>> {w} <<<\n")
            for stg, plug, top, bot in self.perf_data[w]:
                self.result_box.insert("end", f"  {stg}: plug={plug}, top={top}, bot={bot}\n")
            self.current_well_index += 1
            if self.current_well_index >= len(wells):
                self.next_button.configure(text="Export to Excel", command=self.export_excel)
        else:
            self.export_excel()

    def export_excel(self):
        default = "Perf_Converter_" + "-".join(self.perf_data.keys()) + ".xlsx"
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=default, filetypes=[("Excel","*.xlsx")])
        if not path:
            return
        file_utils.save_perf_excel(self.perf_data, path)
        self.result_box.insert("end", f"\n✅ Saved Excel: {path}\n")


def main():
    app = FracMasterApp()
    app.mainloop()


if __name__ == "__main__":
    main()