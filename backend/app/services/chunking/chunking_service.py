import logging
import re

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)

# Patterns that signal structural document elements
_LIST_ITEM_RE = re.compile(r"^\s*([•\u2022\u25E6\-\u2023\u25C7\u25C8\u2022]|\d+\.|\d+\))\s+")
_HEADING_KEYWORDS = re.compile(
    r"\b(Experience|Education|Skills|Projects|Certifications|Summary|Profile|"
    r"Contact|Resume|Work History|Expleo|Portfolio|Kaggle|Github|Email|Mobile|"
    r"Sentiment Analysis|ResNet|Brain Tumor|Hand Gesture|KNN|SVM|Decision Tree|"
    r"RAG|Data Augmentation|Test Cases|Automation)\b",
    re.IGNORECASE,
)


class ChunkingService:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
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
                pc["heading_hierarchy"] = self._extract_headings(text)
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

    def _chunk_page(self, text: str, document_id: str, fname: str, page_number: int, start_counter: int) -> list:
        chunks = []
        text_length = len(text)
        counter = start_counter

        sentences = self._split_into_sentences(text)

        if not sentences:
            if text.strip():
                chunk_id = f"{document_id}_chunk_{counter}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "file_name": fname,
                    "document_id": document_id,
                    "page_number": page_number,
                    "chunk_text": text,
                    "char_start": 0,
                    "char_end": text_length,
                })
            return chunks

        current_chunk_sentences = []
        current_chunk_len = 0
        chunk_start = 0
        last_sentence_end = 0

        for _i, sentence in enumerate(sentences):
            sentence_len = len(sentence)

            if current_chunk_len + sentence_len > self.chunk_size and current_chunk_sentences:
                chunk_text = "".join(current_chunk_sentences)
                chunk_id = f"{document_id}_chunk_{counter}"

                chunks.append({
                    "chunk_id": chunk_id,
                    "file_name": fname,
                    "document_id": document_id,
                    "page_number": page_number,
                    "chunk_text": chunk_text,
                    "char_start": chunk_start,
                    "char_end": chunk_start + len(chunk_text),
                })

                counter += 1

                overlap_len = 0
                overlap_text = ""
                for sent in reversed(current_chunk_sentences):
                    if overlap_len + len(sent) <= self.chunk_overlap:
                        overlap_text = sent + overlap_text
                        overlap_len += len(sent)
                    else:
                        break

                current_chunk_sentences = [overlap_text] if overlap_text.strip() else []
                current_chunk_len = len(overlap_text)
                chunk_start = chunk_start + len(chunk_text) - overlap_len

            current_chunk_sentences.append(sentence)
            current_chunk_len += sentence_len
            last_sentence_end = chunk_start + current_chunk_len

        if current_chunk_sentences:
            chunk_text = "".join(current_chunk_sentences)
            chunk_id = f"{document_id}_chunk_{counter}"
            chunks.append({
                "chunk_id": chunk_id,
                "file_name": fname,
                "document_id": document_id,
                "page_number": page_number,
                "chunk_text": chunk_text,
                "char_start": chunk_start,
                "char_end": last_sentence_end,
            })

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        sentences = []
        current = []
        i = 0

        while i < len(text):
            current.append(text[i])

            if text[i] in '.!?':
                if i + 1 < len(text) and text[i + 1] in '.!?':
                    i += 1
                    current.append(text[i])

                if i + 1 < len(text) and text[i + 1] in ' \t\n':
                    sentence = ''.join(current).strip()
                    if sentence:
                        sentences.append(sentence + text[i])
                    current = []
                    i += 1
                    while i < len(text) and text[i] in ' \t\n':
                        i += 1
                    continue

            elif text[i] == '\n' and i + 1 < len(text) and text[i + 1] == '\n':
                sentence = ''.join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []

            i += 1

        if current:
            sentence = ''.join(current).strip()
            if sentence:
                sentences.append(sentence)

        return sentences
