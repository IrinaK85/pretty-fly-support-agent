"""
Pretty Fly Support Agent - CSV-based, Claude-powered
Real-time support ticket processing with customer context
"""

import os
import json
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Optional
from anthropic import Anthropic
from datetime import datetime

# Initialize Anthropic client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Global data cache (loaded once on startup)
_data_cache = {
    'customers': None,
    'orders': None,
    'line_items': None,
    'variants': None,
    'products': None,
    'refunds': None,
}

DATA_DIR = "pretty_fly_data_pack/data"


def load_data():
    """Load all CSV data into memory (optional for Vercel deployment)"""
    global _data_cache

    if _data_cache['customers'] is not None:
        return  # Already loaded

    try:
        _data_cache['customers'] = pd.read_csv(f"{DATA_DIR}/customers.csv")
        _data_cache['orders'] = pd.read_csv(f"{DATA_DIR}/orders.csv", parse_dates=['created_at'])
        _data_cache['line_items'] = pd.read_csv(f"{DATA_DIR}/line_items.csv")
        _data_cache['variants'] = pd.read_csv(f"{DATA_DIR}/variants.csv")
        _data_cache['products'] = pd.read_csv(f"{DATA_DIR}/products.csv")
        _data_cache['refunds'] = pd.read_csv(f"{DATA_DIR}/refunds.csv")
        return True
    except FileNotFoundError:
        print(f"Warning: CSV data files not found at {DATA_DIR}. Running with mock data.")
        # Create empty DataFrames so API still works
        _data_cache['customers'] = pd.DataFrame(columns=['customer_id', 'created_at', 'gender_segment_affinity'])
        _data_cache['orders'] = pd.DataFrame(columns=['order_id', 'customer_id', 'created_at', 'total_price', 'financial_status', 'fulfillment_status'])
        _data_cache['refunds'] = pd.DataFrame(columns=['order_id', 'refund_id'])
        _data_cache['products'] = pd.DataFrame(columns=['product_id', 'title', 'product_type', 'gender_segment'])
        return False
    except Exception as e:
        print(f"Warning: Could not load CSV data: {e}")
        return False


@dataclass
class CustomerContext:
    """Context assembled for a customer"""
    customer_id: str
    cohort_month: str
    cohort_gender: str
    lifetime_value: float
    repeat_rate: float
    total_orders: int
    refund_rate: float
    recent_orders: list


@dataclass
class TicketContext:
    """Full context for a support ticket"""
    ticket_id: str
    category: str
    subject: str
    customer_context: CustomerContext
    order_info: dict
    product_info: dict
    eligibility: dict


def classify_ticket(subject: str, body: str) -> str:
    """Classify support ticket into category using keywords"""
    text = (subject + " " + body).lower()

    if any(word in text for word in ["return", "exchange", "send back", "refund"]):
        return "returns_exchanges"
    elif any(word in text for word in ["size", "fit", "too big", "too small", "length"]):
        return "sizing_fit"
    elif any(word in text for word in ["code", "discount", "promo", "coupon"]):
        return "discount_code"
    elif any(word in text for word in ["track", "order", "arrive", "delivery", "where"]):
        return "order_status"
    elif any(word in text for word in ["quality", "broken", "torn", "fade", "defect"]):
        return "product_quality"
    elif any(word in text for word in ["restock", "drop", "available", "when"]):
        return "drop_restock"
    else:
        return "other"


def get_customer_context(customer_id: str) -> Optional[CustomerContext]:
    """Assemble customer context from in-memory data"""
    load_data()

    customers_df = _data_cache['customers']
    orders_df = _data_cache['orders']
    refunds_df = _data_cache['refunds']

    # Get customer info
    customer = customers_df[customers_df['customer_id'] == customer_id]
    if customer.empty:
        # Return mock context if no data (for Vercel deployment without CSV files)
        return CustomerContext(
            customer_id=customer_id,
            cohort_month="unknown",
            cohort_gender="Unknown",
            lifetime_value=0,
            repeat_rate=0,
            total_orders=0,
            refund_rate=0,
            recent_orders=[]
        )

    customer_row = customer.iloc[0]
    customer_id = customer_row['customer_id']
    cohort_month = str(customer_row['created_at'][:7])
    cohort_gender = customer_row.get('gender_segment_affinity', 'Unknown')

    # Get customer orders
    customer_orders = orders_df[orders_df['customer_id'] == customer_id]
    if customer_orders.empty:
        # Return basic context if no orders
        return CustomerContext(
            customer_id=customer_id,
            cohort_month=cohort_month,
            cohort_gender=cohort_gender,
            lifetime_value=0,
            repeat_rate=0,
            total_orders=0,
            refund_rate=0,
            recent_orders=[]
        )

    total_orders = len(customer_orders)
    lifetime_value = customer_orders['total_price'].sum()

    # Calculate repeat rate (orders per month)
    date_range_days = (customer_orders['created_at'].max() - customer_orders['created_at'].min()).days + 1
    repeat_rate_monthly = (total_orders / max(date_range_days, 1)) * 30

    # Calculate refund rate
    refund_orders = refunds_df[refunds_df['order_id'].isin(customer_orders['order_id'])]
    refund_rate = (len(refund_orders.drop_duplicates('order_id')) / total_orders * 100) if total_orders > 0 else 0

    # Get recent orders
    recent_orders = []
    for _, order_row in customer_orders.nlargest(3, 'created_at').iterrows():
        recent_orders.append({
            "order_id": order_row['order_id'],
            "date": str(order_row['created_at']),
            "total": float(order_row['total_price']),
            "products": "N/A"  # Would need line_items join
        })

    return CustomerContext(
        customer_id=customer_id,
        cohort_month=cohort_month,
        cohort_gender=cohort_gender,
        lifetime_value=float(lifetime_value),
        repeat_rate=float(repeat_rate_monthly),
        total_orders=total_orders,
        refund_rate=float(refund_rate),
        recent_orders=recent_orders
    )


def get_order_info(order_id: str) -> dict:
    """Get order details"""
    load_data()

    orders_df = _data_cache['orders']
    order = orders_df[orders_df['order_id'] == order_id]

    if order.empty:
        return {}

    order_row = order.iloc[0]
    days_since = (datetime.fromisoformat('2026-06-01') - pd.Timestamp(order_row['created_at'])).days

    return {
        "order_id": order_row['order_id'],
        "created_at": str(order_row['created_at']),
        "total_price": float(order_row['total_price']),
        "financial_status": order_row.get('financial_status', 'Unknown'),
        "fulfillment_status": order_row.get('fulfillment_status', 'Unknown'),
        "days_since_order": days_since
    }


def get_product_info(product_id: str) -> dict:
    """Get product details"""
    load_data()

    products_df = _data_cache['products']
    product = products_df[products_df['product_id'] == product_id]

    if product.empty:
        return {}

    product_row = product.iloc[0]

    return {
        "product_id": product_row['product_id'],
        "title": product_row.get('title', 'Unknown'),
        "product_type": product_row.get('product_type', 'Unknown'),
        "gender_segment": product_row.get('gender_segment', 'Unknown'),
        "size_related_returns": 0  # Simplified for now
    }


def assess_return_eligibility(order_info: dict, product_info: dict) -> dict:
    """Assess if a return is eligible"""
    days_since = order_info.get("days_since_order", 999)

    return {
        "eligible": days_since <= 30,
        "days_since_order": days_since,
        "reason": "Within 30-day window" if days_since <= 30 else f"Outside 30-day window ({days_since} days ago)"
    }


def make_automation_decision(
    category: str,
    customer_context: CustomerContext,
    order_info: dict,
    eligibility: dict
) -> dict:
    """
    Decide whether to auto-resolve, escalate, or ask for verification
    Based on category AND customer value
    """
    ltv = customer_context.lifetime_value
    is_high_value = ltv > 200

    decision = {
        "action": "escalate_to_human",
        "reasoning": "",
        "priority": "normal"
    }

    if category == "returns_exchanges":
        if eligibility.get("eligible") and is_high_value:
            decision["action"] = "auto_process_return"
            decision["reasoning"] = f"High-value customer ({customer_context.cohort_gender} cohort, LTV £{ltv:.0f}). Within return window."
            decision["priority"] = "high"
        elif eligibility.get("eligible"):
            decision["action"] = "verify_then_process"
            decision["reasoning"] = "Eligible for return. Verify reason before processing."
            decision["priority"] = "normal"
        else:
            decision["action"] = "escalate_to_human"
            decision["reasoning"] = f"Outside 30-day window ({eligibility.get('days_since_order')} days). Needs discretion."
            decision["priority"] = "normal"

    elif category == "discount_code":
        decision["action"] = "verify_and_apply"
        decision["reasoning"] = "Check code validity; apply if valid."
        decision["priority"] = "high" if is_high_value else "normal"

    elif category == "sizing_fit":
        decision["action"] = "provide_guidance"
        decision["reasoning"] = f"Provide product-specific sizing guidance."
        decision["priority"] = "high" if is_high_value else "normal"

    elif category == "order_status":
        days_since = order_info.get("days_since_order", 0)
        if days_since > 10:
            decision["action"] = "investigate_and_respond"
            decision["reasoning"] = f"Order {days_since} days old. Investigate tracking."
            decision["priority"] = "high"
        else:
            decision["action"] = "provide_tracking"
            decision["reasoning"] = "Provide tracking info."
            decision["priority"] = "normal"

    elif category == "product_quality":
        decision["action"] = "escalate_to_human"
        decision["reasoning"] = "Quality complaints need human judgment."
        decision["priority"] = "high"

    else:
        decision["action"] = "escalate_to_human"
        decision["reasoning"] = "Unclear issue. Route to human agent."
        decision["priority"] = "normal"

    return decision


def generate_response(
    ticket_subject: str,
    ticket_body: str,
    category: str,
    context: TicketContext,
    automation_decision: dict
) -> str:
    """Use Claude to generate a support response in real-time"""

    # Build context prompt
    context_prompt = f"""
Customer Context:
- Cohort: {context.customer_context.cohort_gender} ({context.customer_context.cohort_month})
- Lifetime Value: £{context.customer_context.lifetime_value:.2f}
- Total Orders: {context.customer_context.total_orders}
- Repeat Rate: {context.customer_context.repeat_rate:.2f} orders/month
- Recent Orders: {json.dumps(context.customer_context.recent_orders[:2], default=str)}

Order Context (if applicable):
- Days Since Order: {context.order_info.get('days_since_order', 'N/A')}
- Status: {context.order_info.get('fulfillment_status', 'N/A')}
- Price: £{context.order_info.get('total_price', 'N/A')}

Product: {context.product_info.get('title', 'Unknown')}
Category: {category}

Automation Plan: {automation_decision['action']}
Reasoning: {automation_decision['reasoning']}

Generate a friendly, helpful response that:
1. Acknowledges the customer's issue
2. Takes action appropriate to the category and customer value
3. Sets clear expectations
4. Reflects the automation decision

Keep response to 2-3 sentences. Be warm but concise. Sign as Pretty Fly Support.
"""

    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=300,
            system="You are a support agent for Pretty Fly, a London streetwear brand. Be helpful, friendly, and action-oriented.",
            messages=[
                {
                    "role": "user",
                    "content": f"Ticket: {ticket_subject}\n\nCustomer message: {ticket_body}\n\n{context_prompt}"
                }
            ]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error generating response: {str(e)}"


def process_ticket(
    ticket_id: str,
    customer_id: str,
    order_id: str,
    product_id: str,
    subject: str,
    body: str
) -> dict:
    """Process a support ticket end-to-end"""

    # 1. Classify
    category = classify_ticket(subject, body)

    # 2. Assemble context
    customer_context = get_customer_context(customer_id)
    if not customer_context:
        return {
            "error": "Customer not found",
            "ticket_id": ticket_id
        }

    order_info = get_order_info(order_id) if order_id else {}
    product_info = get_product_info(product_id) if product_id else {}
    eligibility = assess_return_eligibility(order_info, product_info) if order_id and product_id else {}

    context = TicketContext(
        ticket_id=ticket_id,
        category=category,
        subject=subject,
        customer_context=customer_context,
        order_info=order_info,
        product_info=product_info,
        eligibility=eligibility
    )

    # 3. Make automation decision
    automation_decision = make_automation_decision(
        category,
        customer_context,
        order_info,
        eligibility
    )

    # 4. Generate response using Claude API (real-time)
    response = generate_response(subject, body, category, context, automation_decision)

    # 5. Assemble result
    return {
        "ticket_id": ticket_id,
        "category": category,
        "customer_cohort": f"{customer_context.cohort_gender} ({customer_context.cohort_month})",
        "customer_ltv": customer_context.lifetime_value,
        "automation_decision": automation_decision["action"],
        "automation_reasoning": automation_decision["reasoning"],
        "priority": automation_decision["priority"],
        "agent_response": response
    }


if __name__ == "__main__":
    # Load data on startup
    load_data()
    print("Data loaded successfully")
