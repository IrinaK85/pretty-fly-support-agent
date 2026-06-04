"""
Pretty Fly Support Agent - Multi-turn conversations with Claude
Real-time support ticket processing with conversation history
"""

import os
import json
import pandas as pd
from dataclasses import dataclass
from typing import Optional, List
from anthropic import Anthropic
from datetime import datetime

# Initialize Anthropic client
_api_key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=_api_key) if _api_key else None

# Global data cache
_data_cache = {
    'customers': None,
    'orders': None,
    'tickets': None,
}

# Conversation history storage (in-memory for demo)
_conversations = {}

DATA_DIR = "data"


def load_data():
    """Load sample data into memory"""
    global _data_cache

    if _data_cache['customers'] is not None:
        return True

    try:
        _data_cache['customers'] = pd.read_csv(f"{DATA_DIR}/sample_customers.csv")
        _data_cache['orders'] = pd.read_csv(f"{DATA_DIR}/sample_orders.csv", parse_dates=['created_at'])
        _data_cache['tickets'] = pd.read_csv(f"{DATA_DIR}/sample_tickets.csv")
        return True
    except FileNotFoundError:
        print(f"Warning: Sample data not found at {DATA_DIR}")
        return False
    except Exception as e:
        print(f"Warning: Could not load data: {e}")
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


def get_sample_tickets() -> List[dict]:
    """Get list of support tickets"""
    load_data()

    tickets_df = _data_cache['tickets']
    if tickets_df is None or len(tickets_df) == 0:
        return []

    customers_df = _data_cache['customers']
    result = []

    for _, ticket in tickets_df.head(15).iterrows():
        customer = customers_df[customers_df['customer_id'] == ticket['customer_id']]
        if not customer.empty:
            c = customer.iloc[0]
            result.append({
                'ticket_id': ticket['ticket_id'],
                'customer_id': ticket['customer_id'],
                'customer_name': f"{c.get('first_name', 'Customer')}",
                'subject': ticket.get('subject', 'Support Request'),
                'category': ticket.get('category', 'general'),
                'ltv': float(c.get('ltv', 0)),
                'order_id': str(ticket.get('related_order_id', '')),
                'product_id': str(ticket.get('related_product_id', ''))
            })

    return result


def get_customer_context(customer_id: str) -> CustomerContext:
    """Get customer context"""
    load_data()

    customers_df = _data_cache['customers']
    if customers_df is None or customers_df.empty:
        return CustomerContext(customer_id, "Unknown", "unknown@example.com", 0, 0, "Unknown")

    customer = customers_df[customers_df['customer_id'] == customer_id]
    if customer.empty:
        return CustomerContext(customer_id, "Unknown", "unknown@example.com", 0, 0, "Unknown")

    c = customer.iloc[0]
    return CustomerContext(
        customer_id=customer_id,
        name=f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
        email=c.get('email', ''),
        ltv=float(c.get('ltv', 0)),
        order_count=int(c.get('order_count', 0)),
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


def classify_issue(text: str) -> str:
    """Classify support issue"""
    text = text.lower()

    if any(word in text for word in ["return", "exchange", "refund", "send back"]):
        return "returns_exchanges"
    elif any(word in text for word in ["size", "fit", "too big", "too small"]):
        return "sizing_fit"
    elif any(word in text for word in ["track", "delivery", "where", "arrived"]):
        return "order_status"
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
    """Generate Claude response"""

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

    # System prompt with context
    system_prompt = f"""You are a helpful support agent for Pretty Fly, a London streetwear brand.

CUSTOMER:
- Name: {ticket_context.customer.name}
- Lifetime Value: £{ticket_context.customer.ltv:.2f}
- Orders: {ticket_context.customer.order_count}
- Gender Segment: {ticket_context.customer.cohort_gender}

TICKET:
- Subject: {ticket_context.subject}
- Category: {ticket_context.category}

Be friendly, concise (2-3 sentences), and action-oriented. For high-value customers (LTV > £200), prioritize resolution."""

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
        "bot_response": bot_response,
        "category": ticket_context.category,
        "suggested_responses": get_suggested_responses(ticket_context.category)
    }


if __name__ == "__main__":
    load_data()
    print("✅ Support agent ready")
