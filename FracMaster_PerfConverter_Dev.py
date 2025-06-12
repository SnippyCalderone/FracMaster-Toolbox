import customtkinter as ctk
import os
import pdfplumber  # Replaces fitz for table extraction
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FracMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FracMaster Toolbox - Dev")
        self.geometry("1300x800")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(expand=True, fill="both")

        self.create_job_setup_tab()
        self.create_file_dropper_tab()
        self.create_perf_converter_tab()

    def create_job_setup_tab(self):
        tab = self.tabs.add("Job Setup")
        placeholder = ctk.CTkLabel(tab, text="[Job Setup Tool Placeholder]\n(To be reintegrated later)", font=("Arial", 16))
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

            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_num = i + 1
                    for well_name, pages in well_page_map.items():
                        if page_num in pages:
                            tables = page.extract_tables()
                            for table in tables:
                                flat_headers = [cell.lower() for cell in table[0] if cell]
                                if any(keyword in ' '.join(flat_headers) for keyword in ["gun", "cluster", "stage", "plug"]):
                                    col_widths = [max(len(str(cell)) if cell else 0 for cell in col) for col in zip(*table)]
                                    self.result_box.insert("end", f"--- {well_name} | Table Found on Page {page_num} ---\n")
                                    for row in table:
                                        row_str = " | ".join((cell.strip() if cell else "").ljust(col_widths[i]) for i, cell in enumerate(row))
                                        self.result_box.insert("end", row_str + "\n")
                                    self.result_box.insert("end", f"{'-'*80}\n")

        except Exception as e:
            self.result_box.delete("1.0", "end")
            self.result_box.insert("1.0", f"❌ Failed to read PDF: {str(e)}")

if __name__ == "__main__":
    app = FracMasterApp()
    app.mainloop()
