"""
Pretty Fly Support Agent - Flask Web App
Vercel-ready with Claude API integration
"""

from flask import Flask, render_template, request, jsonify
import os
from support_agent import process_ticket, load_data, _data_cache

app = Flask(__name__, static_folder='static', template_folder='templates')

# Initialize data on app startup
try:
    load_data()
except Exception as e:
    print(f"Warning: Could not load CSV data on startup: {e}")
    # Continue - API will work with empty/mock data


def get_sample_tickets():
    """Get sample tickets (real if data loaded, mock otherwise)"""
    load_data()

    orders_df = _data_cache['orders']
    customers_df = _data_cache['customers']

    if orders_df is None or customers_df is None or len(orders_df) == 0:
        # Return mock tickets for demo when no data available
        return [
            {
                'ticket_id': 'demo_001',
                'customer_id': 'cust_demo_001',
                'order_id': 'ord_demo_001',
                'product_id': 'prod_demo_001',
                'subject': 'Help with sizing on the Heritage Hoodie',
                'category': 'sizing_fit',
                'customer_gender': 'Mens',
                'days_since_order': 5
            },
            {
                'ticket_id': 'demo_002',
                'customer_id': 'cust_demo_002',
                'order_id': 'ord_demo_002',
                'product_id': 'prod_demo_002',
                'subject': 'Can I return my order?',
                'category': 'returns_exchanges',
                'customer_gender': 'Womens',
                'days_since_order': 10
            }
        ]

    # Real tickets if data available
    sample_orders = orders_df.head(15)

    tickets = []
    for _, order_row in sample_orders.iterrows():
        customer = customers_df[customers_df['customer_id'] == order_row['customer_id']]
        if not customer.empty:
            customer_row = customer.iloc[0]
            tickets.append({
                'ticket_id': f"ticket_{order_row['order_id']}",
                'customer_id': order_row['customer_id'],
                'order_id': order_row['order_id'],
                'product_id': None,
                'subject': f"Question about order {order_row['order_id']}",
                'category': 'order_status',
                'customer_gender': customer_row.get('gender_segment_affinity', 'Unknown'),
                'days_since_order': 0
            })

    return tickets if tickets else get_sample_tickets()  # Fallback to mock if no real tickets


@app.route('/')
def index():
    """Main demo page"""
    return render_template('index.html')


@app.route('/demo')
def demo():
    """Interactive demo page"""
    try:
        with open('demo.html', 'r') as f:
            return f.read()
    except:
        return "<h1>Demo not found</h1>", 404


@app.route('/api/process_ticket', methods=['POST'])
def process_support_ticket():
    """Process a support ticket via API - real-time Claude response"""
    data = request.json

    try:
        result = process_ticket(
            ticket_id=data.get('ticket_id', 'demo_' + str(__import__('time').time())),
            customer_id=data.get('customer_id', 'unknown'),
            order_id=data.get('order_id', ''),
            product_id=data.get('product_id', ''),
            subject=data.get('subject', ''),
            body=data.get('body', '')
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/sample_tickets', methods=['GET'])
def sample_tickets():
    """Get sample tickets for demo"""
    tickets = get_sample_tickets()
    return jsonify(tickets)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    load_data()
    data_loaded = _data_cache['customers'] is not None
    return jsonify({
        'status': 'healthy',
        'data_loaded': data_loaded
    })


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# Export for Vercel
if __name__ == '__main__':
    # Local development
    app.run(debug=True, port=5000)
