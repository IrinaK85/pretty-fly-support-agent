"""
Pretty Fly Support Agent - Flask Web App
Multi-turn support conversations with Claude API
"""

from flask import Flask, render_template, request, jsonify
import os
from support_agent import (
    load_data, get_sample_tickets, get_ticket_context,
    get_conversation, process_ticket_message, get_suggested_responses,
    get_metrics, LTV_TIERS
)

app = Flask(__name__, static_folder='static', template_folder='templates')

# Load data on startup
try:
    load_data()
except Exception as e:
    print(f"Warning: Could not load data: {e}")


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/metrics')
def metrics_page():
    """Metrics dashboard page"""
    return render_template('metrics.html')


@app.route('/api/tickets', methods=['GET'])
def list_tickets():
    """Get list of support tickets"""
    try:
        tickets = get_sample_tickets()
        return jsonify(tickets)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/ticket/<ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    """Get ticket details and conversation"""
    try:
        context = get_ticket_context(ticket_id)
        if not context:
            return jsonify({'error': 'Ticket not found'}), 404

        conversation = get_conversation(ticket_id)
        suggested = get_suggested_responses(context.category)
        tier_info = LTV_TIERS[context.customer.ltv_tier]

        return jsonify({
            'ticket_id': ticket_id,
            'customer_id': context.customer.customer_id,
            'customer_name': context.customer.name,
            'customer_email': context.customer.email,
            'customer_ltv': context.customer.ltv,
            'customer_ltv_tier': context.customer.ltv_tier,
            'customer_ltv_color': tier_info['color'],
            'customer_order_count': context.customer.order_count,
            'subject': context.subject,
            'category': context.category,
            'order_id': context.order_id,
            'product_id': context.product_id,
            'conversation': [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp
                }
                for msg in conversation
            ],
            'suggested_responses': suggested
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/ticket/<ticket_id>/message', methods=['POST'])
def add_message(ticket_id):
    """Process a new message in a ticket"""
    try:
        data = request.json
        customer_message = data.get('message', '')

        if not customer_message:
            return jsonify({'error': 'Message required'}), 400

        result = process_ticket_message(ticket_id, customer_message)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/metrics', methods=['GET'])
def get_metrics_data():
    """Get support metrics"""
    try:
        metrics = get_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy'})


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
