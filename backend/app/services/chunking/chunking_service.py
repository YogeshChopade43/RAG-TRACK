import logging
import re
from typing import Optional

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)

# Patterns that signal structural document elements
_LIST_ITEM_RE = re.compile(r"^\s*([•\u2022\u25E6\-\u2023\u25C7\u25C8\u2022]|\d+\.|\d+\))\s+")
_HEADING_KEYWORDS = re.compile(
    r"\b(Experience|Education|Skills|Projects|Certifications|Summary|Profile|"
    r"Contact|Resume|Work History|Introduction|Overview|Background|Methods?|"
    r"Results|Discussion|Conclusions?|References|Appendix|Abstract)\b",
    re.IGNORECASE,
)
_SECTION_HEADING_RE = re.compile(
    r"\b(Experience|Education|Skills|Projects|Certifications|Summary|Profile|"
    r"Contact|Resume|Work History)\b",
    re.IGNORECASE,
)


class ChunkingService:
    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        self.chunk_size = chunk_size or CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or CHUNK_OVERLAP

    def chunk(self, parsed_load: dict) -> list:
        document_id = parsed_load["document_id"]
        pages = parsed_load["pages"]
        fname = parsed_load["file_name"]
        logger.info(f"Chunking document {document_id} with filename {fname}")

        if not pages:
            raise ValueError("No pages found to chunk")

        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE must be positive")

        chunks = []
        chunk_counter = 1
        reading_order = 0

        for page_idx, page in enumerate(pages):
            page_number = page["page_number"]
            text = page["text"]

            page_chunks = self._chunk_page(
                text, document_id, fname, page_number, chunk_counter
            )
            for pc in page_chunks:
                pc["is_title_block"] = page_idx == 0 and reading_order == 0
                pc["reading_order"] = reading_order
                pc["structural_type"] = self._classify_chunk(pc["chunk_text"])
                reading_order += 1

            chunks.extend(page_chunks)
            chunk_counter += len(page_chunks)

        logger.info(f"Total chunks created: {len(chunks)}")
        if chunks:
            logger.debug(f"Sample chunk: {chunks[0]}")

        return chunks

    @staticmethod
    def _classify_chunk(text: str) -> str:
        """Classify a chunk by its dominant structural pattern."""
        stripped = text.strip()
        if not stripped:
            return "paragraph"

        lines = [l for l in stripped.splitlines() if l.strip()]
        if not lines:
            return "paragraph"

        # Title / header block: short, no terminal punctuation, looks like a title
        first_line = lines[0].strip()
        if len(first_line) <= 100 and not first_line.endswith((".", "!", "?")):
            if _HEADING_KEYWORDS.search(first_line) and len(first_line.split()) <= 15:
                return "heading"

        # List item: starts with bullet or numbered marker
        if _LIST_ITEM_RE.match(stripped):
            return "list_item"

        # Multi-line block where most lines are list items
        list_count = sum(1 for l in lines if _LIST_ITEM_RE.match(l))
        if list_count > 0 and list_count >= len(lines) * 0.5:
            return "list_item"

        return "paragraph"

    @staticmethod
    def _extract_headings(text: str) -> list[str]:
        """Extract heading-like lines from page text for hierarchy context."""
        headings = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if _HEADING_KEYWORDS.search(stripped) and len(stripped) <= 60:
                headings.append(stripped)
        return headings

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """Split page text into sections at heading boundaries.

        Uses regex to find section headings anywhere in the text,
        not just at line boundaries, to handle PDFs with inline text.
        """
        sections: list[tuple[str, str]] = []
        heading_positions: list[tuple[int, str]] = []

        for m in _SECTION_HEADING_RE.finditer(text):
            heading_positions.append((m.start(), m.group().strip()))

        if not heading_positions:
            return [("", text)]

        heading_positions.sort(key=lambda x: x[0])

        prev_end = 0
        for pos, heading in heading_positions:
            if pos > prev_end:
                sections.append(("", text[prev_end:pos]))
            next_pos = None
            for next_pos_iter, _ in heading_positions:
                if next_pos_iter > pos:
                    next_pos = next_pos_iter
                    break
            end = next_pos if next_pos is not None else len(text)
            sections.append((heading, text[pos:end]))
            prev_end = end

        if prev_end < len(text):
            sections.append(("", text[prev_end:]))

        return sections

    def _chunk_page(self, text: str, document_id: str, fname: str, page_number: int, start_counter: int) -> list:
        sections = self._split_into_sections(text)
        chunks = []
        counter = start_counter

        for heading, section_text in sections:
            if not section_text.strip():
                continue

            section_chunks = self._chunk_section(
                section_text, document_id, fname, page_number, counter
            )
            for chunk in section_chunks:
                chunk["heading_hierarchy"] = [heading] if heading else []
            chunks.extend(section_chunks)
            counter += len(section_chunks)

        return chunks

    def _chunk_section(self, text: str, document_id: str, fname: str, page_number: int, start_counter: int) -> list:
        """Pack sentences into chunks of up to chunk_size characters, overlapping by up to chunk_overlap."""
        sentences = self._split_into_sentences(text) or ([text.strip()] if text.strip() else [])
        chunks = []
        counter = start_counter
        chunk_start = 0
        current: list[str] = []

        def emit(sents: list[str]) -> str:
            chunk_text = " ".join(sents)
            chunks.append({
                "chunk_id": f"{document_id}_chunk_{counter}",
                "file_name": fname,
                "document_id": document_id,
                "page_number": page_number,
                "chunk_text": chunk_text,
                "char_start": chunk_start,
                "char_end": chunk_start + len(chunk_text),
            })
            return chunk_text

        for sentence in sentences:
            if current and len(" ".join(current + [sentence])) > self.chunk_size:
                chunk_text = emit(current)
                counter += 1
                # Carry the trailing sentences that fit in chunk_overlap into the next chunk
                overlap: list[str] = []
                for sent in reversed(current):
                    if len(" ".join([sent] + overlap)) > self.chunk_overlap:
                        break
                    overlap.insert(0, sent)
                chunk_start += len(chunk_text) - len(" ".join(overlap))
                current = overlap
            current.append(sentence)

        if current:
            emit(current)
        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split at ., ! or ? (runs like '?!' kept together) followed by whitespace, or at blank lines."""
        parts = re.split(r"(?<=[.!?])\s+|\n\s*\n", text)
        return [p.strip() for p in parts if p and p.strip()]
