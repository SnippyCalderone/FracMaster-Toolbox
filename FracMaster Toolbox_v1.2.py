import customtkinter as ctk
import os
import shutil
import re
from tkinter import filedialog
import subprocess

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FracMasterApp(ctk.CTk):
    def toggle_file_type_inputs(self, choice):
        if choice == "Other File":
            self.other_file_name_entry.grid()
        else:
            self.other_file_name_entry.grid_remove()

    def select_job_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.populate_well_checkboxes(folder)

    def select_master_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.master_file_entry.delete(0, "end")
            self.master_file_entry.insert(0, filepath)
            self.master_file_path = filepath

    def populate_well_checkboxes(self, job_folder):
        for widget in self.well_check_frame.winfo_children():
            widget.destroy()
        self.stage_wells_data = {}

        for well in sorted(os.listdir(job_folder)):
            well_path = os.path.join(job_folder, well)
            if os.path.isdir(well_path):
                row = ctk.CTkFrame(self.well_check_frame)
                row.pack(fill="x", pady=2)

                check = ctk.CTkCheckBox(row, text=well)
                check.pack(side="left", padx=5)

                start_stage = ctk.CTkEntry(row, width=80, placeholder_text="Start")
                start_stage.pack(side="left", padx=2)

                to_end = ctk.CTkCheckBox(row, text="To End")
                to_end.pack(side="left", padx=2)
                to_end.configure(command=lambda w=well: self.set_end_stage_to_max(w))

                end_stage = ctk.CTkEntry(row, width=80, placeholder_text="End")
                end_stage.pack(side="left", padx=2)

                self.stage_wells_data[well] = {
                    "check": check,
                    "start": start_stage,
                    "end": end_stage,
                    "to_end": to_end,
                    "path": well_path
                }

    def get_max_stage(self, well_path):
        stage_folders = [name for name in os.listdir(well_path) if re.match(r"Stage \d{2}$", name)]
        return max([int(name.split()[1]) for name in stage_folders], default=0)

    def set_end_stage_to_max(self, well):
        max_stage = self.get_max_stage(self.stage_wells_data[well]["path"])
        self.stage_wells_data[well]["end"].delete(0, "end")
        self.stage_wells_data[well]["end"].insert(0, str(max_stage))
        self.stage_wells_data[well]["start"].delete(0, "end")
        self.stage_wells_data[well]["start"].insert(0, "01")
        self.stage_wells_data[well]["to_end"].configure(text=f"To Stage {max_stage}")

    def copy_file_to_stages(self):
        choice = self.file_type_var.get()
        file_to_copy = self.master_file_path
        custom_name = self.other_file_name_entry.get().strip()
        customer = self.customer_name_entry.get().strip()
        pad = self.pad_name_entry.get().strip()
        preview = []

        for well, data in self.stage_wells_data.items():
            if data["check"].get():
                start = data["start"].get()
                end = data["end"].get()

                try:
                    start = int(start)
                    end = int(end)
                except:
                    self.copy_status.configure(text=f"⚠️ Invalid stage range for {well}")
                    return

                for stage_num in range(start, end + 1):
                    stage_folder = os.path.join(data["path"], f"Stage {stage_num:02}")
                    os.makedirs(stage_folder, exist_ok=True)

                    ext = os.path.splitext(file_to_copy)[1]

                    if choice == "Frac Loader":
                        new_name = f"{well} {pad} Frac Loader Stage {stage_num:02}{ext}"
                    elif choice == "Primary Stage Files":
                        new_name = f"NE07_{customer}_{pad}_{well}_Stage Perf_Stage {stage_num:02}{ext}"
                    elif choice == "Other File" and custom_name:
                        new_name = f"NE07_{customer}_{pad}_{well}_{custom_name}_Stage {stage_num:02}{ext}"
                    else:
                        continue

                    dest_path = os.path.join(stage_folder, new_name)
                    shutil.copy(file_to_copy, dest_path)
                    preview.append(dest_path)

        self.preview_output.configure(state="normal")
        self.preview_output.delete("0.0", "end")
        self.preview_output.insert("0.0", "\n".join(preview))
        self.preview_output.configure(state="disabled")
        self.copy_status.configure(text="✅ Files copied successfully.")
    def __init__(self):
        super().__init__()
        self.title("FracMaster Toolbox")
        self.geometry("1300x800")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(expand=True, fill="both")

        self.create_job_setup_tab()
        self.create_stage_dropper_tab()

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

        generate_fields_button = ctk.CTkButton(tab, text="Generate Well Fields", command=self.generate_well_name_fields)
        generate_fields_button.grid(row=4, column=1, padx=10, pady=5)

        self.optional_files_frame = ctk.CTkFrame(tab)
        self.optional_files_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="nw")

        self.frac_loader_checkbox = ctk.CTkCheckBox(self.optional_files_frame, text="Include Frac Loader", command=self.toggle_frac_loader_picker)
        self.frac_loader_checkbox.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        self.redacted_checkbox = ctk.CTkCheckBox(self.optional_files_frame, text="Include Redacted FT")
        self.redacted_checkbox.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        self.witsml_checkbox = ctk.CTkCheckBox(self.optional_files_frame, text="Include WITSML")
        self.witsml_checkbox.grid(row=2, column=0, sticky="w", padx=5, pady=2)

        self.frac_loader_picker_frame = ctk.CTkFrame(tab)
        self.frac_loader_picker_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.frac_loader_picker_frame.grid_remove()

        self.file_paths = {}
        self.create_file_picker(self.frac_loader_picker_frame, "Master Frac Loader")

        self.well_name_frame = ctk.CTkFrame(tab)
        self.well_name_frame.grid(row=7, column=0, columnspan=2, padx=10, pady=10, sticky="nw")

        self.status_label = ctk.CTkLabel(tab, text="")
        self.status_label.grid(row=100, column=0, columnspan=2, pady=10)

        self.well_entries = []
        self.generate_button = ctk.CTkButton(tab, text="Generate Job Folder Structure", command=self.generate_job_structure)
        self.generate_button.grid(row=99, column=0, columnspan=2, pady=30)

    def toggle_frac_loader_picker(self):
        if self.frac_loader_checkbox.get():
            self.frac_loader_picker_frame.grid()
        else:
            self.frac_loader_picker_frame.grid_remove()

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
        use_frac_loader = self.frac_loader_checkbox.get()
        include_redacted = self.redacted_checkbox.get()
        include_witsml = self.witsml_checkbox.get()
        master_loader = self.file_paths["Master Frac Loader"].get() if use_frac_loader else None

        outer_folder_name = f"{customer} {pad}"
        full_path = os.path.join(base_path, outer_folder_name)
        os.makedirs(full_path, exist_ok=True)

        if use_frac_loader and os.path.exists(master_loader):
            outer_loader_name = f"{customer} {pad} Master Frac Loader.xlsm"
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

                if use_frac_loader and os.path.exists(master_loader):
                    loader_name = f"{well} {pad} Frac Loader {stage_str}.xlsm"
                    shutil.copy(master_loader, os.path.join(stage_path, loader_name))

                open(os.path.join(stage_path, f"{fleet}_{customer}_{pad}_{well}_CSV_{stage_str}.csv"), 'a').close()
                open(os.path.join(stage_path, f"{fleet}_{customer}_{pad}_{well}_Post Job Report_{stage_str}.pdf"), 'a').close()
                open(os.path.join(stage_path, f"{fleet}_{customer}_{pad}_{well}_SFT_{stage_str}.pdf"), 'a').close()
                open(os.path.join(stage_path, "PJR.csv"), 'a').close()
                open(os.path.join(stage_path, "PJR.rtf"), 'a').close()

                if include_redacted:
                    open(os.path.join(stage_path, f"{fleet}_{customer}_{pad}_{well}_Redacted FT_{stage_str}.pdf"), 'a').close()
                if include_witsml:
                    open(os.path.join(stage_path, f"{fleet}_{customer}_{pad}_{well}_Job File_{stage_str}.xml"), 'a').close()

        try:
            subprocess.run(["explorer", os.path.realpath(full_path)])
        except Exception as e:
            print("Explorer open error:", e)

        self.status_label.configure(text="✅ Successful File Folder Generation!")

    def create_stage_dropper_tab(self):
        tab = self.tabs.add("File Injector")

        self.master_file_path = ""
        self.stage_wells_data = {}

        self.file_type_var = ctk.StringVar(value="")
        self.file_type_dropdown = ctk.CTkOptionMenu(
            tab,
            values=["Frac Loader", "Primary Stage Files", "Other File"],
            variable=self.file_type_var,
            command=self.toggle_file_type_inputs
        )
        self.file_type_dropdown.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.file_type_dropdown.set("")

        self.customer_name_entry = ctk.CTkEntry(tab, width=250, placeholder_text="Enter Customer Name")
        self.customer_name_entry.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.pad_name_entry = ctk.CTkEntry(tab, width=250, placeholder_text="Enter Pad Name")
        self.pad_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.other_file_name_entry = ctk.CTkEntry(tab, width=250, placeholder_text="Enter File Type (e.g. Stage Sheet)")
        self.other_file_name_entry.grid(row=0, column=1, padx=10, pady=10)
        self.other_file_name_entry.grid_remove()

        self.folder_entry = ctk.CTkEntry(tab, width=400, placeholder_text="Select Job Folder")
        self.folder_entry.grid(row=2, column=0, padx=10, pady=10)
        browse_btn = ctk.CTkButton(tab, text="Browse", command=self.select_job_folder)
        browse_btn.grid(row=2, column=1, padx=10, pady=10)

        self.master_file_entry = ctk.CTkEntry(tab, width=400, placeholder_text="Select File to Copy")
        self.master_file_entry.grid(row=3, column=0, padx=10, pady=10)
        file_btn = ctk.CTkButton(tab, text="Browse File", command=self.select_master_file)
        file_btn.grid(row=3, column=1, padx=10, pady=10)

        self.well_check_frame = ctk.CTkScrollableFrame(tab, width=1200, height=200)
        self.well_check_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.copy_button = ctk.CTkButton(tab, text="Copy File to Stage Ranges", command=self.copy_file_to_stages)
        self.copy_button.grid(row=5, column=0, columnspan=2, pady=5)

        self.copy_status = ctk.CTkLabel(tab, text="")
        self.copy_status.grid(row=6, column=0, columnspan=2, pady=5)

        self.preview_output = ctk.CTkTextbox(tab, width=1200, height=200, wrap="none")
        self.preview_output.configure(font=("Courier", 12))
        self.preview_output.grid(row=7, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="nsew")
        self.preview_output.insert("0.0", "📂 File preview will appear here...")
        self.preview_output.configure(state="disabled")

    def browse_destination_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination_entry.delete(0, "end")
            self.destination_entry.insert(0, folder)

if __name__ == "__main__":
    app = FracMasterApp()
    app.mainloop()
