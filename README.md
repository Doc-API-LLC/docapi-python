# docapi-sdk

Official Python SDK for [DocAPI](https://www.docapi.co) — generate PDFs and screenshots from HTML.

```bash
pip install docapi-sdk
```

Zero dependencies. Uses Python's built-in `urllib` (Python 3.8+).

## Quick start

```python
from docapi import DocAPI

client = DocAPI("pk_live_...")

# Generate a PDF
pdf = client.pdf("<h1>Hello World</h1>")
with open("output.pdf", "wb") as f:
    f.write(pdf)

# Screenshot a URL
img = client.screenshot(url="https://example.com")
with open("screenshot.png", "wb") as f:
    f.write(img)
```

Get a free API key at [docapi.co/signup](https://www.docapi.co/signup) — 100 calls/month, no credit card.

---

## API

### `DocAPI(api_key)`

```python
client = DocAPI("pk_live_...")
```

### `client.pdf(html, **options)`

Convert HTML to a PDF. Returns `bytes`.

```python
pdf = client.pdf(
    """
    <html>
      <head>
        <style>body { font-family: sans-serif; padding: 40px; }</style>
      </head>
      <body>
        <h1>Invoice #123</h1>
        <p>Amount due: $4,500.00</p>
      </body>
    </html>
    """,
    format="A4",
    margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
)

with open("invoice.pdf", "wb") as f:
    f.write(pdf)
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `format` | str | `"A4"` | `"A4"`, `"Letter"`, `"Legal"`, `"Tabloid"` |
| `landscape` | bool | `False` | Landscape orientation |
| `print_background` | bool | `True` | Include background colours/images |
| `margin` | dict | — | `{"top": "0.5in", "bottom": "0.5in", ...}` |
| `scale` | float | `1` | Scale factor 0.1–2 |
| `page_ranges` | str | — | Pages to print e.g. `"1-5, 8"` |

### `client.screenshot(*, url=None, html=None, **options)`

Screenshot a URL or render HTML. Returns `bytes`. Provide `url` OR `html`, not both.

```python
# From a URL (e.g. OG image)
img = client.screenshot(url="https://mysite.com/blog/post", width=1200, height=630)

# From HTML
img = client.screenshot(
    html="""
    <div style="width:1200px;height:630px;background:#0f172a;
                display:flex;align-items:center;padding:80px">
      <h1 style="color:white;font-size:64px">My Blog Post</h1>
    </div>
    """,
    width=1200,
    height=630,
)

with open("og.png", "wb") as f:
    f.write(img)
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `url` | str | — | URL to screenshot |
| `html` | str | — | HTML to render |
| `width` | int | `1200` | Viewport width |
| `height` | int | `630` | Viewport height |
| `format` | str | `"png"` | `"png"` or `"jpeg"` |

### `client.credits()`

Check remaining credits and USDC top-up address. Agent accounts only.

```python
info = client.credits()
print(f"{info['credits']} credits remaining")
print(f"Send USDC to {info['usdc_address']}")
```

### `client.credits_remaining`

After any `pdf()` or `screenshot()` call, `client.credits_remaining` holds the value from the `X-Credits-Remaining` response header. Use this to trigger proactive USDC top-ups.

```python
pdf = client.pdf(html)
if (client.credits_remaining or 999) < 50:
    # top up via USDC
    pass
```

### `DocAPI.register(notify_email=None)`

Register a new agent account programmatically. No API key required.

```python
account = DocAPI.register(notify_email="ops@yourcompany.com")

print(account["api_key"])       # "pk_..."
print(account["usdc_address"])  # "0x..."
print(account["free_calls"])    # 10
```

---

## Error handling

All errors raise `DocAPIError` with `status` and `code` attributes.

```python
from docapi import DocAPI, DocAPIError

try:
    pdf = client.pdf("<h1>Hello</h1>")
except DocAPIError as e:
    print(e.status)   # 401, 402, 429, 500
    print(e.code)     # "invalid_api_key", "credits_exhausted", etc.
    print(e.message)
```

| Status | Code | Meaning |
|--------|------|---------|
| 401 | `invalid_api_key` | Invalid or missing API key |
| 402 | `credits_exhausted` | Agent account out of credits — send USDC |
| 429 | `usage_limit_exceeded` | Monthly plan limit reached |
| 500 | `generation_failed` | Rendering error |

---

## Self-managing credits (agent pattern)

```python
from docapi import DocAPI, DocAPIError

API_KEY = "pk_..."
USDC_ADDRESS = "0x..."  # from DocAPI.register()
THRESHOLD = 50
TOPUP_USDC = 10

client = DocAPI(API_KEY)

def generate_pdf(html: str) -> bytes:
    pdf = client.pdf(html)
    if (client.credits_remaining or 999) < THRESHOLD:
        # send USDC via Coinbase AgentKit or your wallet
        # send_usdc(to=USDC_ADDRESS, amount=TOPUP_USDC)
        pass
    return pdf
```

---

## Django example

```python
# views.py
from django.http import HttpResponse
from docapi import DocAPI
import os

client = DocAPI(os.environ["DOCAPI_KEY"])

def invoice_pdf(request, invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    html = render_to_string("invoice.html", {"invoice": invoice})
    pdf = client.pdf(html, format="A4")
    return HttpResponse(pdf, content_type="application/pdf")
```

## Flask example

```python
from flask import Flask, send_file
from docapi import DocAPI
import io, os

app = Flask(__name__)
client = DocAPI(os.environ["DOCAPI_KEY"])

@app.route("/invoice/<int:invoice_id>.pdf")
def invoice_pdf(invoice_id):
    html = build_invoice_html(invoice_id)
    pdf = client.pdf(html)
    return send_file(io.BytesIO(pdf), mimetype="application/pdf")
```

---

## Links

- [Documentation](https://www.docapi.co/docs)
- [Pricing](https://www.docapi.co/pricing)
- [MCP Server](https://www.docapi.co/docs#mcp-server) — use DocAPI directly from Claude Desktop
- [npm SDK](https://www.npmjs.com/package/@docapi/sdk) — Node.js version
- [GitHub](https://github.com/Doc-API-LLC/docapi-python)
