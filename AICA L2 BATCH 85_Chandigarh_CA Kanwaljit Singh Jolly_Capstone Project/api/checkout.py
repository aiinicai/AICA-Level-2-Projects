"""
Checkout API endpoints for Task Checker
Handles signup requests and email notifications via Supabase Edge Function
"""
import os

import requests
from flask import Blueprint, jsonify, request

checkout_bp = Blueprint('checkout', __name__)

# Supabase Edge Function URL for sending emails
EDGE_FUNCTION_URL = os.getenv(
    'SUPABASE_EDGE_FUNCTION_URL',
    'https://arcdudppbvhijxqqochi.supabase.co/functions/v1/send-signup-email'
)


def send_email_notification(signup_data):
    """Send email notification to admin via Supabase Edge Function using Resend"""

    try:
        # Call Supabase Edge Function
        response = requests.post(
            EDGE_FUNCTION_URL,
            json=signup_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Email sent successfully via Resend. Email ID: {result.get('emailId')}")
            return True
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            print(f"Edge function error ({response.status_code}): {error_data}")

            # Log signup details (email service not configured, but still record the signup)
            print("=" * 60)
            print("SIGNUP REQUEST RECEIVED (Email not sent - Resend not configured)")
            print("=" * 60)
            print(f"   Name: {signup_data['fullName']}")
            print(f"   Email: {signup_data['email']}")
            print(f"   Company: {signup_data['company']}")
            print(f"   Phone: {signup_data.get('phone', 'Not provided')}")
            print(f"   Plan: {signup_data['plan'].upper()}")
            print(f"   Price: ${signup_data['price']}/month" if isinstance(signup_data['price'], (int, float)) else signup_data['price'])
            if signup_data.get('notes'):
                print(f"   Notes: {signup_data['notes']}")
            print("=" * 60)
            print("ACTION REQUIRED: Set RESEND_API_KEY in Supabase Edge Function secrets")
            print("See RESEND_SETUP.md for instructions")
            print("=" * 60)

            # Don't raise exception - allow signup to succeed even if email fails
            return True

    except requests.exceptions.RequestException as e:
        print(f"Network error calling edge function: {e}")

        # Log signup details (network error, but still record the signup)
        print("=" * 60)
        print("SIGNUP REQUEST RECEIVED (Network error)")
        print("=" * 60)
        print(f"   Name: {signup_data['fullName']}")
        print(f"   Email: {signup_data['email']}")
        print(f"   Company: {signup_data['company']}")
        print(f"   Phone: {signup_data.get('phone', 'Not provided')}")
        print(f"   Plan: {signup_data['plan'].upper()}")
        print(f"   Price: ${signup_data['price']}/month" if isinstance(signup_data['price'], (int, float)) else signup_data['price'])
        if signup_data.get('notes'):
            print(f"   Notes: {signup_data['notes']}")
        print("=" * 60)

        # Don't raise exception - allow signup to succeed even if email fails
        return True


@checkout_bp.route('/checkout/notify', methods=['POST'])
def notify_admin():
    """Handle checkout form submission and notify admin"""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['fullName', 'email', 'company', 'plan', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Send email notification (or log if SMTP not configured)
        send_email_notification(data)

        return jsonify({
            'success': True,
            'message': 'Signup request received successfully! We will contact you at the email address provided within 24 hours with your login credentials.'
        }), 200

    except Exception as e:
        import traceback
        print(f"Checkout error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'error': 'Failed to process signup request. Please try again or contact admin@infinitysolutions.app'
        }), 500
