"""
html_utils.py — shared HTML-to-text helper.

Used by both validate.py (to judge real content length/garbledness) and
clean_transform.py (to produce the text that gets embedded). Both stages
need to agree on what "the actual text" of a ticket is — validating
raw-HTML length would let a near-empty body slip through just because it's
wrapped in a few tags.
"""

from bs4 import BeautifulSoup


def strip_html(raw: str) -> str:
    """Parse (possibly malformed) HTML and return plain text.

    Uses a real HTML parser rather than regex substitution — regex can't
    reliably handle unclosed tags, nested markup, or entity decoding, all
    of which show up in real rich-text ticket bodies.
    """
    if not raw or "<" not in raw or ">" not in raw:
        return raw
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for quote in soup.find_all("blockquote"):
        quote.decompose()  # drop quoted prior-message thread — pure noise for search
    return soup.get_text(separator=" ")
