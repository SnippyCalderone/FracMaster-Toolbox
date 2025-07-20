import customtkinter as ctk
import os
import json
import openpyxl
import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class WITSMLInjectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FracMaster - WITSML Injector (Prototype)")
        self.geometry("1200x800")

        self.excel_path = ""
        self.witsml_path = ""
        self.job_folder = ""
        self.master_packet_path = ""
        self.config_folder = ""
        self.config = {}
        self.job_metadata = {}
        self.selected_well = ctk.StringVar()
        self.selected_stage = ctk.StringVar()

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(expand=True, fill="both")

        self.setup_file_tab()
        self.setup_manual_tab()
        self.setup_mapping_tab()
        self.setup_inject_tab()

        self.check_and_load_latest_config()

    def setup_file_tab(self):
        tab = self.tabs.add("1. Job Info")

        self.master_packet_entry = ctk.CTkEntry(tab, width=500, placeholder_text="Select Master Packet File")
        self.master_packet_entry.grid(row=0, column=0, padx=10, pady=10)
        master_btn = ctk.CTkButton(tab, text="Browse", command=self.browse_master_packet)
        master_btn.grid(row=0, column=1, padx=5, pady=10)

        self.job_folder_entry = ctk.CTkEntry(tab, width=500, placeholder_text="Select Job Folder")
        self.job_folder_entry.grid(row=1, column=0, padx=10, pady=10)
        job_btn = ctk.CTkButton(tab, text="Browse", command=self.browse_job_folder)
        job_btn.grid(row=1, column=1, padx=5, pady=10)

        self.save_config_btn = ctk.CTkButton(tab, text="Save Config", command=self.save_config)
        self.save_config_btn.grid(row=2, column=0, padx=5, pady=10)

        self.job_info_display = ctk.CTkTextbox(tab, height=300, width=1000)
        self.job_info_display.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def check_and_load_latest_config(self):
        self.config_folder = os.path.join(os.getcwd(), "witsml_configs")
        os.makedirs(self.config_folder, exist_ok=True)

        configs = [f for f in os.listdir(self.config_folder) if f.endswith(".json")]
        if configs:
            latest = max(configs, key=lambda f: os.path.getctime(os.path.join(self.config_folder, f)))
            config_path = os.path.join(self.config_folder, latest)
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.master_packet_path = self.config.get("master_packet", "")
            self.job_folder = self.config.get("job_folder", "")
            self.master_packet_entry.insert(0, self.master_packet_path)
            self.job_folder_entry.insert(0, self.job_folder)
            self.display_job_metadata()

    def browse_master_packet(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Macro-Enabled Workbook", "*.xlsm")])
        if path:
            self.master_packet_path = path
            self.master_packet_entry.delete(0, "end")
            self.master_packet_entry.insert(0, path)
            self.load_mapping_config()

    def browse_job_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.job_folder = folder
            self.job_folder_entry.delete(0, "end")
            self.job_folder_entry.insert(0, folder)
            self.display_job_metadata()

    def save_config(self):
        if not self.master_packet_path or not self.job_folder:
            messagebox.showwarning("Warning", "Please select both Master Packet and Job Folder first.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_data = {
            "master_packet": self.master_packet_path,
            "job_folder": self.job_folder
        }
        config_path = os.path.join(self.config_folder, f"witsml_config_{timestamp}.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=4)
        messagebox.showinfo("Config Saved", f"Configuration saved to: {config_path}")

    def load_mapping_config(self):
        config_path = os.path.join(os.path.dirname(self.master_packet_path), "witsml_mapping_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.config = json.load(f)

    def display_job_metadata(self):
        self.job_info_display.configure(state="normal")
        self.job_info_display.delete("0.0", "end")

        wells = []
        total_stages = 0
        for well in sorted(os.listdir(self.job_folder)):
            well_path = os.path.join(self.job_folder, well)
            if os.path.isdir(well_path):
                stages = [s for s in os.listdir(well_path) if s.startswith("Stage ")]
                wells.append(f"{well} ({len(stages)} stages)")
                total_stages += len(stages)

        output = f"Job Folder: {os.path.basename(self.job_folder)}\n"
        output += f"Master Packet: {os.path.basename(self.master_packet_path)}\n"
        output += f"\nWells Detected:\n" + "\n".join(wells)
        output += f"\n\nTotal Stages: {total_stages}"

        self.job_info_display.insert("0.0", output)
        self.job_info_display.configure(state="disabled")

    def setup_manual_tab(self):
        tab = self.tabs.add("2. Manual Entry")

        form_frame = ctk.CTkFrame(tab)
        form_frame.pack(pady=20)

        row = 0
        ctk.CTkLabel(form_frame, text="Select Well and Stage Number").grid(row=row, column=0, columnspan=2, pady=10)

        row += 1
        ctk.CTkLabel(form_frame, text="Well:").grid(row=row, column=0, sticky="e")
        self.manual_well_dropdown = ctk.CTkComboBox(form_frame, variable=self.selected_well, values=[])
        self.manual_well_dropdown.grid(row=row, column=1, padx=10, pady=5)

        row += 1
        ctk.CTkLabel(form_frame, text="Stage:").grid(row=row, column=0, sticky="e")
        self.manual_stage_dropdown = ctk.CTkComboBox(form_frame, variable=self.selected_stage, values=[])
        self.manual_stage_dropdown.grid(row=row, column=1, padx=10, pady=5)

        self.manual_inputs = {}
        fields = ["Pumps on NG Start", "Pumps on NG End", "Diesel Usage (gal)", "CNG Usage (mcf)"]
        for field in fields:
            row += 1
            ctk.CTkLabel(form_frame, text=field).grid(row=row, column=0, sticky="e")
            entry = ctk.CTkEntry(form_frame)
            entry.grid(row=row, column=1, padx=10, pady=5)
            self.manual_inputs[field] = entry

        row += 1
        inject_btn = ctk.CTkButton(form_frame, text="Inject Manual Data", command=self.inject_manual_data)
        inject_btn.grid(row=row, column=0, columnspan=2, pady=10)

    def inject_manual_data(self):
        try:
            well = self.selected_well.get()
            stage = self.selected_stage.get()
            stage_folder = os.path.join(self.job_folder, well, f"Stage {stage}")
            if not os.path.exists(stage_folder):
                raise FileNotFoundError(f"Stage folder does not exist: {stage_folder}")

            packet_file = next((f for f in os.listdir(stage_folder) if f.endswith(".xlsm") and "Master" not in f), None)
            if not packet_file:
                raise FileNotFoundError("No valid stage packet found in folder.")

            full_path = os.path.join(stage_folder, packet_file)
            wb = openpyxl.load_workbook(full_path)
            ws = wb["Engineer"]

            mapping = {
                "Pumps on NG Start": "D7",
                "Pumps on NG End": "D8",
                "Diesel Usage (gal)": "C31",
                "CNG Usage (mcf)": "E28"
            }

            for field, entry in self.manual_inputs.items():
                value = entry.get()
                if value:
                    cell = mapping.get(field)
                    if cell:
                        ws[cell] = value

            wb.save(full_path)
            messagebox.showinfo("Success", f"Manual data injected into: {packet_file}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to inject manual data: {e}")

    def setup_mapping_tab(self):
        tab = self.tabs.add("3. Field Mapping")
        label = ctk.CTkLabel(tab, text="Field Mapping Tab - Coming Soon")
        label.pack(pady=20)

    def setup_inject_tab(self):
        tab = self.tabs.add("4. Inject Data")
        label = ctk.CTkLabel(tab, text="Inject Tab - Coming Soon")
        label.pack(pady=20)

if __name__ == "__main__":
    app = WITSMLInjectorApp()
    app.mainloop()
