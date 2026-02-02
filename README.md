# Website Reverse-Engineering Agent 🔬

An autonomous agent that crawls websites and generates comprehensive "Rebuild Blueprints" - detailed JSON specifications describing data models, user flows, and business logic.

## 🎯 Key Innovation: Split-Brain Architecture

This system uses a **"Split-Brain" cost-optimization strategy**:

1. **The Scout (Free)**: Uses Playwright to navigate, cluster pages by structural similarity, and capture network traffic. Costs $0.
2. **The Analyst (Paid)**: Uses LLM APIs ONLY to analyze unique page templates. Minimizes API costs by 50-95%.

### Why This Matters

Without clustering, analyzing 1,000 pages = 1,000 LLM API calls ($30-$150).  
With clustering, 1,000 pages → ~10 unique templates = 10 LLM API calls ($0.30-$1.50).

**~95% cost reduction while maintaining quality.**

---

## 🏗️ Architecture

```
web_reverser/
├── core/
│   ├── scout.py        # Playwright-based crawler (FREE)
│   └── analyst.py      # LLM-based analyzer (PAID)
├── utils/
│   └── dom_processor.py # Structural hashing & token optimization
├── models/
│   └── schemas.py      # Pydantic data models
└── main.py            # Orchestrator
```

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# 1. Clone or copy the project
cd web_reverser

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium
```

---

## 📖 Usage

### Basic Usage (Testing Mode - No LLM Costs)

```bash
python main.py https://example.com --max-pages 20 --max-depth 2
```

This will:
- Crawl up to 20 pages
- Cluster them by structure
- Generate a blueprint (without LLM analysis)
- Show cost savings from clustering

### Production Usage (With LLM Analysis)

```bash
python main.py https://target-site.com \
  --max-pages 50 \
  --max-depth 3 \
  --enable-llm \
  --output-dir ./blueprints
```

### Command Line Options

```
--max-pages N        Maximum pages to crawl (default: 20)
--max-depth N        Maximum link depth (default: 2)
--enable-llm         Enable LLM analysis (requires API key)
--headless           Run browser in headless mode (default: True)
--output-dir PATH    Output directory for blueprints (default: ./output)
```

---

## 🧩 Core Components

### 1. Structural Clustering Engine (The Cost Saver)

**File**: `utils/dom_processor.py`

**Problem**: Analyzing 100 product pages individually is wasteful.

**Solution**: `generate_structural_hash(html)` creates a signature based only on DOM hierarchy, ignoring content.

```python
from utils.dom_processor import generate_structural_hash

# Same structure = Same hash
hash1 = generate_structural_hash(product_page_1)
hash2 = generate_structural_hash(product_page_2)

if hash1 == hash2:
    print("Duplicate structure! Skip LLM analysis.")
```

**Algorithm**:
1. Strip all text content
2. Remove dynamic attributes (href, src, data-*)
3. Keep only: tag names, nesting, structural classes
4. Generate SHA256 hash

### 2. Token Diet Pre-processor

**Function**: `clean_dom_for_llm(html)`

**Problem**: Raw HTML = 500KB = 100k+ tokens = $3-$5 per page

**Solution**: Aggressive cleaning → 5KB = 2k tokens = $0.06 per page

**What it removes**:
- `<script>`, `<style>`, `<svg>`, `<meta>`
- Comments, inline styles
- Generic wrapper `<div>`s
- Excessive whitespace

**What it keeps**:
- Forms, inputs, buttons (critical for logic)
- Semantic headers (H1-H6)
- Aria-labels (semantic meaning)
- Text samples (truncated)

**Example**:
```python
from utils.dom_processor import clean_dom_for_llm, estimate_tokens

cleaned_html, raw_size, cleaned_size = clean_dom_for_llm(html)

print(f"Raw: {raw_size} bytes → {estimate_tokens(html)} tokens")
print(f"Cleaned: {cleaned_size} bytes → {estimate_tokens(cleaned_html)} tokens")
print(f"Reduction: {((raw_size - cleaned_size) / raw_size) * 100:.1f}%")
```

### 3. Network Sniffer (The Truth-Seeker)

**File**: `core/scout.py`

**Philosophy**: The UI lies, but the API tells the truth about data structures.

Playwright intercepts all XHR/Fetch JSON responses:

```python
# Automatically captures:
POST /api/login
  Payload: {"email": "user@example.com", "password": "xxx"}
  Response: {"token": "abc", "user": {"id": 1, "name": "John"}}

# Infers data model:
{
  "entity": "User",
  "attributes": ["id", "email", "name", "token"]
}
```

### 4. The Output Schema

**File**: `models/schemas.py`

Pydantic models define the blueprint structure:

```python
class RebuildBlueprint(BaseModel):
    project_name: str
    base_url: str
    total_pages_crawled: int
    unique_clusters_found: int
    total_tokens_saved: int
    clusters: List[PageCluster]
```

Example output:
```json
{
  "project_name": "example_com_clone",
  "base_url": "https://example.com",
  "total_pages_crawled": 47,
  "unique_clusters_found": 8,
  "total_tokens_saved": 125000,
  "clusters": [
    {
      "cluster_id": "a3f2e1...",
      "page_type": "Product Detail Page",
      "representative_url": "/products/123",
      "total_pages_in_cluster": 23,
      "inferred_data_models": [
        {
          "entity": "Product",
          "attributes": ["id", "name", "price", "description"]
        }
      ],
      "network_intercepts": [
        {
          "url": "/api/products/123",
          "method": "GET",
          "response_structure": {...}
        }
      ]
    }
  ]
}
```

---

## 💡 Usage Examples

### Example 1: Test Infrastructure (No Costs)

```bash
# Crawl example.com to test the infrastructure
python main.py https://example.com --max-pages 5 --max-depth 1
```

**Output**:
```
🚀 PHASE 1: Scout Deployment (Free Navigation)
📄 [1/5] Visiting: https://example.com (depth: 0)
   🆕 New cluster detected: a3f2e12d
📄 [2/5] Visiting: https://example.com/about (depth: 1)
   ♻️ Duplicate structure: a3f2e12d (cluster already analyzed)

📊 SCOUT RESULTS
✓ Pages crawled: 5
✓ Unique clusters: 2
✓ Duplicate pages skipped: 3
✓ Tokens saved by clustering: 8,500
✓ Clustering efficiency: 60.0%
✓ Estimated cost savings: $0.26
```

### Example 2: Analyze a Blog

```bash
python main.py https://myblog.com --max-pages 30 --max-depth 2
```

**Expected clusters**:
- Homepage (1 page)
- Blog Post Template (25 pages)
- About Page (1 page)
- Contact Form (1 page)

**Result**: Analyze 4 clusters instead of 30 pages → 87% cost reduction

### Example 3: E-Commerce Site (With LLM)

```bash
export OPENAI_API_KEY="your-key"
python main.py https://shop.example.com \
  --max-pages 100 \
  --max-depth 3 \
  --enable-llm
```

**Expected clusters**:
- Homepage
- Category Pages
- Product Detail Pages (50+ pages, 1 cluster!)
- Cart
- Checkout
- Account Dashboard

**Result**: 6 LLM calls instead of 100 → 94% cost reduction

---

## 🔧 Programmatic Usage

```python
import asyncio
from main import WebReverseEngineer

async def analyze_site():
    engineer = WebReverseEngineer(
        target_url="https://example.com",
        max_pages=50,
        max_depth=2,
        enable_llm_analysis=False  # True in production
    )
    
    blueprint = await engineer.reverse_engineer()
    engineer.save_blueprint(blueprint, output_dir="./output")
    
    # Access results
    print(f"Found {blueprint.unique_clusters_found} unique page types")
    for cluster in blueprint.clusters:
        print(f"- {cluster.page_type}: {cluster.total_pages_in_cluster} pages")

asyncio.run(analyze_site())
```

---

## 🧪 Testing Individual Components

### Test DOM Processor

```bash
cd utils
python dom_processor.py
```

### Test Scout

```bash
cd core
python scout.py
```

### Test Analyst

```bash
cd core
python analyst.py
```

---

## 📊 Cost Analysis

### Without Clustering (Naive Approach)

| Pages | Tokens/Page | Total Tokens | Cost (GPT-4) |
|-------|-------------|--------------|--------------|
| 100   | 5,000       | 500,000      | $15.00       |
| 500   | 5,000       | 2,500,000    | $75.00       |
| 1,000 | 5,000       | 5,000,000    | $150.00      |

### With Clustering (This System)

| Pages | Unique Clusters | Tokens/Cluster | Total Tokens | Cost (GPT-4) | Savings |
|-------|-----------------|----------------|--------------|--------------|---------|
| 100   | 8               | 2,000          | 16,000       | $0.48        | **97%** |
| 500   | 12              | 2,000          | 24,000       | $0.72        | **99%** |
| 1,000 | 15              | 2,000          | 30,000       | $0.90        | **99%** |

---

## 🛠️ Extending the System

### Add Real LLM Integration

Edit `core/analyst.py`:

```python
async def analyze_with_llm(self, cleaned_html, network_logs):
    # Example: OpenAI
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=self.api_key)
    
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a web architecture analyst..."},
            {"role": "user", "content": f"Analyze this page:\n{cleaned_html}"}
        ]
    )
    
    return json.loads(response.choices[0].message.content)
```

### Add Custom Clustering Logic

Edit `utils/dom_processor.py`:

```python
def generate_structural_hash(html: str, custom_rules: dict = None) -> str:
    # Add domain-specific clustering rules
    if custom_rules:
        # Apply custom heuristics
        pass
```

---

## 🎓 Key Concepts Explained

### Why Structural Hashing Works

**Intuition**: Most websites use templates. A product page for "iPhone" and "Android Phone" use the SAME layout but different content.

**Example**:
```html
<!-- Page A -->
<div class="product">
  <h1>iPhone 15</h1>
  <p>$999</p>
</div>

<!-- Page B -->
<div class="product">
  <h1>Samsung Galaxy</h1>
  <p>$899</p>
</div>
```

**After Stripping Content**:
```html
<!-- Both pages -->
<div class="product">
  <h1></h1>
  <p></p>
</div>
```

**Result**: Same hash → Same cluster → Analyze once!

---

## 🚨 Limitations & Roadmap

### Current Limitations

1. **No JavaScript Rendering Analysis**: Currently analyzes static DOM, not dynamic client-side rendering logic
2. **Mock LLM Analysis**: Placeholder implementation (easy to replace)
3. **No Auth Handling**: Doesn't handle login flows yet
4. **English-Centric**: Token estimation assumes English text

### Roadmap

- [ ] Add real LLM integration (OpenAI, Anthropic, Local)
- [ ] Support authentication flows
- [ ] Add screenshot capture for visual analysis
- [ ] Implement page interaction simulation (form filling)
- [ ] Add export to various formats (Markdown, PlantUML)
- [ ] Create web UI for blueprint visualization

---

## 📝 License

MIT License - Feel free to use and modify!

---

## 🤝 Contributing

This is a proof-of-concept architecture. To improve it:

1. Replace mock LLM calls with real implementations
2. Add more sophisticated clustering heuristics
3. Implement better data model inference
4. Add test coverage

---

## 💬 Questions?

This system demonstrates:
- ✅ Asynchronous web crawling with Playwright
- ✅ Cost-optimized LLM usage through clustering
- ✅ Network traffic interception
- ✅ DOM structural analysis
- ✅ Pydantic schema validation

**Core Philosophy**: Intelligence (LLM) is expensive. Navigation (browser) is free. Maximize the free part, minimize the expensive part.

---

**Built with Python 🐍 + Playwright 🎭 + Smart Engineering 🧠**
