import io
import pymupdf
from dataclasses import dataclass

@dataclass  
class ParsedPage:
    text: str
    page_num: int
    
class PdfParser:
    def parse(self, file_bytes: bytes) -> list[ParsedPage]:
        doc = pymupdf.open(stream=io.BytesIO(file_bytes), filetype="pdf")
        pages = []
        for i, page in enumerate(doc): # type: ignore
            text = page.get_text().strip()
            if text:
                pages.append(ParsedPage(text=text, page_num=i + 1))
        doc.close()
        return pages