import re
from typing import List, Dict


class TextCleaningService:
    """
    Cleans parsed PDF/TXT pages.

    Goal:
    Convert layout-extracted PDF text -> semantic readable text
    before chunking and embeddings.

    Input:
        [
          {"page_number": 1, "text": "..."}
        ]

    Output:
        same structure but cleaned text
    """
    
    def clean_pages(self, pages: List[Dict]) -> List[Dict]:

        if not pages:
            return []

        cleaned_pages: List[Dict] = []

        for page in pages:
            text = page.get("text", "")

            if not text:
                continue

            # ---- Cleaning Pipeline Order Matters ----
            text = self._remove_page_footer(text)
            text = self._remove_unicode_noise(text)
            text = self._remove_dotted_lines(text)
            text = self._fix_line_breaks(text)
            text = self._normalize_bullets(text)
            text = self._normalize_hyphenation(text)
            text = self._normalize_spaces(text)
            text = self._normalize_punctuation(text)

            if text.strip():
                cleaned_pages.append({
                    "page_number": page["page_number"],
                    "text": text
                })

        return cleaned_pages

    # =====================================================
    # Individual Cleaning Steps
    # =====================================================

    def _remove_page_footer(self, text: str) -> str:
        """
        Removes footer patterns like:
        Page | 1 of 3
        Page 2 of 5
        """

        text = re.sub(r'Page\s*\|\s*\d+\s*of\s*\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Page\s*\d+\s*of\s*\d+', '', text, flags=re.IGNORECASE)

        return text


    def _remove_unicode_noise(self, text: str) -> str:
        """
        Removes invisible unicode characters and typography artifacts
        """

        # zero-width characters
        text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)

        # normalize fancy dashes
        text = text.replace('–', '-')
        text = text.replace('—', '-')
        text = text.replace('-', '-')

        # normalize ellipsis to space
        text = text.replace('…', ' ')

        return text


    def _remove_dotted_lines(self, text: str) -> str:
        """
        Removes dotted TOC leader lines
        Handles:
            .....
            ………
            . . . . .
        """

        # ascii dots
        text = re.sub(r'\.{3,}', ' ', text)

        # repeated ellipsis
        text = re.sub(r'(…){2,}', ' ', text)

        # mixed dot + ellipsis
        text = re.sub(r'(\.|…){3,}', ' ', text)

        # spaced dots
        text = re.sub(r'(\.\s*){3,}', ' ', text)

        return text


    def _fix_line_breaks(self, text: str) -> str:
        """
        PDF text extraction breaks sentences mid-line.
        This restores paragraphs.
        """

        # join broken lines inside a paragraph
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

        # collapse multiple newlines
        text = re.sub(r'\n{2,}', '\n', text)

        return text


    def _normalize_bullets(self, text: str) -> str:
        """
        Converts bullet glyphs into readable text separators
        """

        bullets = ['•', '▪', '●', '○', '◦', '■', '□']

        for b in bullets:
            text = text.replace(b, '- ')

        return text


    def _normalize_hyphenation(self, text: str) -> str:
        """
        Fix words broken across lines:
        Example:
            time-
            consuming
        becomes:
            timeconsuming
        """

        text = re.sub(r'-\s+', '', text)
        return text


    def _normalize_spaces(self, text: str) -> str:
        """
        Final cleanup of whitespace and punctuation spacing
        """

        # multiple spaces
        text = re.sub(r'[ \t]+', ' ', text)

        # space before punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)

        # remove leading/trailing spaces
        return text.strip()
    
    def _normalize_punctuation(self, text: str) -> str:
        """
        Fix repeated punctuation artifacts left from PDF extraction.
        """

        # collapse multiple periods
        text = re.sub(r'\.{2,}', '.', text)

        # collapse multiple commas
        text = re.sub(r',{2,}', ',', text)

        # collapse multiple exclamation/question
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)

        # remove period at end of very short fragments (common in headings)
        text = re.sub(r'\b([A-Za-z]{2,})\.\s*$', r'\1', text)

        return text