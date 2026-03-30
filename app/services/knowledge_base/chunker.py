from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

@dataclass
class TextChunk:
    content: str
    chunk_index: int
    metadata: dict  # carries page_num, source_type, section, etc.

class Chunker:
    """
    Splits text into smaller chunks for processing and embedding.
    """
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]
        )
        
    def chunk(self, text: str, base_metadata: dict = {}) -> list[TextChunk]:
        """
        Split text into chunks. base_metadata is merged into every chunk
        so downstream you know which page, section, or URL it came from.
        """
        if not text or not text.strip():
            return []

        raw_chunks = self._splitter.split_text(text)

        return [
            TextChunk(
                content=chunk,
                chunk_index=i,
                metadata={**base_metadata, "chunk_index": i, "chunk_total": len(raw_chunks)},
            )
            for i, chunk in enumerate(raw_chunks)
            if chunk.strip()  # drop empty chunks
        ]

    def chunk_documents(
            self,
            pages: list[dict],  # [{"text": "...", "page_num": 1}, ...]
        ) -> list[TextChunk]:
            """
            For PDFs or multi-page sources — chunk per page and carry page metadata.
            Keeps chunk origins traceable all the way back to the source page.
            """
            all_chunks = []

            for page in pages:
                page_chunks = self.chunk(
                    text=page["text"],
                    base_metadata={k: v for k, v in page.items() if k != "text"},
                )
                all_chunks.extend(page_chunks)

            # Re-index globally after combining all pages
            for i, chunk in enumerate(all_chunks):
                chunk.chunk_index = i

            return all_chunks