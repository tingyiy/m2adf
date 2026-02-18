# md2adf

Convert Markdown to [Atlassian Document Format (ADF)](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/) — the JSON format required by Jira and Confluence REST APIs for rich text.

## Installation

```bash
pip install md2adf
```

## Usage

```python
from md2adf import convert

adf = convert("**Hello** world")
# {
#   "version": 1,
#   "type": "doc",
#   "content": [
#     {
#       "type": "paragraph",
#       "content": [
#         {"type": "text", "text": "Hello", "marks": [{"type": "strong"}]},
#         {"type": "text", "text": " world"}
#       ]
#     }
#   ]
# }
```

Use it with the Jira API:

```python
import requests
from md2adf import convert

requests.post(
    "https://your-domain.atlassian.net/rest/api/3/issue/PROJ-123/comment",
    json={"body": convert("Fixed the **bug** in `parse_config()`")},
    auth=("user@example.com", "api-token"),
)
```

## Supported Markdown

| Feature | Markdown | ADF Node |
|---------|----------|----------|
| Paragraphs | plain text | `paragraph` |
| Headings | `# H1` ... `###### H6` | `heading` |
| Bold | `**bold**` | `strong` mark |
| Italic | `_italic_` | `em` mark |
| Strikethrough | `~~deleted~~` | `strike` mark |
| Inline code | `` `code` `` | `code` mark |
| Links | `[text](url)` | `link` mark |
| Images | `![alt](url)` | `link` mark (fallback) |
| Code blocks | `` ```lang `` | `codeBlock` |
| Bullet lists | `- item` | `bulletList` |
| Ordered lists | `1. item` | `orderedList` |
| Nested lists | indented items | nested list nodes |
| Blockquotes | `> text` | `blockquote` |
| Horizontal rules | `---` | `rule` |
| Hard line breaks | trailing `  ` | `hardBreak` |
| Tables (GFM) | `\| a \| b \|` | `table` |

Nested inline formatting works correctly — `**bold _and italic_ text**` produces three text nodes with the right combination of marks.

## How It Works

1. Parse markdown with [mistune](https://github.com/lepture/mistune) in AST mode
2. Walk the AST tree recursively, accumulating inline marks (bold, italic, link, etc.)
3. Flatten marks onto leaf text nodes — solving the nested-marks problem that makes naive HTML-style rendering impossible for ADF

## License

MIT
