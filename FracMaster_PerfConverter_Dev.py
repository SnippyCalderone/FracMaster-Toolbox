import customtkinter as ctk
import os
import csv
import pdfplumber
from tkinter import filedialog
import re
from collections import defaultdict
import openpyxl
from openpyxl import Workbook

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FracMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FracMaster Toolbox - Dev")
        self.geometry("1300x800")

        self.customer_name = ""
        self.pad_name = ""
        self.stage1_expected_guns = 0

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(expand=True, fill="both")

        self.create_job_setup_tab()
        self.create_file_dropper_tab()
        self.create_perf_converter_tab()

    def create_job_setup_tab(self):
        tab = self.tabs.add("Job Setup")

        customer_label = ctk.CTkLabel(tab, text="Customer Name")
        customer_label.pack(pady=(10, 0))
        self.customer_entry = ctk.CTkEntry(tab)
        self.customer_entry.pack(pady=(0, 10))

        pad_label = ctk.CTkLabel(tab, text="Pad Name")
        pad_label.pack(pady=(10, 0))
        self.pad_entry = ctk.CTkEntry(tab)
        self.pad_entry.pack(pady=(0, 10))

        stage1_label = ctk.CTkLabel(tab, text="Expected Guns in Stage 1")
        stage1_label.pack(pady=(10, 0))
        self.stage1_entry = ctk.CTkEntry(tab)
        self.stage1_entry.pack(pady=(0, 10))

        placeholder = ctk.CTkLabel(tab, text="[Job Setup Tool Placeholder]\n(To be reintegrated later)", font=("Arial", 14))
        placeholder.pack(pady=20)

    def create_file_dropper_tab(self):
        tab = self.tabs.add("File Dropper")
        placeholder = ctk.CTkLabel(tab, text="[File Dropper Tool Placeholder]\n(To be reintegrated later)", font=("Arial", 16))
        placeholder.pack(pady=20)

    def create_perf_converter_tab(self):
        self.perf_well_data = []
        tab = self.tabs.add("Perf Converter")

        self.instructions = ctk.CTkLabel(tab, text="Upload a Completion Procedure PDF. The tool will extract:\n\n- Top/Bottom Perf Depths\n- Plug Depths\n- KOP and Heel Depth\n- TVD per stage (if available)\n\nYou may upload a directional survey file in the future.", justify="left")
        self.instructions.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        self.num_wells_entry = ctk.CTkEntry(tab, placeholder_text="How many wells on this pad?")
        self.num_wells_entry.place(x=10, y=10)

        self.load_wells_button = ctk.CTkButton(tab, text="Submit Well Count", command=self.load_well_entries)
        self.load_wells_button.place(x=10, y=50)

        self.well_entry_frame = ctk.CTkScrollableFrame(tab, height=200, width=600)
        self.well_entry_frame.place(x=10, y=100)

        self.upload_button = ctk.CTkButton(tab, text="Upload Completion Procedure PDF", command=self.upload_pdf)
        self.upload_button.place(x=10, y=310)

        scrollable_frame = ctk.CTkScrollableFrame(tab, height=3000, width=925)
        scrollable_frame.place(x=10, y=350)

        self.result_box = ctk.CTkTextbox(scrollable_frame, wrap="none", height=475, width=925)
        self.result_box.pack(pady=10, fill="y", expand=True, anchor="se")

    def load_well_entries(self):
        for child in self.well_entry_frame.winfo_children():
            child.destroy()
        try:
            count = int(self.num_wells_entry.get())
            self.perf_well_data = []
            for i in range(count):
                name_entry = ctk.CTkEntry(self.well_entry_frame, placeholder_text=f"Well {i+1} Name")
                page_entry = ctk.CTkEntry(self.well_entry_frame, placeholder_text="Pg. # e.g. 22-25")
                stage_entry = ctk.CTkEntry(self.well_entry_frame, placeholder_text="# Stages")
                cluster_entry = ctk.CTkEntry(self.well_entry_frame, placeholder_text="# Clusters/Stage")

                name_entry.grid(row=0, column=i, pady=(10, 10), padx=2, sticky="n")
                page_entry.grid(row=1, column=i, pady=(0, 10), padx=2, sticky="n")
                stage_entry.grid(row=2, column=i, pady=(0, 10), padx=2, sticky="n")
                cluster_entry.grid(row=3, column=i, pady=(0, 10), padx=2, sticky="n")

                self.perf_well_data.append((name_entry, page_entry, stage_entry, cluster_entry))
        except ValueError:
            pass

    def upload_pdf(self):
        self.customer_name = self.customer_entry.get().strip() or "CustomerName"
        self.pad_name = self.pad_entry.get().strip() or "PadName"
        try:
            self.stage1_expected_guns = int(self.stage1_entry.get().strip())
        except ValueError:
            self.stage1_expected_guns = 0

        pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not pdf_path:
            return

        try:
            well_page_map = {}
            for well_entry, pages_entry, _, _ in self.perf_well_data:
                name = well_entry.get().strip()
                pages_raw = pages_entry.get().replace(" ", "")
                page_set = set()
                for r in pages_raw.split(';'):
                    if '-' in r:
                        start, end = map(int, r.split('-'))
                        page_set.update(range(start, end + 1))
                    elif r.isdigit():
                        page_set.add(int(r))
                if name:
                    well_page_map[name] = page_set

            self.result_box.delete("1.0", "end")
            perf_summary = defaultdict(list)

            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_num = i + 1
                    for well_name, pages in well_page_map.items():
                        if page_num in pages:
                            tables = page.extract_tables()
                            for table in tables:
                                data_rows = [row for row in table if sum(1 for cell in row if cell and cell.strip()) >= 10]

                                for row in data_rows:
                                    if len(row) >= 16:
                                        fallback_headers = ["Stage", "Plug Top"] + [f"Gun {i}" for i in range(1, 15)]
                                        zipped_row = dict(zip(fallback_headers, row[:16]))

                                        gun_depths = []
                                        for key in fallback_headers[2:]:
                                            raw = zipped_row.get(key, "")
                                            if raw:
                                                try:
                                                    val = float(raw.replace(",", "").strip())
                                                    gun_depths.append(val)
                                                except ValueError:
                                                    pass

                                        plug_depth = None
                                        plug_raw = zipped_row.get("Plug Top", "")
                                        if plug_raw:
                                            try:
                                                plug_depth = float(plug_raw.replace(",", "").strip())
                                            except ValueError:
                                                pass

                                        if gun_depths:
                                            stage = zipped_row.get("Stage", "?")
                                            if stage == "1" and len(gun_depths) < self.stage1_expected_guns:
                                                self.result_box.insert("end", f"[NOTICE] Stage 1 skipped (expected >{len(gun_depths)} guns)\n")
                                                continue
                                            top = min(gun_depths)
                                            bottom = max(gun_depths)
                                            perf_summary[well_name].append((stage, plug_depth, top, bottom))
                                            self.result_box.insert("end", f"Stage {stage} | Top: {top:.2f} | Bottom: {bottom:.2f} | Plug: {plug_depth if plug_depth is not None else 'N/A'}\n")

            self.result_box.insert("end", "\n==== PERF SUMMARY ====\n")
            for well, stages in perf_summary.items():
                self.result_box.insert("end", f"{well}:\n")
                for stage, plug, top, bot in stages:
                    self.result_box.insert("end", f"  Stage {stage}: Plug = {plug if plug is not None else 'N/A'}, Top = {top:.2f}, Bottom = {bot:.2f}\n")
                self.result_box.insert("end", "\n")

            xlsx_path = os.path.join(os.path.dirname(pdf_path), f"{self.customer_name}_{self.pad_name}_PerfConverter.xlsx")
            wb = Workbook()
            default_sheet = wb.active
            wb.remove(default_sheet)

            for well, stages in perf_summary.items():
                sheet = wb.create_sheet(title=well[:31])
                sheet.append(["Stage #", "Plug Depth (ft)", "Top Perf (ft)", "Bottom Perf (ft)"])
                for stage, plug, top, bot in stages:
                    sheet.append([stage, plug if plug is not None else "N/A", f"{top:.2f}", f"{bot:.2f}"])

            wb.save(xlsx_path)
            self.result_box.insert("end", f"Excel exported to: {xlsx_path}\n")

        except Exception as e:
            self.result_box.delete("1.0", "end")
            self.result_box.insert("1.0", f"❌ Failed to read PDF: {str(e)}")

if __name__ == "__main__":
    app = FracMasterApp()
    app.mainloop()
