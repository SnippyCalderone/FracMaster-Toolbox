import customtkinter as ctk
import os
import shutil
import json
from tkinter import filedialog
import re
import subprocess
import sys
from fracmaster_toolbox.utils import perf_parser
from fracmaster_toolbox.ob_agent import call_ob_agent
import csv

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FracMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = {}
        self.title("FracMaster Toolbox - v1.4")
        self.geometry("1300x800")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        self.create_job_setup_tab()
        self.create_stage_dropper_tab()
        self.create_perf_converter_tab()

    def refresh_tabs_for_config(self):
        try:
            existing_tabs = self.tabs._tab_dict.keys()  # FIX: tab_names() is invalid in CTkTabview
            if "File Injector" in existing_tabs:
                self.tabs.delete("File Injector")
            if "Perf Converter" in existing_tabs:
                self.tabs.delete("Perf Converter")
        except Exception as e:
            print(f"[DEBUG] Error refreshing tabs: {e}")
        if not self.config_data:
            print("[DEBUG] refresh_tabs_for_config called without config_data set")
        self.create_stage_dropper_tab()
        self.create_perf_converter_tab()

    def save_config(self):
        destination = getattr(self, "current_job_path", None)
        if not destination:
            destination = self.destination_entry.get().strip()
        if not destination:
            self.status_label.configure(text="⚠️ Select destination first.")
            return

        wells = []
        for entry, count in self.well_entries:
            name = entry.get().strip()
            try:
                stages = int(count.get().strip())
            except ValueError:
                stages = 0
            if name and stages > 0:
                wells.append({"name": name, "stages": stages})

        opts = {
            "include_frac_loader": bool(self.frac_loader_checkbox.get()),
            "master_frac_loader_path": self.file_paths["Master Frac Loader"].get().strip(),
            "include_redacted_ft": bool(self.redacted_checkbox.get()),
            "include_witsml": bool(self.witsml_checkbox.get()),
            "blank_master_packet_path": self.file_paths["Blank Master Packet"].get().strip()
        }

        cust = self.customer_entry.get().strip()
        pad = self.pad_entry.get().strip()
        fleet = self.fleet_entry.get().strip()

        cfg = {
            "destination": destination,
            "fleet": fleet,
            "customer": cust,
            "pad": pad,
            "wells": wells,
            "options": opts
        }

        safe_cust = cust.replace(" ", "_")
        safe_pad = pad.replace(" ", "_")
        filename = f"{safe_cust}_{safe_pad}_job_config.json"
        path = os.path.join(destination, filename)

        try:
            with open(path, "w") as f:
                json.dump(cfg, f, indent=4)
            self.config_data = cfg
            normalized = path.replace("\\", "/")
            self.status_label.configure(text=f"✅ Config saved to {normalized}")
        except Exception as e:
            self.status_label.configure(text=f"⚠️ Save error: {e}")
        else:
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

        self.config_data = cfg  # Ensure config is set before tab refresh
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
        if opts.get("include_frac_loader"):
            self.frac_loader_checkbox.select()
        else:
            self.frac_loader_checkbox.deselect()
        self.toggle_frac_loader_picker()
        self.file_paths["Master Frac Loader"].delete(0, 'end')
        self.file_paths["Master Frac Loader"].insert(0, opts.get("master_frac_loader_path", ""))
        if opts.get("include_redacted_ft"):
            self.redacted_checkbox.select()
        else:
            self.redacted_checkbox.deselect()
        if opts.get("include_witsml"):
            self.witsml_checkbox.select()
        else:
            self.witsml_checkbox.deselect()
        if opts.get("blank_master_packet_path"):
            self.blank_packet_checkbox.select()
        else:
            self.blank_packet_checkbox.deselect()
        self.toggle_blank_packet_picker()
        self.file_paths["Blank Master Packet"].delete(0, 'end')
        self.file_paths["Blank Master Packet"].insert(0, opts.get("blank_master_packet_path", ""))
        self.status_label.configure(text=f"✅ Config loaded from {path}")

        self.refresh_tabs_for_config()
        self._build_perf_converter_rows()
        
    def export_csv_for_well(self, well: str):
        if well not in self.perf_data:
            self.status_label.configure(text=f"⚠️ No data for {well}")
            return

        cfg = self.config_data
        base = cfg.get("destination", "")
        cust = cfg.get("customer", "")
        pad  = cfg.get("pad", "")
        well_dir = os.path.join(base, f"{cust} {pad}", well)
        os.makedirs(well_dir, exist_ok=True)
        out_path = os.path.join(well_dir, f"{well} Perf Summary.csv")

        # ✅ SORT HERE before writing
        rows = sorted(self.perf_data[well], key=lambda r: int(str(r[0]).zfill(2)))

        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Well", "Stage", "Plug(ftKB)", "Top(ftKB)", "Bottom(ftKB)"])
            for stg, plug, top, bot in rows:
                s = str(stg).zfill(2)
                # Stage 01: leave top/bottom blank so user can revise
                if s == "01":
                    top_out = ""
                    bot_out = ""
                else:
                    top_out = "" if top is None else top
                    bot_out = "" if bot is None else bot
                w.writerow([well, s, "" if plug is None else plug, top_out, bot_out])

        self.status_label.configure(text=f"✅ Exported: {out_path}")


    def export_current_well_csv(self):
        if self.parsed_well_names:
            idx = min(self.current_well_index, len(self.parsed_well_names) - 1)
            self.export_csv_for_well(self.parsed_well_names[idx])
        else:
            self.status_label.configure(text="⚠️ No well selected/parsed yet")

    def export_all_wells_csv(self):
        if not self.perf_data:
            self.status_label.configure(text="⚠️ Nothing to export")
            return
        for well in self.perf_data.keys():
            self.export_csv_for_well(well)
            
    def _get_parser_knobs(self):
        # Min depth
        md_txt = (self.knob_min_depth_entry.get().strip() if hasattr(self, "knob_min_depth_entry") else "")
        try:
            min_depth = float(md_txt) if md_txt else None
        except:
            min_depth = None

        # Window below plug
        try:
            window = float(self.knob_window_entry.get().strip())
        except:
            window = 1200.0

        prefer = bool(self.knob_prefer_explicit_var.get()) if hasattr(self, "knob_prefer_explicit_var") else True
        return {
            "min_depth": min_depth,
            "window_below_plug": window,
            "prefer_explicit_top_bottom": prefer,
        }
        
    def _append_ob_comparison(self, ob_perf: dict):
        # print OB rows and flag mismatches relative to local (>5 ft)
        tol = 5.0
        for well, stages in ob_perf.items():
            self.result_box.insert("end", f"\n=== {well}: Parsed {len(stages)} stages (OB) ===\n")
            # normalize dict for easy lookup
            local_map = {}
            if well in self.perf_data:
                for stg, plug, top, bot in self.perf_data[well]:
                    local_map[str(stg).zfill(2)] = (plug, top, bot)

            # sort OB stages
            try:
                stages_sorted = sorted(stages, key=lambda r: int(str(r[0]).zfill(2)))
            except Exception:
                stages_sorted = stages

            for stg, plug, top, bot in stages_sorted:
                s = str(stg).zfill(2)
                # Stage 01 display rule
                t_disp = "NULL" if s == "01" else ("NULL" if top is None else top)
                b_disp = "NULL" if s == "01" else ("NULL" if bot is None else bot)

                # Diff
                flag = ""
                if s in local_map:
                    l_plug, l_top, l_bot = local_map[s]
                    def delta(a, b):
                        if a is None or b is None: return None
                        try: return abs(float(a) - float(b))
                        except: return None
                    d_plug = delta(plug, l_plug)
                    d_top  = delta(top,  l_top)
                    d_bot  = delta(bot,  l_bot)
                    if (d_plug and d_plug > tol) or (d_top and d_top > tol) or (d_bot and d_bot > tol):
                        flag = "  ⚠️ diff vs Local"

                self.result_box.insert("end", f"Stage {s}: plug={plug}, top={t_disp}, bot={b_disp}{flag}\n")
                
    def toggle_advanced_panel(self):
        if not self.adv_shown:
            self.adv_frame.grid(row=5, column=0, columnspan=4, padx=10, pady=10, sticky="we")
            self.adv_toggle_btn.configure(text="Hide Advanced Parser Settings")
            self.adv_shown = True
        else:
            self.adv_frame.grid_forget()
            self.adv_toggle_btn.configure(text="Show Advanced Parser Settings")
            self.adv_shown = False






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
        # Keep a handle to the tab so later methods can reference it directly
        self.perf_tab = self.tabs.add("Perf Converter")
        tab = self.perf_tab

        # Instructions
        instr = (
            "Upload a Completion Procedure PDF. The tool will extract:\n\n"
            " - Top/Bottom Perf Depths\n"
            " - Plug Depths\n\n"
            "Enter only Page Ranges and # Clusters/Stage for each well below,\n"
            "then click “Proceed to Next Well’s Perf Data”."
        )
        ctk.CTkLabel(tab, text=instr, justify="left").grid(
            row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w"
        )

        # State used by Perf Converter
        self.perf_well_data = []       # [(name, entry_start, entry_end, entry_clust), ...]
        self.perf_data = {}            # {well: [(stage, plug, top, bottom), ...]}
        self.parsed_well_names = []    # order-preserving list of wells with results
        self.current_well_index = 0
        self.next_well_btn = None

        # Per-well inputs (start/end pages, clusters)
        self.perf_rows_frame = ctk.CTkScrollableFrame(tab, width=1200, height=200)
        self.perf_rows_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="we")
        self._build_perf_converter_rows()

        # Actions
        ctk.CTkButton(tab, text="Upload Completion Procedure PDF", command=self.upload_pdf).grid(
            row=2, column=0, padx=10, pady=10, sticky="w"
        )
        ctk.CTkButton(tab, text="Load Config", command=self.load_config).grid(
            row=2, column=2, padx=10, pady=10, sticky="w"
        )

        # Results area container (two-column)
        preview_frame = ctk.CTkFrame(tab)
        preview_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="we")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            preview_frame, text="Results Preview (Local → OB + Diff):",
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, sticky="w", padx=5)
        

        # Left: results box
        ob_scroll = ctk.CTkScrollableFrame(preview_frame, width=450, height=200)
        ob_scroll.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="nsew")
        self.result_box = ctk.CTkTextbox(ob_scroll, wrap="none", width=430, height=180)
        self.result_box.pack(padx=5, pady=5, fill="both", expand=True)

        # ── Right control panel (NEW) ────────────────────────────────────────────
        right_panel = ctk.CTkFrame(preview_frame)
        right_panel.grid(row=1, column=1, padx=5, pady=(0,10), sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)

        # OB Mode segmented control
        ctk.CTkLabel(right_panel, text="OB Mode").grid(row=0, column=0, sticky="w", padx=6, pady=(8,2))
        self.ob_mode_var = ctk.StringVar(value="Auto")
        ctk.CTkSegmentedButton(
            right_panel,
            values=["Never", "Auto", "Always"],
            variable=self.ob_mode_var
        ).grid(row=1, column=0, sticky="w", padx=6)

        # Raw text popup
        ctk.CTkButton(
            right_panel, text="View Raw Text…", command=self.view_raw_text_popup
        ).grid(row=2, column=0, sticky="w", padx=6, pady=(10,2))

        # Regions status placeholder (for later when we add the annotator)
        self.regions_status_label = ctk.CTkLabel(right_panel, text="Regions: none")
        self.regions_status_label.grid(row=3, column=0, sticky="w", padx=6, pady=(8,2))

        # Export buttons
        export_frame = ctk.CTkFrame(preview_frame)
        export_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=(10, 0), sticky="w")
        ctk.CTkButton(export_frame, text="Export CSV (current well)", command=self.export_current_well_csv)\
            .pack(side="left", padx=(0, 8))
        ctk.CTkButton(export_frame, text="Export CSV (all wells)", command=self.export_all_wells_csv)\
            .pack(side="left")

        # Advanced knobs (optional)
        self.adv_shown = False
        self.adv_toggle_btn = ctk.CTkButton(
            tab, text="Show Advanced Parser Settings",
            command=self.toggle_advanced_panel
        )
        self.adv_toggle_btn.grid(row=4, column=0, padx=10, pady=(10, 0), sticky="w")

        self.adv_frame = ctk.CTkFrame(tab)

        row = ctk.CTkFrame(self.adv_frame); row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text="Min depth (ft, blank = auto)").pack(side="left")
        self.knob_min_depth_entry = ctk.CTkEntry(row, width=120, placeholder_text="")
        self.knob_min_depth_entry.pack(side="left", padx=6)

        row2 = ctk.CTkFrame(self.adv_frame); row2.pack(fill="x", pady=4)
        ctk.CTkLabel(row2, text="Cluster window below plug (ft)").pack(side="left")
        self.knob_window_entry = ctk.CTkEntry(row2, width=120)
        self.knob_window_entry.insert(0, "1200")
        self.knob_window_entry.pack(side="left", padx=6)

        row3 = ctk.CTkFrame(self.adv_frame); row3.pack(fill="x", pady=4)
        self.knob_prefer_explicit_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            row3,
            text="Prefer explicit Top/Bottom columns if present",
            variable=self.knob_prefer_explicit_var
        ).pack(side="left")


        # Render any existing results
        self._render_perf_results()
        
    def _format_stage_row(self, stage, plug, top, bot):
        s = str(stage).zfill(2)
        def fmt_num(x):
            return "NULL" if x is None else f"{float(x):,.1f}"
        top_disp = None if s == "01" else top
        bot_disp = None if s == "01" else bot
        return f"Stage {s:>2} | plug {fmt_num(plug):>8} | top {fmt_num(top_disp):>8} | bot {fmt_num(bot_disp):>8}\n"
        
    def upload_pdf(self):
        from tkinter import filedialog
        import json
        from fracmaster_toolbox.ob_agent import call_ob_agent
        from fracmaster_toolbox.utils import perf_parser

        if not self.config_data.get("wells"):
            self.result_box.delete("1.0", "end")
            self.result_box.insert("end", "⚠️ Load a job_config.json first.")
            return

        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return
        self.last_pdf_path = file_path  # for future annotator

        # reset state
        self.perf_data = {}
        self.parsed_well_names = []
        self.current_well_index = 0

        # build well_map with guarded page ranges (your version already does this safely)
        well_map: dict[str, dict[str, int]] = {}
        for name, entry_start, entry_end, entry_clust in self.perf_well_data:
            sp_txt = (entry_start.get() or "").strip()
            ep_txt = (entry_end.get() or "").strip()
            cl_txt = (entry_clust.get() or "").strip()
            start_page = end_page = clusters = 0
            try:
                clusters = int(cl_txt) if cl_txt else 0
            except:  # leave 0
                pass
            try:
                if sp_txt: start_page = max(1, int(sp_txt))
                if ep_txt: end_page = max(1, int(ep_txt))
            except:
                start_page = end_page = 0
            if start_page and not end_page:
                end_page = start_page
            if start_page and end_page and end_page < start_page:
                end_page = start_page
            well_map[name] = {"start_page": start_page, "end_page": end_page, "n_clusters": clusters}

        # RAW text → cache for popup
        try:
            pdf_text_by_well = perf_parser.extract_text_by_well(file_path, well_map)
            self.last_pdf_text_by_well = pdf_text_by_well
        except Exception as e:
            self.result_box.delete("1.0", "end")
            self.result_box.insert("end", f"⚠️ Failed to read PDF: {e}")
            return

        # Local parser (show first)
        knobs = self._get_parser_knobs()  # assumes you already have this helper
        try:
            local_structured = perf_parser.parse_pdf_structured(
                file_path,
                well_map,
                min_depth=knobs["min_depth"],
                window_below_plug=knobs["window_below_plug"],
                prefer_explicit_top_bottom=knobs["prefer_explicit_top_bottom"],
                split_digit_stage=True,
                stage01_null=False,  # we null Stage 01 only in the GUI formatter
            )
        except Exception as e:
            local_structured = {}
            self.result_box.delete("1.0", "end")
            self.result_box.insert("end", f"🧰 Local Parser Results:\n⚠️ Parser error: {e}\n")

        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", "🧰 Local Parser Results:\n")
        if local_structured:
            self.perf_data = local_structured
            self.parsed_well_names = [w for w in well_map if w in self.perf_data]
            self._render_perf_results()
        else:
            self.result_box.insert("end", "⚠️ No rows parsed locally.\n")

        # OB validator (we’ll add the Auto/Never/Always gate next)
        payload = {
            "pdf_text": pdf_text_by_well,
            "job_config": self.config_data,
            "well_map": well_map,
            "instructions": "Extract plug, top, and bottom perf for each stage per well.",
        }
        try:
            ob = call_ob_agent("perf_parser", payload)
        except Exception as e:
            ob = {"error": f"OB call failed: {e}"}

        if isinstance(ob, str):
            try:
                ob = json.loads(ob)
            except json.JSONDecodeError:
                ob = {"error": "Invalid JSON from OB"}

        self.result_box.insert("end", "\n🤖 OB Agent Results:\n")
        if "error" in ob:
            self.result_box.insert("end", f"⚠️ {ob['error']}\n")
            return

        ob_perf = ob.get("perf_data", {})
        if not ob_perf:
            self.result_box.insert("end", "⚠️ No perf data returned by OB.\n")
            return

        # If you already have _append_ob_comparison, keep using it:
        self._append_ob_comparison(ob_perf)

        if self.parsed_well_names:
            self._add_next_well_button()



    def _render_perf_results(self):
        for well, stages in self.perf_data.items():
            self.result_box.insert("end", f"\n=== {well}: Parsed {len(stages)} stages (Local) ===\n")
            try:
                stages_sorted = sorted(stages, key=lambda r: int(str(r[0]).zfill(2)))
            except Exception:
                stages_sorted = stages
            for stg, plug, top, bot in stages_sorted:
                self.result_box.insert("end", self._format_stage_row(stg, plug, top, bot))

        if self.perf_data:
            self._add_next_well_button()


    def _build_perf_converter_rows(self):
        for widget in self.perf_rows_frame.winfo_children():
            widget.destroy()

        self.perf_well_data.clear()

        headers = ["Start", "End", "Clusters"]
        for col, text in enumerate(headers, start=1):
            ctk.CTkLabel(self.perf_rows_frame, text=text).grid(row=0, column=col, padx=5)

        for i, well in enumerate(self.config_data.get("wells", []), start=1):
            name = well["name"]
            ctk.CTkLabel(self.perf_rows_frame, text=f"{name}:").grid(row=i, column=0, padx=5, pady=2)
            entry_start = ctk.CTkEntry(self.perf_rows_frame, width=40)
            entry_end = ctk.CTkEntry(self.perf_rows_frame, width=40)
            entry_clust = ctk.CTkEntry(self.perf_rows_frame, width=40)
            entry_start.grid(row=i, column=1)
            entry_end.grid(row=i, column=2)
            entry_clust.grid(row=i, column=3)
            self.perf_well_data.append((name, entry_start, entry_end, entry_clust))

    def _display_well_data(self, well_name):
        if well_name not in self.perf_data:
            return
        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", f"=== {well_name} Results (Local) ===\n")
        stages = self.perf_data[well_name]
        try:
            stages = sorted(stages, key=lambda r: int(str(r[0]).zfill(2)))
        except Exception:
            pass
        for stg, plug, top, bot in stages:
            self.result_box.insert("end", self._format_stage_row(stg, plug, top, bot))
            
    def view_raw_text_popup(self):
        if not getattr(self, "last_pdf_text_by_well", None):
            # nothing cached yet
            top = ctk.CTkToplevel(self)
            top.title("Raw Text")
            ctk.CTkLabel(top, text="No raw text cached. Upload a PDF first.").pack(padx=16, pady=16)
            return

        top = ctk.CTkToplevel(self)
        top.title("Raw Extracted PDF Text")
        top.geometry("900x600")

        # Well picker
        wells = list(self.last_pdf_text_by_well.keys())
        sel = ctk.StringVar(value=wells[0] if wells else "")
        bar = ctk.CTkFrame(top); bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(bar, text="Well:").pack(side="left", padx=(4,6))
        picker = ctk.CTkOptionMenu(bar, values=wells, variable=sel)
        picker.pack(side="left")

        # Text box
        scroll = ctk.CTkScrollableFrame(top, width=840, height=480)
        scroll.pack(fill="both", expand=True, padx=8, pady=(0,8))
        tb = ctk.CTkTextbox(scroll, wrap="none")
        tb.pack(fill="both", expand=True, padx=6, pady=6)

        def refresh_text(*_):
            tb.delete("1.0", "end")
            well = sel.get()
            tb.insert("end", f"==== {well} PDF Text ====\n{self.last_pdf_text_by_well.get(well, '')}\n")

        sel.trace_add("write", lambda *_: refresh_text())
        refresh_text()




    def _add_next_well_button(self):
        if self.next_well_btn:
            self.next_well_btn.destroy()

        self.next_well_btn = ctk.CTkButton(
            self.perf_tab,
            text="Proceed to Next Well",
            command=self.show_next_well
        )
        # was row=4 — move it below the Advanced panel
        self.next_well_btn.grid(row=6, column=0, columnspan=4, padx=10, pady=10, sticky="we")


    def show_next_well(self):
        self.current_well_index += 1
        if self.current_well_index >= len(self.parsed_well_names):
            if self.next_well_btn:
                self.next_well_btn.configure(state="disabled")
            return

        next_well = self.parsed_well_names[self.current_well_index]
        self._display_well_data(next_well)




def main():
    app = FracMasterApp()
    app.mainloop()

if __name__ == "__main__":
    main()