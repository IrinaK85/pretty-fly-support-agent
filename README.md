# Pretty Fly Support Agent

AI-powered support ticket processor for Pretty Fly streetwear. Uses Claude API to generate contextual, customer-value-aware support responses in real-time.

## Features

- **Real-time Claude API Integration**: Generates support responses using live Claude inference
- **Customer Context Analysis**: Assembles lifetime value, cohort, repeat rate, and purchase history
- **Smart Automation**: Routes tickets based on customer value and issue category
- **CSV-based Data**: Loads transaction data into memory on startup (Vercel-compatible)
- **Web Interface**: Demo app with ticket processing UI

## Tech Stack

- **Backend**: Flask (Python)
- **AI**: Anthropic Claude API (Claude Opus 4.8)
- **Data**: Pandas (in-memory CSV loading)
- **Hosting**: Vercel

## Setup

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export ANTHROPIC_API_KEY="sk-..."
   ```

3. **Run the app**:
   ```bash
   python app.py
   ```

   Visit `http://localhost:5000` to see the demo interface.

### Vercel Deployment

1. **Connect GitHub repo to Vercel**:
   - Push to GitHub
   - Import project in Vercel

2. **Set environment variables in Vercel**:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key

3. **Deploy**:
   ```bash
   vercel --prod
   ```

The app will be live at your Vercel URL.

## API Endpoints

### POST /api/process_ticket

Process a support ticket with Claude-generated response.

**Request**:
```json
{
  "ticket_id": "ticket_123",
  "customer_id": "cust_001",
  "order_id": "ord_042",
  "product_id": "prod_007",
  "subject": "Help with sizing",
  "body": "The hoodie feels too tight..."
}
```

**Response**:
```json
{
  "ticket_id": "ticket_123",
  "category": "sizing_fit",
  "customer_cohort": "Mens (2024-06)",
  "customer_ltv": 450.50,
  "automation_decision": "provide_guidance",
  "automation_reasoning": "Provide product-specific sizing guidance.",
  "priority": "normal",
  "agent_response": "Thanks for reaching out! The Heritage Hoodie fits true to size..."
}
```

### GET /api/sample_tickets

Get sample tickets for demo purposes.

### GET /api/health

Health check endpoint.

## Data Loading

The app loads Pretty Fly transaction data from CSV files:
- `customers.csv` - Customer profiles and cohorts
- `orders.csv` - Order history
- `line_items.csv` - Order line items
- `variants.csv` - Product variants
- `products.csv` - Product catalog
- `refunds.csv` - Return/refund history

Data is loaded into memory on the first API request.

## Architecture

```
app.py                 - Flask application & routes
support_agent.py       - Claude integration & ticket processing logic
templates/             - HTML templates for demo UI
pretty_fly_data_pack/  - Transaction data (CSV files)
```

## How It Works

1. **Ticket Classification**: Categorizes support request (returns, sizing, order status, etc.)
2. **Context Assembly**: Pulls customer lifetime value, cohort, order history
3. **Automation Decision**: Decides routing based on customer value + category
4. **Claude Generation**: Sends context to Claude API for real-time response generation
5. **Response Return**: Returns ticket decision + Claude-generated response

Example flow:
- Customer: "Can I return my hoodie?"
- Classification: `returns_exchanges`
- Context: High-value customer (LTV £650), within 30-day window
- Decision: `auto_process_return`
- Response: Claude generates warm, action-oriented reply

## Testing

```bash
# Local test
python support_agent.py
```

This will process a sample ticket and print the result.

## Environment Variables

- `ANTHROPIC_API_KEY`: Required. Your Anthropic API key.

## Notes

- All timestamps in UTC; convert to Europe/London for local analysis
- Currency is GBP
- Dataset covers June 2024 - May 2026
- Data loads into memory on startup (~50MB for full transaction history)

---

Built for Wayflyer × Fin AI Hackathon 2026
