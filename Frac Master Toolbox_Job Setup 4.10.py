import customtkinter as ctk
import os
import shutil
import subprocess
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FracMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FracMaster Toolbox")
        self.geometry("900x700")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(expand=True, fill="both")

        self.create_stage_dropper_tab()
        self.create_job_setup_tab()
        self.create_placeholder_tabs()

    def create_stage_dropper_tab(self):
        tab = self.tabs.add("Stage File Dropper")

    def create_job_setup_tab(self):
        tab = self.tabs.add("Job Setup")

        self.destination_entry = ctk.CTkEntry(tab, width=400, placeholder_text="Select Destination Folder for Job")
        self.destination_entry.grid(row=0, column=0, padx=10, pady=10)
        dest_button = ctk.CTkButton(tab, text="Browse Destination", command=self.browse_destination_folder)
        dest_button.grid(row=0, column=1, padx=10, pady=10)

        self.fleet_entry = ctk.CTkEntry(tab, width=150, placeholder_text="Fleet ID (e.g. NE07)")
        self.fleet_entry.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.customer_entry = ctk.CTkEntry(tab, width=300, placeholder_text="Customer Name")
        self.customer_entry.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.pad_entry = ctk.CTkEntry(tab, width=300, placeholder_text="Pad Name")
        self.pad_entry.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.num_wells_entry = ctk.CTkEntry(tab, width=100, placeholder_text="# of Wells")
        self.num_wells_entry.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.ohio_checkbox = ctk.CTkCheckBox(tab, text="Is this an Ohio Pad?")
        self.ohio_checkbox.grid(row=5, column=0, padx=10, pady=10, sticky="w")

        self.well_name_frame = ctk.CTkFrame(tab)
        self.well_name_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="nw")

        generate_fields_button = ctk.CTkButton(tab, text="Generate Well Fields", command=self.generate_well_name_fields)
        generate_fields_button.grid(row=4, column=1, padx=10, pady=5)

        self.status_label = ctk.CTkLabel(tab, text="")
        self.status_label.grid(row=100, column=0, columnspan=2, pady=10)

        self.well_entries = []
        self.file_paths = {}
        self.create_file_picker(tab, "Master Frac Loader", 7)

        self.generate_button = ctk.CTkButton(tab, text="Generate Job Folder Structure", command=self.generate_job_structure)
        self.generate_button.grid(row=99, column=0, columnspan=2, pady=30)

    def create_file_picker(self, parent, label, row):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")

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

    def generate_well_name_fields(self):
        for widget in self.well_name_frame.winfo_children():
            widget.destroy()
        self.well_entries.clear()

        try:
            num_wells = int(self.num_wells_entry.get())
            for i in range(num_wells):
                row = ctk.CTkFrame(self.well_name_frame)
                row.pack(fill="x", pady=2)

                well_name_entry = ctk.CTkEntry(row, width=200, placeholder_text=f"Well {i+1} Name")
                well_name_entry.pack(side="left", padx=5)

                stage_count_entry = ctk.CTkEntry(row, width=100, placeholder_text="# of Stages")
                stage_count_entry.pack(side="left", padx=5)

                self.well_entries.append((well_name_entry, stage_count_entry))
        except ValueError:
            pass

    def generate_job_structure(self):
        base_path = self.destination_entry.get()
        fleet = self.fleet_entry.get().strip()
        customer = self.customer_entry.get().strip()
        pad = self.pad_entry.get().strip()
        is_ohio = self.ohio_checkbox.get()
        master_loader = self.file_paths["Master Frac Loader"].get()

        outer_folder_name = f"{customer} {pad}"
        full_path = os.path.join(base_path, outer_folder_name)
        os.makedirs(full_path, exist_ok=True)

        # Copy Master Frac Loader into outermost folder with new name
        outer_loader_name = f"{customer} {pad} Master Frac Loader.xlsm"
        if os.path.exists(master_loader):
            shutil.copy(master_loader, os.path.join(full_path, outer_loader_name))

        for well_entry, stage_entry in self.well_entries:
            well = well_entry.get().strip()
            try:
                stages = int(stage_entry.get())
            except ValueError:
                continue

            well_path = os.path.join(full_path, f"{well}")
            os.makedirs(well_path, exist_ok=True)

            for stage in range(1, stages + 1):
                stage_str = f"Stage {stage:02}"
                stage_path = os.path.join(well_path, stage_str)
                os.makedirs(stage_path, exist_ok=True)

                # File names
                loader_name = f"{well} {pad} Frac Loader {stage_str}.xlsm"
                csv_name = f"{fleet}_{customer}_{pad}_{well}_CSV_{stage_str}.csv"
                pjr_name = f"{fleet}_{customer}_{pad}_{well}_Post Job Report_{stage_str}.pdf"
                sft_name = f"{fleet}_{customer}_{pad}_{well}_SFT_{stage_str}.pdf"
                redacted_name = f"{fleet}_{customer}_{pad}_{well}_Redacted FT_{stage_str}.pdf"

                # Copy frac loader to each stage
                if os.path.exists(master_loader):
                    shutil.copy(master_loader, os.path.join(stage_path, loader_name))

                # Create blank placeholder files
                open(os.path.join(stage_path, csv_name), 'a').close()
                open(os.path.join(stage_path, pjr_name), 'a').close()
                open(os.path.join(stage_path, sft_name), 'a').close()
                if is_ohio:
                    open(os.path.join(stage_path, redacted_name), 'a').close()

                open(os.path.join(stage_path, "PJR.csv"), 'a').close()
                open(os.path.join(stage_path, "PJR.rtf"), 'a').close()

        try:
            subprocess.run(["explorer", os.path.realpath(full_path)])
        except Exception as e:
            print("Explorer open error:", e)

        self.status_label.configure(text="✅ Successful File Folder Generation!")

    def browse_destination_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination_entry.delete(0, "end")
            self.destination_entry.insert(0, folder)

    def create_placeholder_tabs(self):
        self.tabs.add("Template Generator")
        self.tabs.add("Tracer Tool")
        self.tabs.add("Rename Utility")

    def copy_file_to_stages(self):
        pass

if __name__ == "__main__":
    app = FracMasterApp()
    app.mainloop()
