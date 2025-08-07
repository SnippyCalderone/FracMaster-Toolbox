import pdfplumber
import logging

# Configure logging (standard library, no need to add to requirements.txt)
logging.basicConfig(level=logging.INFO, format='[PerfParser] %(message)s')

def parse_pdf(pdf_path, well_map):
    """
    Extract raw text from PDF pages for each well.
    Returns a dictionary where each key is a well name and value is the combined text from its page range.
    This function replaces the old behavior of returning structured perf_data, as OB will now handle parsing.
    """
    return _extract_text(pdf_path, well_map)

def extract_text_by_well(pdf_path, well_map):
    """
    Wrapper for extracting raw text for OB or other consumers.
    This aligns with OB integration and no longer parses stage/plug data locally.
    """
    return _extract_text(pdf_path, well_map)

def _extract_text(pdf_path, well_map):
    text_data = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for well, info in well_map.items():
                start, end = info.get("start_page", 0), info.get("end_page", 0)
                extracted_text = []
                for page_num in range(start - 1, end):
                    if 0 <= page_num < len(pdf.pages):
                        page = pdf.pages[page_num]
                        text = page.extract_text() or "[No text found]"
                        if text == "[No text found]":
                            logging.warning(f"No text extracted from page {page_num+1} for well {well}")
                        extracted_text.append(text)
                    else:
                        logging.warning(f"Page {page_num+1} out of range for well {well}")
                text_data[well] = "\n".join(extracted_text)
    except Exception as e:
        logging.error(f"Failed to read PDF: {e}")
        return {well: "" for well in well_map}
    return text_data