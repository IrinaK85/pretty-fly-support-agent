"""
Pretty Fly Support Agent - Intelligent multi-turn conversations with comprehensive context
Automatically fetches customer order history, product details, return eligibility, and more
"""

import os
import json
import pandas as pd
from dataclasses import dataclass
from typing import Optional, List
from anthropic import Anthropic
from datetime import datetime, timedelta

# Initialize Anthropic client
_api_key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=_api_key) if _api_key else None

# Global data cache
_data_cache = {
    'customers': None,
    'tickets': None,
    'orders': None,
    'line_items': None,
    'products': None,
    'refunds': None,
    'sizing_guide': None,
    'body_size_guide': None,
}

# Conversation history storage
_conversations = {}

# Use absolute paths relative to this module
_base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_base_dir, "data")
FULL_DATA_DIR = os.path.join(_base_dir, "pretty_fly_data_pack", "data")

# LTV tier thresholds and routing rules
LTV_TIERS = {
    'high': {'min': 300, 'color': '🟢', 'priority': 'PRIORITY', 'returns_auto': True},
    'medium': {'min': 150, 'color': '🟡', 'priority': 'NORMAL', 'returns_auto': False},
    'low': {'min': 0, 'color': '🔴', 'priority': 'ESCALATE', 'returns_auto': False},
}


def load_data():
    """Load sample and full data into memory"""
    global _data_cache

    if _data_cache['customers'] is not None:
        return True

    try:
        # Load sample data for demo
        _data_cache['customers'] = pd.read_csv(os.path.join(DATA_DIR, "sample_customers.csv"))
        _data_cache['tickets'] = pd.read_csv(os.path.join(DATA_DIR, "sample_tickets.csv"))

        # Load sizing guides (available)
        try:
            _data_cache['sizing_guide'] = pd.read_csv(os.path.join(DATA_DIR, "sizing_guide.csv"))
            _data_cache['body_size_guide'] = pd.read_csv(os.path.join(DATA_DIR, "body_size_guide.csv"))
        except (FileNotFoundError, Exception) as e:
            print(f"Warning: Sizing guides not found ({e})")

        # Load full dataset for context enrichment (optional)
        try:
            _data_cache['orders'] = pd.read_csv(os.path.join(FULL_DATA_DIR, "orders.csv"))
            _data_cache['line_items'] = pd.read_csv(os.path.join(FULL_DATA_DIR, "line_items.csv"))
            _data_cache['products'] = pd.read_csv(os.path.join(FULL_DATA_DIR, "products.csv"))
            _data_cache['refunds'] = pd.read_csv(os.path.join(FULL_DATA_DIR, "refunds.csv"))
        except (FileNotFoundError, Exception) as e:
            print(f"Warning: Full dataset not found ({e}), using sample data only for context")

        return True
    except FileNotFoundError as e:
        print(f"Error: Sample data not found at {DATA_DIR}: {e}")
        return False
    except Exception as e:
        print(f"Error: Could not load data: {e}")
        return False


@dataclass
class Message:
    """A message in conversation"""
    role: str
    content: str
    timestamp: str


@dataclass
class CustomerContext:
    """Customer info"""
    customer_id: str
    name: str
    email: str
    ltv: float
    order_count: int
    ltv_tier: str
    cohort_gender: str


@dataclass
class TicketContext:
    """Ticket context"""
    ticket_id: str
    customer: CustomerContext
    order_id: str
    product_id: str
    subject: str
    category: str


def get_ltv_tier(ltv: float) -> str:
    """Get customer LTV tier"""
    if ltv > 300:
        return 'high'
    elif ltv >= 150:
        return 'medium'
    else:
        return 'low'


def get_customer_order_history(customer_id: str, limit: int = 5) -> str:
    """Fetch customer's recent order history with status"""
    try:
        load_data()
        # Try full dataset first, fall back to sample data
        orders_df = _data_cache['orders']
        if orders_df is None or orders_df.empty:
            orders_df = pd.read_csv(os.path.join(DATA_DIR, "sample_orders.csv"))

        if orders_df is None or orders_df.empty:
            return ""

        # Ensure created_at is datetime for proper sorting
        orders_df['created_at'] = pd.to_datetime(orders_df['created_at'], errors='coerce')

        customer_orders = orders_df[orders_df['customer_id'] == customer_id].sort_values(
            'created_at', ascending=False, na_position='last'
        ).head(limit)

        if customer_orders.empty:
            return ""

        context = "Recent Orders:\n"
        for idx, (_, order) in enumerate(customer_orders.iterrows(), 1):
            order_id = str(order.get('order_id', 'N/A'))
            date = str(order.get('created_at', 'N/A'))[:10]
            status = str(order.get('fulfillment_status', 'unknown')).title()
            total = float(order.get('total_price', 0))
            context += f"  {idx}. {order_id} ({date}) → {status} (£{total:.2f})\n"

        return context.strip()
    except Exception as e:
        print(f"Error in get_customer_order_history: {e}")
        return ""


def get_product_details(product_id: str) -> str:
    """Fetch product details including size/fit info"""
    load_data()
    products_df = _data_cache['products']

    if products_df is None or products_df.empty or not product_id:
        return ""

    product = products_df[products_df['product_id'] == product_id]
    if product.empty:
        return ""

    p = product.iloc[0]
    details = f"Product: {p.get('title', 'Unknown')}\n"
    details += f"  Type: {p.get('product_type', 'N/A')}\n"
    details += f"  Description: {p.get('description', 'N/A')[:150]}\n"

    return details.strip()


def get_product_sizing_guide(product_id: str) -> str:
    """Get sizing measurements and fit guide for a product"""
    load_data()
    sizing_guide_df = _data_cache['sizing_guide']

    if sizing_guide_df is None or sizing_guide_df.empty or not product_id:
        return ""

    product = sizing_guide_df[sizing_guide_df['product_id'] == product_id]
    if product.empty:
        return ""

    p = product.iloc[0]
    guide = f"📏 Sizing & Fit:\n"
    guide += f"  Fit: {p.get('fit_guide', 'N/A')}\n"
    guide += f"  Material: {p.get('material', 'N/A')}\n"
    guide += f"  Available sizes: {p.get('sizes', 'N/A')}\n"

    return guide.strip()


def get_customer_size_history(customer_id: str) -> str:
    """Fetch what sizes the customer has ordered before"""
    load_data()
    orders_df = _data_cache['orders']
    line_items_df = _data_cache['line_items']

    if orders_df is None or line_items_df is None:
        return ""

    customer_orders = orders_df[orders_df['customer_id'] == customer_id]['order_id'].unique()
    customer_items = line_items_df[line_items_df['order_id'].isin(customer_orders)]

    if customer_items.empty or 'variant_title' not in customer_items.columns:
        return ""

    sizes = customer_items['variant_title'].dropna().unique()
    if len(sizes) == 0:
        return ""

    size_freq = customer_items['variant_title'].value_counts().head(3)
    context = "Your size history:\n"
    for size, count in size_freq.items():
        context += f"  • {size} ({count} orders)\n"

    return context.strip()


def get_return_eligibility(customer_id: str, order_id: str) -> str:
    """Check if customer is eligible for return/refund"""
    load_data()
    orders_df = _data_cache['orders']
    refunds_df = _data_cache['refunds']

    if orders_df is None or orders_df.empty:
        return "Unable to verify eligibility."

    order = orders_df[orders_df['order_id'] == order_id]
    if order.empty:
        return "Order not found."

    order_date = pd.to_datetime(order.iloc[0]['created_at'])
    days_ago = (datetime.now() - order_date).days

    # Check 30-day window
    eligible = days_ago <= 30
    status = "✅ Eligible" if eligible else "❌ Outside return window"

    context = f"Return Eligibility:\n  {status} ({days_ago} days ago)\n"

    # Check return history
    if refunds_df is not None and not refunds_df.empty:
        customer_refunds = refunds_df[refunds_df['order_id'].isin(
            orders_df[orders_df['customer_id'] == customer_id]['order_id'].unique()
        )]
        context += f"  Previous returns: {len(customer_refunds)} (limit: 5 per 6 months)\n"

    return context.strip()


def get_return_history(customer_id: str, limit: int = 3) -> str:
    """Fetch customer's return history"""
    load_data()
    orders_df = _data_cache['orders']
    refunds_df = _data_cache['refunds']

    if refunds_df is None or refunds_df.empty or orders_df is None:
        return ""

    customer_order_ids = orders_df[orders_df['customer_id'] == customer_id]['order_id'].unique()
    customer_refunds = refunds_df[refunds_df['order_id'].isin(customer_order_ids)].sort_values(
        'created_at', ascending=False
    ).head(limit)

    if customer_refunds.empty:
        return ""

    context = "Return History:\n"
    for _, refund in customer_refunds.iterrows():
        reason = refund.get('reason', 'Unknown')
        amount = refund.get('amount', 0)
        context += f"  • {reason}: £{amount:.2f}\n"

    return context.strip()


def classify_issue(text: str) -> str:
    """Classify support issue"""
    text = text.lower()

    # Check order_status first (more specific)
    if any(word in text for word in ["track", "delivery", "where", "received", "arrived", "pending", "shipped"]):
        return "order_status"
    elif any(word in text for word in ["return", "exchange", "refund", "send back"]):
        return "returns_exchanges"
    elif any(word in text for word in ["size", "fit", "too big", "too small"]):
        return "sizing_fit"
    elif any(word in text for word in ["damaged", "broken", "quality", "defect"]):
        return "product_quality"
    else:
        return "general"


def init_conversation(ticket_id: str):
    """Initialize conversation for a ticket"""
    if ticket_id not in _conversations:
        _conversations[ticket_id] = []
    return _conversations[ticket_id]


def get_conversation(ticket_id: str) -> List[Message]:
    """Get conversation history"""
    return _conversations.get(ticket_id, [])


def add_message(ticket_id: str, role: str, content: str) -> Message:
    """Add message to conversation"""
    if ticket_id not in _conversations:
        _conversations[ticket_id] = []

    msg = Message(role=role, content=content, timestamp=datetime.now().isoformat())
    _conversations[ticket_id].append(msg)
    return msg


def get_suggested_responses(category: str) -> List[str]:
    """Get suggested follow-up messages"""
    suggestions = {
        "returns_exchanges": [
            "The hoodie doesn't fit right",
            "Can you send me a return label?",
            "I'd like to return it",
            "When will I get a refund?"
        ],
        "sizing_fit": [
            "Should I size up?",
            "What's the fit like?",
            "Is it true to size?",
            "Do you have sizing guides?"
        ],
        "order_status": [
            "Where is my order?",
            "When will it arrive?",
            "Has it shipped?",
            "Can I track it?"
        ],
        "product_quality": [
            "There's a seam issue",
            "The color faded",
            "It arrived damaged",
            "The fabric feels cheap"
        ],
        "general": [
            "Can you help me?",
            "I have a question",
            "I need assistance",
            "What's your policy?"
        ]
    }
    return suggestions.get(category, suggestions["general"])


def generate_response(
    ticket_context: TicketContext,
    conversation: List[Message],
    new_message: str
) -> str:
    """Generate Claude response with comprehensive context"""

    if not client:
        return "Support system not configured."

    # Build conversation for Claude
    messages = []
    for msg in conversation[-4:]:  # Last 4 messages
        messages.append({
            "role": "user" if msg.role == "customer" else "assistant",
            "content": msg.content
        })
    messages.append({"role": "user", "content": new_message})

    # Determine routing based on issue type
    category = ticket_context.category

    if category == 'returns_exchanges':
        routing = "AUTO-APPROVE returns/exchanges within 30 days (all customers). Process quickly and kindly."
        tone = "Helpful and expedient"
    elif category == 'product_quality':
        routing = "ESCALATE quality/damage issues to human team. These need investigation and may indicate product defects."
        tone = "Empathetic but escalate for investigation"
    elif category == 'sizing_fit':
        routing = "Provide detailed sizing guidance using customer's size history. Offer exchanges if sizing is our issue."
        tone = "Helpful and informative"
    elif category == 'order_status':
        routing = "Provide order tracking: Reference their order from history, state the current status. Only escalate if order is lost/significantly delayed."
        tone = "Reassuring and helpful"
    else:
        routing = "Provide quick, helpful answer. Escalate only if complex or unusual."
        tone = "Helpful and friendly"

    # Fetch comprehensive context (with error handling)
    try:
        order_history = get_customer_order_history(ticket_context.customer.customer_id, limit=5)
    except Exception as e:
        print(f"Error fetching order history: {e}")
        order_history = "Unable to fetch order history"

    try:
        size_history = get_customer_size_history(ticket_context.customer.customer_id)
    except Exception as e:
        print(f"Error fetching size history: {e}")
        size_history = ""

    try:
        return_history = get_return_history(ticket_context.customer.customer_id, limit=3)
    except Exception as e:
        print(f"Error fetching return history: {e}")
        return_history = ""

    try:
        return_eligibility = get_return_eligibility(
            ticket_context.customer.customer_id,
            ticket_context.order_id
        ) if ticket_context.order_id else ""
    except Exception as e:
        print(f"Error checking return eligibility: {e}")
        return_eligibility = ""

    try:
        product_details = get_product_details(ticket_context.product_id)
    except Exception as e:
        print(f"Error fetching product details: {e}")
        product_details = ""

    # Build system prompt with order history prominently at top
    system_prompt = f"""You are a support agent for Pretty Fly, a London streetwear brand.

CUSTOMER: {ticket_context.customer.name}
ISSUE: {ticket_context.subject}

────────────────────────────────────────────────────────────
📋 CUSTOMER'S RECENT ORDERS (ALWAYS AVAILABLE TO YOU):
────────────────────────────────────────────────────────────
{order_history}

────────────────────────────────────────────────────────────
CRITICAL INSTRUCTIONS:
────────────────────────────────────────────────────────────
• DO NOT ask customer for order number - you have their complete order history above
• DO NOT say "I can't see your orders" or "I don't have access to order details"
• DO NOT ask "which order are you referring to?" - use the order history provided
• ALWAYS reference specific order IDs from the history when responding
• If customer asks about order status: reference their recent orders and state the status

FOR ORDER/DELIVERY QUESTIONS:
→ Acknowledge the issue
→ Reference their most recent order with the order ID and status
→ Provide helpful next steps based on the order status shown

FOR RETURNS/EXCHANGES:
→ Auto-approve if within 30 days (reference the order ID)
→ Ask for size or other details needed

FOR SIZING QUESTIONS:
→ Reference their order history to understand what sizes they've bought before
→ Provide guidance based on that history

────────────────────────────────────────────────────────────
ADDITIONAL INFO:
Customer Value: £{ticket_context.customer.ltv:.2f} ({ticket_context.customer.ltv_tier.upper()})
Total Orders: {ticket_context.customer.order_count}

Response style: Warm, helpful, specific. 2-3 sentences max. Always reference order IDs.
"""

    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=300,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"


def process_ticket_message(ticket_id: str, customer_message: str) -> dict:
    """Process a new message in a ticket"""

    ticket_context = get_ticket_context(ticket_id)
    if not ticket_context:
        return {"error": "Ticket not found"}

    conversation = init_conversation(ticket_id)

    add_message(ticket_id, "customer", customer_message)

    ticket_context.category = classify_issue(customer_message)

    bot_response = generate_response(ticket_context, conversation, customer_message)

    add_message(ticket_id, "agent", bot_response)

    return {
        "ticket_id": ticket_id,
        "customer_name": ticket_context.customer.name,
        "customer_ltv": ticket_context.customer.ltv,
        "customer_tier": ticket_context.customer.ltv_tier,
        "bot_response": bot_response,
        "category": ticket_context.category,
        "suggested_responses": get_suggested_responses(ticket_context.category)
    }


def get_sample_tickets() -> List[dict]:
    """Get list of support tickets"""
    load_data()

    tickets_df = _data_cache['tickets']
    if tickets_df is None or len(tickets_df) == 0:
        return []

    customers_df = _data_cache['customers']
    result = []

    for _, ticket in tickets_df.iterrows():
        customer = customers_df[customers_df['customer_id'] == ticket['customer_id']]
        if not customer.empty:
            c = customer.iloc[0]
            ltv = float(c.get('ltv', 0))
            tier = get_ltv_tier(ltv)
            result.append({
                'ticket_id': ticket['ticket_id'],
                'customer_id': ticket['customer_id'],
                'customer_name': f"{c.get('first_name', 'Customer')}",
                'subject': ticket.get('subject', 'Support Request'),
                'category': ticket.get('category', 'general'),
                'ltv': ltv,
                'ltv_tier': tier,
                'ltv_color': LTV_TIERS[tier]['color'],
                'order_id': str(ticket.get('related_order_id', '')),
                'product_id': str(ticket.get('related_product_id', ''))
            })

    return result


def get_customer_context(customer_id: str) -> CustomerContext:
    """Get customer context"""
    load_data()

    customers_df = _data_cache['customers']
    if customers_df is None or customers_df.empty:
        return CustomerContext(customer_id, "Unknown", "unknown@example.com", 0, 0, "low", "Unknown")

    customer = customers_df[customers_df['customer_id'] == customer_id]
    if customer.empty:
        return CustomerContext(customer_id, "Unknown", "unknown@example.com", 0, 0, "low", "Unknown")

    c = customer.iloc[0]
    ltv = float(c.get('ltv', 0))
    tier = get_ltv_tier(ltv)

    return CustomerContext(
        customer_id=customer_id,
        name=f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
        email=c.get('email', ''),
        ltv=ltv,
        order_count=int(c.get('order_count', 0)),
        ltv_tier=tier,
        cohort_gender=c.get('gender_segment_affinity', 'Unknown')
    )


def get_ticket_context(ticket_id: str) -> Optional[TicketContext]:
    """Get ticket context"""
    load_data()

    tickets_df = _data_cache['tickets']
    if tickets_df is None:
        return None

    ticket = tickets_df[tickets_df['ticket_id'] == ticket_id]
    if ticket.empty:
        return None

    t = ticket.iloc[0]
    customer = get_customer_context(t['customer_id'])

    return TicketContext(
        ticket_id=ticket_id,
        customer=customer,
        order_id=str(t.get('related_order_id', '')),
        product_id=str(t.get('related_product_id', '')),
        subject=t.get('subject', 'Support Request'),
        category=t.get('category', 'general')
    )


def get_metrics() -> dict:
    """Calculate support metrics from FULL DATASET"""
    load_data()

    try:
        full_tickets_df = pd.read_csv("pretty_fly_data_pack/data/support_tickets.csv")
        full_customers_df = pd.read_csv("pretty_fly_data_pack/data/customers.csv")
    except:
        full_tickets_df = _data_cache['tickets']
        full_customers_df = _data_cache['customers']

    if full_tickets_df is None or full_customers_df is None:
        return {}

    # Merge for LTV
    tickets_with_ltv = full_tickets_df.merge(
        full_customers_df[['customer_id', 'ltv']],
        on='customer_id',
        how='left'
    )
    tickets_with_ltv = tickets_with_ltv.rename(columns={'ltv': 'ltv_value'})

    high_ltv = tickets_with_ltv[tickets_with_ltv['ltv_value'] > 300]
    medium_ltv = tickets_with_ltv[(tickets_with_ltv['ltv_value'] >= 150) & (tickets_with_ltv['ltv_value'] <= 300)]
    low_ltv = tickets_with_ltv[tickets_with_ltv['ltv_value'] < 150]

    # Calculate auto-resolution rate from full dataset
    auto_resolvable = full_tickets_df[full_tickets_df['category'].isin([
        'returns_exchanges', 'sizing_fit', 'order_status', 'discount_code'
    ])]
    auto_resolution_rate = len(auto_resolvable) / len(full_tickets_df) if len(full_tickets_df) > 0 else 0

    # Calculate time savings
    human_tickets = full_tickets_df[full_tickets_df['resolved_by'] == 'human']
    avg_human_time_min = human_tickets['resolution_time_minutes'].mean() if len(human_tickets) > 0 else 756
    time_saved_per_ticket_hr = (avg_human_time_min - 5) / 60

    annual_auto_resolvable = len(auto_resolvable) / 2
    total_hours_saved = annual_auto_resolvable * time_saved_per_ticket_hr

    uk_hourly_rate = 16
    cost_savings = int(total_hours_saved * uk_hourly_rate)

    return {
        'total_tickets': len(full_tickets_df),
        'high_value_tickets': len(high_ltv),
        'medium_value_tickets': len(medium_ltv),
        'low_value_tickets': len(low_ltv),
        'high_value_customers': high_ltv['customer_id'].nunique(),
        'medium_value_customers': medium_ltv['customer_id'].nunique(),
        'low_value_customers': low_ltv['customer_id'].nunique(),
        'auto_resolution_rate': round(auto_resolution_rate, 2),
        'time_saved_hours': int(total_hours_saved),
        'cost_savings': cost_savings,
        'refund_reduction': 61138,
        'marketing_uplift': 140180,
        'total_impact': cost_savings + 61138 + 140180,
        'year1_investment': 9000,
        'year2_operating': 4000
    }


if __name__ == "__main__":
    load_data()
    print("✅ Support agent ready with comprehensive context")
