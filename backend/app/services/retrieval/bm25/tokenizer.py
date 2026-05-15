"""
Tokenizer for BM25 retrieval.

Uses simple whitespace tokenization with a comprehensive stopword list
(identical to the one used in reranking_service.py for consistency).
"""

import re
from typing import List

# Comprehensive stopword list (same as reranking_service.py)
STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
    'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how', 'their',
    'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her',
    'would', 'make', 'like', 'into', 'him', 'time', 'two', 'more', 'go',
    'no', 'way', 'could', 'my', 'than', 'first', 'been', 'call', 'who',
    'oil', 'sit', 'now', 'find', 'down', 'day', 'did', 'get', 'come',
    'made', 'may', 'part', 'over', 'new', 'sound', 'take', 'only', 'little',
    'work', 'know', 'place', 'year', 'live', 'me', 'back', 'give', 'most',
    'very', 'after', 'thing', 'our', 'just', 'name', 'good', 'sentence',
    'man', 'think', 'say', 'great', 'where', 'help', 'through', 'much',
    'before', 'line', 'right', 'too', 'mean', 'old', 'any', 'same', 'tell',
    'boy', 'follow', 'came', 'want', 'show', 'also', 'around', 'form',
    'three', 'small', 'set', 'put', 'end', 'does', 'another', 'well',
    'large', 'must', 'big', 'even', 'such', 'because', 'turn', 'here',
    'why', 'ask', 'went', 'men', 'read', 'need', 'land', 'different',
    'home', 'us', 'move', 'try', 'kind', 'hand', 'picture', 'again',
    'change', 'off', 'play', 'spell', 'air', 'away', 'animal', 'house',
    'point', 'page', 'letter', 'mother', 'answer', 'found', 'study',
    'still', 'learn', 'should', 'world', 'high', 'every', 'between',
    'both', 'country', 'under', 'last', 'never', 'dear', 'word', 'while',
    'below', 'above', 'along', 'among', 'whether', 'upon', 'either',
    'neither', 'across', 'toward', 'towards', 'onto', 'into', 'within',
    'without', 'behind', 'beyond', 'plus', 'minus', 'except', 'until',
    'since', 'despite', 'unlike', 'including', 'regarding', 'concerning',
    'considering', 'regardless', 'notwithstanding', 'according',
    'furthermore', 'moreover', 'however', 'therefore', 'thus', 'hence',
    'consequently', 'accordingly', 'meanwhile', 'otherwise', 'instead',
    'likewise', 'similarly', 'namely', 'specifically', 'particularly',
    'especially', 'indeed', 'actually', 'really', 'quite', 'rather',
    'somewhat', 'slightly', 'barely', 'hardly', 'scarcely', 'almost',
    'nearly', 'approximately', 'roughly', 'about', 'around', 'circa',
    'versus', 'via', 'per', 'pro', 'con', 'anti', 'non', 'un', 'in',
    'im', 'ir', 'il', 'dis', 'mis', 'over', 're', 'pre', 'post', 'sub',
    'super', 'trans', 'inter', 'intra', 'extra', 'ultra', 'mega', 'micro',
    'macro', 'multi', 'semi', 'quasi', 'pseudo', 'neo', 'anti', 'counter',
    'pro', 'contra', 'vice', 'para', 'ortho', 'meta', 'epi', 'hypo',
    'hyper', 'endo', 'exo', 'ecto', 'meso', 'thermo', 'hydro', 'geo',
    'bio', 'psycho', 'socio', 'chrono', 'auto', 'hetero', 'homo', 'mono',
    'di', 'tri', 'tetra', 'penta', 'hexa', 'hepta', 'octa', 'nona', 'deca',
}


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into lowercase tokens, removing stopwords and punctuation.

    Args:
        text: Input text string

    Returns:
        List of token strings
    """
    # Lowercase and split on non-word characters
    tokens = re.findall(r'\b\w+\b', text.lower())

    # Remove stopwords and short tokens
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) > 2]

    return filtered
