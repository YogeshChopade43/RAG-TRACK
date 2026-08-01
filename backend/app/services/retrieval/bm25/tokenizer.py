"""
Tokenizer for BM25 retrieval.

Light stopword removal for general text. Preserves technical acronyms
and short tokens (len >= 2) critical for resumes and technical docs.
"""

import re

STOPWORDS = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
    'those', 'it', 'its', 'as', 'by', 'from', 'about', 'into', 'than',
    'then', 'so', 'if', 'out', 'up', 'down', 'here', 'there', 'when',
    'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'very',
    'just', 'too', 'also', 'now',
})


def tokenize(text: str) -> list[str]:
    """
    Tokenize text into lowercase tokens, removing general stopwords.

    Preserves technical acronyms and short tokens (len >= 2)
    that are critical for resumes and technical documents.

    Args:
        text: Input text string

    Returns:
        List of token strings
    """
    tokens = re.findall(r'\b\w+\b', text.lower())
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]
    return filtered
