import pdfplumber
import re
from typing import Dict, List, Tuple


StageData = List[Tuple[str, float, float, float]]


def parse_pdf(pdf_path: str, well_map: Dict[str, dict]) -> Dict[str, StageData]:
    """Parse completion procedure PDF into perf data."""
    perf_data: Dict[str, StageData] = {}

    with pdfplumber.open(pdf_path) as pdf:
        for well, cfg in well_map.items():
            pages = cfg.get("pages", [])
            ncl = cfg.get("n_clusters", 0)
            stages: StageData = []

            for pnum in pages:
                page = pdf.pages[pnum - 1]
                tables = page.extract_tables() or []
                for tbl in tables:
                    hdr = tbl[0] or []
                    low = [(h or "").lower() for h in hdr]
                    if "stage" in " ".join(low) and "plug" in " ".join(low):
                        try:
                            i_stage = next(i for i, h in enumerate(low) if "stage" in h)
                            i_plug = next(i for i, h in enumerate(low) if "plug" in h)
                        except StopIteration:
                            continue
                        cluster_is = [i for i, h in enumerate(low) if "cluster" in h][:ncl]
                        for row in tbl[1:]:
                            if not row or not row[i_stage]:
                                continue
                            stg_txt = str(row[i_stage]).strip()
                            if not stg_txt.isdigit():
                                continue
                            plug_txt = str(row[i_plug]).replace(",", "").strip()
                            if not re.fullmatch(r"\d+(?:\.\d+)?", plug_txt):
                                continue
                            cl_vals = []
                            for ci in cluster_is:
                                ctxt = str(row[ci]).replace(",", "").strip()
                                if re.fullmatch(r"\d+(?:\.\d+)?", ctxt):
                                    cl_vals.append(float(ctxt))
                            if len(cl_vals) < ncl:
                                continue
                            plug = float(plug_txt)
                            top = min(cl_vals)
                            bot = max(cl_vals)
                            stages.append((f"{int(stg_txt):02d}", plug, top, bot))
                        break
            if not stages:
                for pnum in pages:
                    text = pdf.pages[pnum - 1].extract_text() or ""
                    for L in text.splitlines():
                        m = re.search(r"Stage\s+(\d+)", L, re.IGNORECASE)
                        if not m:
                            continue
                        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", L.replace(",", ""))]
                        if len(nums) >= 2 + ncl:
                            stg = f"{int(m.group(1)):02d}"
                            plug = nums[1]
                            clv = nums[2:2+ncl] if ncl else nums[2:4]
                            if not clv:
                                continue
                            top = min(clv)
                            bot = max(clv)
                            if not any(s[0] == stg for s in stages):
                                stages.append((stg, plug, top, bot))
            stages.sort(key=lambda x: int(x[0]))
            perf_data[well] = stages
    return perf_data
