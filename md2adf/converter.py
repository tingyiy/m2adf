"""Core converter: Markdown → Atlassian Document Format (ADF).

Uses mistune's AST mode to parse markdown, then walks the token tree
to produce ADF. The key insight is that ADF uses flat marks on text nodes
while markdown uses nested structure — so we recursively accumulate marks
and flatten them onto leaf text nodes.
"""

from typing import Any, Dict, List, Optional

import mistune


_md = mistune.create_markdown(renderer=None, plugins=["table", "strikethrough"])


def convert(markdown: str) -> Dict[str, Any]:
    """Convert a markdown string to an ADF document.

    Args:
        markdown: The markdown text to convert.

    Returns:
        An ADF document dict with version, type, and content.
    """
    if not markdown or not markdown.strip():
        return {"version": 1, "type": "doc", "content": []}

    tokens = _md(markdown)
    content = _convert_blocks(tokens)

    return {"version": 1, "type": "doc", "content": content}


def _convert_blocks(tokens: List[Dict]) -> List[Dict]:
    """Convert a list of block-level tokens to ADF block nodes."""
    result = []
    for token in tokens:
        node = _convert_block(token)
        if node is not None:
            if isinstance(node, list):
                result.extend(node)
            else:
                result.append(node)
    return result


def _convert_block(token: Dict) -> Optional[Any]:
    """Convert a single block-level token to an ADF node (or list of nodes)."""
    t = token["type"]

    if t == "paragraph":
        content = _convert_inlines(token["children"])
        if content:
            return {"type": "paragraph", "content": content}
        return None

    if t == "heading":
        level = token["attrs"]["level"]
        content = _convert_inlines(token["children"])
        node = {"type": "heading", "attrs": {"level": level}}
        if content:
            node["content"] = content
        return node

    if t == "block_code":
        raw = token.get("raw", "")
        info = token.get("attrs", {}).get("info")
        node = {"type": "codeBlock"}
        if info:
            node["attrs"] = {"language": info}
        node["content"] = [{"type": "text", "text": raw}]
        return node

    if t == "block_quote":
        content = _convert_blocks(token["children"])
        if content:
            return {"type": "blockquote", "content": content}
        return None

    if t == "list":
        ordered = token["attrs"].get("ordered", False)
        list_type = "orderedList" if ordered else "bulletList"
        items = []
        for child in token["children"]:
            if child["type"] == "list_item":
                item_content = _convert_list_item(child)
                items.append({"type": "listItem", "content": item_content})
        return {"type": list_type, "content": items}

    if t == "thematic_break":
        return {"type": "rule"}

    if t == "table":
        return _convert_table(token)

    return None


def _convert_list_item(token: Dict) -> List[Dict]:
    """Convert a list_item token's children into ADF content.

    Mistune wraps tight list text in block_text nodes. We convert those
    to paragraphs. Nested lists are preserved as-is.
    """
    result = []
    for child in token["children"]:
        if child["type"] == "block_text":
            content = _convert_inlines(child["children"])
            if content:
                result.append({"type": "paragraph", "content": content})
        elif child["type"] == "paragraph":
            content = _convert_inlines(child["children"])
            if content:
                result.append({"type": "paragraph", "content": content})
        elif child["type"] == "list":
            result.append(_convert_block(child))
        else:
            block = _convert_block(child)
            if block is not None:
                if isinstance(block, list):
                    result.extend(block)
                else:
                    result.append(block)
    return result


def _convert_table(token: Dict) -> Dict:
    """Convert a mistune table AST to an ADF table node."""
    rows = []
    for child in token["children"]:
        if child["type"] == "table_head":
            # Header row
            cells = []
            for cell_token in child["children"]:
                cell_content = _convert_inlines(cell_token["children"])
                cells.append({
                    "type": "tableHeader",
                    "content": [{"type": "paragraph", "content": cell_content or []}],
                })
            rows.append({"type": "tableRow", "content": cells})

        elif child["type"] == "table_body":
            for row_token in child["children"]:
                cells = []
                for cell_token in row_token["children"]:
                    cell_content = _convert_inlines(cell_token["children"])
                    cells.append({
                        "type": "tableCell",
                        "content": [{"type": "paragraph", "content": cell_content or []}],
                    })
                rows.append({"type": "tableRow", "content": cells})

    return {"type": "table", "content": rows}


def _convert_inlines(children: List[Dict], marks: Optional[List[Dict]] = None) -> List[Dict]:
    """Convert inline tokens to ADF text nodes, flattening nested marks.

    This is the core algorithm: we walk the inline tree recursively,
    accumulating marks (strong, em, link, etc.) and applying them all
    to leaf text nodes. This correctly handles cases like
    ``**bold _italic_ text**`` producing three text nodes all with
    ``strong``, with the middle also having ``em``.

    Args:
        children: List of inline tokens from mistune AST.
        marks: Currently accumulated marks from parent nodes.

    Returns:
        List of ADF inline nodes (text, hardBreak, etc.).
    """
    marks = marks or []
    result = []

    for token in children:
        t = token["type"]

        if t == "text":
            node = {"type": "text", "text": token["raw"]}
            if marks:
                node["marks"] = list(marks)
            result.append(node)

        elif t == "strong":
            result.extend(
                _convert_inlines(token["children"], marks + [{"type": "strong"}])
            )

        elif t == "emphasis":
            result.extend(
                _convert_inlines(token["children"], marks + [{"type": "em"}])
            )

        elif t == "strikethrough":
            result.extend(
                _convert_inlines(token["children"], marks + [{"type": "strike"}])
            )

        elif t == "link":
            link_mark = {"type": "link", "attrs": {"href": token["attrs"]["url"]}}
            result.extend(
                _convert_inlines(token["children"], marks + [link_mark])
            )

        elif t == "image":
            # ADF has a mediaSingle/media node but it requires upload.
            # Fall back to a text link with the alt text.
            url = token["attrs"]["url"]
            alt_children = token.get("children", [])
            alt_text = alt_children[0]["raw"] if alt_children else url
            link_mark = {"type": "link", "attrs": {"href": url}}
            node = {"type": "text", "text": alt_text, "marks": marks + [link_mark]}
            result.append(node)

        elif t == "codespan":
            node = {"type": "text", "text": token["raw"]}
            node["marks"] = marks + [{"type": "code"}]
            result.append(node)

        elif t == "softbreak":
            # Soft line breaks in markdown — just emit a space or skip.
            # ADF doesn't have a direct equivalent; treat as whitespace.
            node = {"type": "text", "text": " "}
            if marks:
                node["marks"] = list(marks)
            result.append(node)

        elif t == "linebreak":
            result.append({"type": "hardBreak"})

    return result
