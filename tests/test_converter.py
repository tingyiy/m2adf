"""Tests for md2adf converter."""

from md2adf import convert


def test_empty_string():
    result = convert("")
    assert result == {"version": 1, "type": "doc", "content": []}


def test_whitespace_only():
    result = convert("   \n\n  ")
    assert result == {"version": 1, "type": "doc", "content": []}


def test_plain_paragraph():
    result = convert("Hello world")
    assert result["type"] == "doc"
    assert result["version"] == 1
    assert len(result["content"]) == 1
    para = result["content"][0]
    assert para["type"] == "paragraph"
    assert para["content"] == [{"type": "text", "text": "Hello world"}]


def test_bold():
    result = convert("**bold**")
    para = result["content"][0]
    assert para["content"] == [
        {"type": "text", "text": "bold", "marks": [{"type": "strong"}]}
    ]


def test_italic():
    result = convert("_italic_")
    para = result["content"][0]
    assert para["content"] == [
        {"type": "text", "text": "italic", "marks": [{"type": "em"}]}
    ]


def test_strikethrough():
    result = convert("~~deleted~~")
    para = result["content"][0]
    assert para["content"] == [
        {"type": "text", "text": "deleted", "marks": [{"type": "strike"}]}
    ]


def test_inline_code():
    result = convert("`code`")
    para = result["content"][0]
    assert para["content"] == [
        {"type": "text", "text": "code", "marks": [{"type": "code"}]}
    ]


def test_bold_and_plain():
    result = convert("**Hello** world")
    para = result["content"][0]
    assert para["content"] == [
        {"type": "text", "text": "Hello", "marks": [{"type": "strong"}]},
        {"type": "text", "text": " world"},
    ]


def test_nested_bold_italic():
    result = convert("**bold _and italic_ text**")
    para = result["content"][0]
    assert len(para["content"]) == 3
    assert para["content"][0] == {
        "type": "text",
        "text": "bold ",
        "marks": [{"type": "strong"}],
    }
    assert para["content"][1] == {
        "type": "text",
        "text": "and italic",
        "marks": [{"type": "strong"}, {"type": "em"}],
    }
    assert para["content"][2] == {
        "type": "text",
        "text": " text",
        "marks": [{"type": "strong"}],
    }


def test_link():
    result = convert("[click](https://example.com)")
    para = result["content"][0]
    assert para["content"] == [
        {
            "type": "text",
            "text": "click",
            "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
        }
    ]


def test_bold_link():
    result = convert("**bold [link](https://example.com)**")
    para = result["content"][0]
    assert len(para["content"]) == 2
    assert para["content"][0] == {
        "type": "text",
        "text": "bold ",
        "marks": [{"type": "strong"}],
    }
    assert para["content"][1] == {
        "type": "text",
        "text": "link",
        "marks": [
            {"type": "strong"},
            {"type": "link", "attrs": {"href": "https://example.com"}},
        ],
    }


def test_image_as_link():
    result = convert("![alt text](https://img.png)")
    para = result["content"][0]
    # Image falls back to a text node with link mark
    assert len(para["content"]) >= 1
    # Find the node with our alt text
    img_nodes = [n for n in para["content"] if n.get("text") == "alt text"]
    assert len(img_nodes) == 1
    assert any(
        m["type"] == "link" and m["attrs"]["href"] == "https://img.png"
        for m in img_nodes[0]["marks"]
    )


def test_heading_levels():
    for level in range(1, 7):
        result = convert(f"{'#' * level} Heading {level}")
        heading = result["content"][0]
        assert heading["type"] == "heading"
        assert heading["attrs"]["level"] == level
        assert heading["content"] == [{"type": "text", "text": f"Heading {level}"}]


def test_code_block():
    result = convert("```python\nprint('hello')\n```")
    block = result["content"][0]
    assert block["type"] == "codeBlock"
    assert block["attrs"] == {"language": "python"}
    assert block["content"] == [{"type": "text", "text": "print('hello')\n"}]


def test_code_block_no_language():
    result = convert("```\nplain code\n```")
    block = result["content"][0]
    assert block["type"] == "codeBlock"
    assert "attrs" not in block
    assert block["content"] == [{"type": "text", "text": "plain code\n"}]


def test_bullet_list():
    result = convert("- item 1\n- item 2\n- item 3")
    lst = result["content"][0]
    assert lst["type"] == "bulletList"
    assert len(lst["content"]) == 3
    for i, item in enumerate(lst["content"]):
        assert item["type"] == "listItem"
        assert item["content"][0]["type"] == "paragraph"
        assert item["content"][0]["content"] == [
            {"type": "text", "text": f"item {i + 1}"}
        ]


def test_ordered_list():
    result = convert("1. first\n2. second")
    lst = result["content"][0]
    assert lst["type"] == "orderedList"
    assert len(lst["content"]) == 2
    assert lst["content"][0]["content"][0]["content"] == [
        {"type": "text", "text": "first"}
    ]


def test_nested_list():
    result = convert("- a\n  - b\n  - c\n- d")
    lst = result["content"][0]
    assert lst["type"] == "bulletList"
    assert len(lst["content"]) == 2  # top-level items: a, d

    # First item should have text "a" and a nested bulletList
    first_item = lst["content"][0]
    assert first_item["content"][0]["type"] == "paragraph"
    assert first_item["content"][0]["content"] == [{"type": "text", "text": "a"}]
    nested_list = first_item["content"][1]
    assert nested_list["type"] == "bulletList"
    assert len(nested_list["content"]) == 2  # b, c


def test_blockquote():
    result = convert("> quoted text")
    bq = result["content"][0]
    assert bq["type"] == "blockquote"
    assert bq["content"][0]["type"] == "paragraph"
    assert bq["content"][0]["content"] == [{"type": "text", "text": "quoted text"}]


def test_blockquote_with_formatting():
    result = convert("> **bold** quote")
    bq = result["content"][0]
    para = bq["content"][0]
    assert para["content"][0] == {
        "type": "text",
        "text": "bold",
        "marks": [{"type": "strong"}],
    }


def test_horizontal_rule():
    result = convert("---")
    assert result["content"][0] == {"type": "rule"}


def test_hard_line_break():
    result = convert("line1  \nline2")
    para = result["content"][0]
    assert {"type": "hardBreak"} in para["content"]
    texts = [n["text"] for n in para["content"] if n["type"] == "text"]
    assert "line1" in texts
    assert "line2" in texts


def test_table():
    md = "| Name | Age |\n|---|---|\n| Alice | 30 |\n| Bob | 25 |"
    result = convert(md)
    table = result["content"][0]
    assert table["type"] == "table"
    assert len(table["content"]) == 3  # 1 header row + 2 data rows

    header_row = table["content"][0]
    assert header_row["content"][0]["type"] == "tableHeader"
    assert header_row["content"][1]["type"] == "tableHeader"

    data_row = table["content"][1]
    assert data_row["content"][0]["type"] == "tableCell"
    assert data_row["content"][1]["type"] == "tableCell"

    # Check header text
    h1_para = header_row["content"][0]["content"][0]
    assert h1_para["content"] == [{"type": "text", "text": "Name"}]

    # Check data text
    d1_para = data_row["content"][0]["content"][0]
    assert d1_para["content"] == [{"type": "text", "text": "Alice"}]


def test_multiple_paragraphs():
    result = convert("First paragraph.\n\nSecond paragraph.")
    assert len(result["content"]) == 2
    assert result["content"][0]["type"] == "paragraph"
    assert result["content"][1]["type"] == "paragraph"


def test_mixed_document():
    md = """# Title

Some **bold** text.

- item 1
- item 2

> A quote

```js
console.log("hi")
```"""
    result = convert(md)
    types = [n["type"] for n in result["content"]]
    assert types == ["heading", "paragraph", "bulletList", "blockquote", "codeBlock"]


def test_table_with_formatting():
    md = "| Header |\n|---|\n| **bold** cell |"
    result = convert(md)
    table = result["content"][0]
    data_row = table["content"][1]
    cell_para = data_row["content"][0]["content"][0]
    bold_node = cell_para["content"][0]
    assert bold_node == {
        "type": "text",
        "text": "bold",
        "marks": [{"type": "strong"}],
    }
