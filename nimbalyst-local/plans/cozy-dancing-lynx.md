# Plan: Rename & Redesign Pretty Fly Support Dashboard

## Context

Three changes requested:
1. **Rename & reorder navigation** — "Pretty Fly Support" consistently; Dashboard (metrics) becomes the landing page; Conversations moves to second
2. **Redesign Dashboard page** — cleaner layout, remove clutter, new smart routing matrix
3. **Fix 76% → 72%** in marketing.html

---

## 1. app.py — Route changes

Make Dashboard (metrics) the landing page:

```python
@app.route('/')
def index():
    return render_template('metrics.html')   # Dashboard = landing page

@app.route('/conversations')
def conversations_page():
    return render_template('dashboard.html') # Conversations = second page

# Keep /metrics as redirect for backwards compatibility
@app.route('/metrics')
def metrics_page():
    return redirect('/')
```

---

## 2. templates/metrics.html — Full redesign

### New page layout order:
1. Header (nav)
2. Impact summary banner
3. **Key Metrics** (4 cards) ← starts here, immediately after banner
4. **Smart Routing Matrix** (new table design)
5. **Estimated System Costs & ROI** (compact 2-column layout)
6. Footer

### Sections REMOVED:
- ~~Tier legend~~ (LTV colour dots — not needed)
- ~~Impact Breakdown~~ (doughnut + bar charts)
- ~~Support Ticket Distribution chart~~
- ~~Data Breakdown~~ (sample vs full dataset cards at bottom)

### Key Metrics (4 cards — replace "Support Hours Saved" with "Response Time"):

| Card | Label | Value | Detail |
|------|-------|-------|--------|
| green | Auto-Resolution Rate | 72% (from API) | 872 of 1,204 tickets auto-handled |
| purple | Response Time | 5 min | Down from 12+ hours (144x faster) |
| red | Marketing Uplift | £140,180 | 10% conversion uplift (potential*) |
| amber | Prevent Sizing Returns | £61,138 | 20% of sizing refunds (potential*) |

*Both labelled "potential — requires sizing context data"

### Impact summary banner — update subtitle:
```
"Based on 24 months of Pretty Fly data (1,204 support tickets)"
"72% auto-resolution · 5-min response · £9k Year 1 investment"
```
Remove the "5,460 hours saved @ £16/hr" line.

### Smart Routing Matrix — new design (replaces the 2-card comparison):

Replace the two "High-Value / Low-Value" comparison cards with a proper routing matrix table:

| Issue Type | Volume | Action | Response Time | Handler |
|---|---|---|---|---|
| Returns & Exchanges | 187 | Auto-approve (≤30 days) | 2 min | 🤖 Claude |
| Order Status | 367 | Auto-provide tracking | Instant | 🤖 Claude |
| Sizing & Fit | 171 | Provide guidance* | 5 min | 🤖 Claude |
| Discount Codes | 147 | Verify & apply | Instant | 🤖 Claude |
| Product Quality | 134 | Escalate — investigate | 24h priority | 👤 Human |
| Drop & Restock | 139 | Escalate — inventory | 24h | 👤 Human |
| Other | 59 | Escalate if complex | 24h | 👤 Human |

*"Sizing — requires product size data for full capability"

Style: clean HTML table with alternating row colours, green rows for auto, amber for escalate.

### Estimated System Costs & ROI — compact redesign:

Instead of 7 individual metric cards stacked vertically (current), use a **2-column compact layout**:

**Left column — costs table:**
```
Year 1 Investment
───────────────────────
Development    £5,000
Claude API       £900
Hosting          £300
Maintenance    £2,000
Infrastructure   £500
Contingency      £300
───────────────────────
TOTAL          £9,000

Year 2+ (recurring): £4,000/year
```

**Right column — ROI summary (3 large stat cards):**
```
[5 months]    Payback Period
[1,950%]      Year 1 ROI
[£201,318]    Annual Benefit (potential)
```

Remove the stale £225,444 and £665,444 figures — these are from before recalculations.

---

## 3. templates/dashboard.html — Nav + title update

- `<title>`: `Pretty Fly Support — Conversations`
- Nav links (reordered):
  ```html
  <a href="/">📊 Dashboard</a>
  <a href="/conversations">Conversations</a>
  <a href="/marketing">📈 Marketing</a>
  ```

---

## 4. templates/marketing.html — Nav + 76% fix

- Nav links (reordered, add self-link):
  ```html
  <a href="/">📊 Dashboard</a>
  <a href="/conversations">Conversations</a>
  <a href="/marketing">📈 Marketing</a>
  ```
- Line 468: `76%` → `72%`

---

## 5. templates/marketing.html — Redesign

### Sections REMOVED:
- ~~Two separate channel cards~~ (replaced with single table)
- ~~Impact Breakdown~~ (revenue + ROAS charts deleted entirely)
- Remove `<script src="chart.js">` (no longer needed)

### Banner — fix to annual, add sizing dependency note:
```
£140,180 additional annual revenue
"Potential impact — requires product sizing context data"
"10% conversion uplift across paid channels (annual estimate)"
```

### Key Insight — update to mention sizing requirement:
> "Google converts 46% better (3.23x ROAS vs 2.21x) at 30% lower CAC (£40.98 vs £58.45). **Proactive sizing support** at checkout reduces cart abandonment — but requires product size guides and customer body data to deliver personalised answers."

### Channel Performance Comparison — single table (annual figures):

All 24-month figures ÷ 2:

| Metric | Google Ads | Meta Ads | Total |
|--------|-----------|----------|-------|
| Annual Orders | 6,172 | 4,523 | 10,695 |
| Annual Spend | £252,883 | £264,359 | £517,241 |
| Annual Revenue | £816,851 | £584,954 | £1,401,805 |
| ROAS | **3.23x** ↑ | 2.21x | 2.71x |
| CAC | **£40.98** ↑ | £58.45 | £48.35 |

Note beneath table: "Google outperforms Meta by 46% on ROAS and 30% lower acquisition cost"

### 10% Conversion Uplift — keep as two side-by-side items, add sizing note:

Update header text to:
> "⚠️ Uplift is conditional on sizing context data. Claude can answer 'Will this fit?' only with product measurements and customer body data integrated."

Keep Google (£81,685) and Meta (£58,495) cards — figures are already annual.

### Proactive Support Tactics — replace static cards with Live Simulation

Delete the 6 static tactic cards. Replace with an **interactive scripted chat simulation** showing how Claude prevents checkout abandonment:

**Layout:** Split screen
- Left panel: Mock product page (Essential Tee, £45, size selector, "Add to Cart" button)
- Right panel: Animated chat widget

**Scripted simulation steps (auto-play with "Replay" button):**

```
Step 1: Chat bubble appears: "Need help finding your size? 👋"
Step 2: Customer types: "I'm usually between S and M, which should I pick?"
Step 3: Claude responds: "Great question! Our Essential Tee has a relaxed fit
        — the M measures 42" chest. If you're between sizes, I'd recommend M.
        Most customers who sized up loved the fit!"
Step 4: Green tick "Conversion saved ✓" overlays the "Add to Cart" button
Step 5: Stats flash below: "Without Claude: cart abandoned | With Claude: £45 sale"
```

Implementation: Pure CSS/JS animation with `setTimeout` steps — no API call needed.

Include note beneath: "Full capability requires: product measurements, customer body data, and size guide integration"

---

## Files Modified

| File | Changes |
|------|---------|
| `app.py` | Route `/` → metrics.html; `/conversations` → dashboard.html; `/metrics` redirects to `/` |
| `templates/metrics.html` | Full redesign per layout above |
| `templates/dashboard.html` | Title + nav links update |
| `templates/marketing.html` | Single channel table (annual), remove charts, sizing note, live simulation |

---

## Verification

1. Restart Flask: `python3 app.py 5001`
2. `http://localhost:5001/` → loads Dashboard (financial metrics page)
3. `http://localhost:5001/conversations` → loads conversations/tickets
4. `http://localhost:5001/metrics` → redirects to `/`
5. All 3 pages show nav: Dashboard | Conversations | Marketing
6. Dashboard: 4 key metric cards (72%, 5 min, £140k, £61k), routing matrix, compact costs
7. Dashboard: no charts, no tier legend, no data breakdown section
8. Marketing: single channel table with annual figures (not 24-month)
9. Marketing: no revenue/ROAS charts
10. Marketing: live chat simulation plays through automatically with Replay button
11. Marketing: sizing dependency note visible in banner and uplift section
12. Marketing: 72% (not 76%) in tactics
13. Push to GitHub → Vercel deploys
