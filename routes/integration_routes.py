from flask import Blueprint, request, jsonify
import json
from models import CustobarIntegration, User, Customer, Transaction, db, Event
import requests
import time
from datetime import datetime

integration_bp = Blueprint('integration_bp', __name__)

# Add Custobar integration
from flask_jwt_extended import jwt_required, get_jwt_identity

@integration_bp.route("/add", methods=["POST"])
@jwt_required()
def add_integration():
    data = request.get_json()
    api_key = data.get("api_key")

    # Decode and parse the identity (sub)
    identity = json.loads(get_jwt_identity())
    user_id = identity.get("user_id")

    if not api_key or not user_id:
        return jsonify({"message": "API key and User ID are required"}), 400

    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Create new Custobar integration for the user
    new_integration = CustobarIntegration(api_key=api_key, user_id=user_id)
    db.session.add(new_integration)
    db.session.commit()

    return jsonify({"message": "Custobar integration added successfully"}), 200


# Get all Custobar integrations for a user
@integration_bp.route("/user/<int:user_id>", methods=["GET"])
@jwt_required()
def get_integrations(user_id):
    try:
        # Extract and decode identity from the JWT token
        identity_json = get_jwt_identity()  # This is the serialized JSON string
        identity = json.loads(identity_json)  # Deserialize the JSON string
        token_user_id = identity.get("user_id")
        print("JWT Identity:", identity)  # Debugging

        # Validate the user_id matches the token user_id
        if token_user_id != user_id:
            return jsonify({"message": "Unauthorized access"}), 403

        # Fetch the user from the database
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        # Fetch integrations for the user
        integrations = CustobarIntegration.query.filter_by(user_id=user_id).all()
        if not integrations:
            return jsonify({"message": "No integrations found"}), 200

        # Serialize the integrations into a list
        integrations_list = [{"id": integration.id, "api_key": integration.api_key} for integration in integrations]

        return jsonify({"integrations": integrations_list}), 200
    except Exception as e:
        print("Error in get_integrations:", str(e))
        return jsonify({"message": "Internal server error"}), 500


CUSTOBAR_BASE_URL = "https://hopkins.custobar.com/api"  # Replace with actual domain

@integration_bp.route('/<int:integration_id>/fetch_data', methods=['POST', 'OPTIONS'])
def handle_fetch_data(integration_id):
    if request.method == 'OPTIONS':
        return jsonify({"message": "Preflight successful"}), 200  # Handle CORS preflight

    return fetch_custobar_data(integration_id)

@jwt_required()
def fetch_custobar_data(integration_id):
    # Validate integration ownership
    # Fetch the identity and deserialize if it's a JSON string
    identity_raw = get_jwt_identity()
    print("Raw JWT Identity:", identity_raw)

    if isinstance(identity_raw, str):
        try:
            identity = json.loads(identity_raw)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JWT Identity: {e}")
            return jsonify({"message": "Invalid token format"}), 401
    elif isinstance(identity_raw, dict):
        identity = identity_raw
    else:
        return jsonify({"message": "Unexpected token format"}), 401

    print("Final JWT Identity:", identity)
    user_id = identity['user_id']

    # Validate integration ownership
    integration = CustobarIntegration.query.filter_by(id=integration_id, user_id=user_id).first()

    if not integration:
        return jsonify({"message": "Unauthorized or invalid integration"}), 403

    try:
        # Prepare API request
        api_key = integration.api_key
        headers = {"Authorization": f"Bearer {api_key}"}
        query_params = request.json or {}  # Accept query params (e.g., {"email": "test@example.com"})
        query_params['limit'] = query_params.get('limit', 10000)  # Default limit


        # Fetch and save events
        print("Fetching events...")
        events = fetch_event_data(headers, query_params)
        save_events(events, integration.id)

        # Fetch and save customers
        print("Fetching customers...")
        customers = fetch_customer_data(headers, query_params)
        save_customers(customers, integration.id)

        # Fetch and save transactions
        print("Fetching transactions...")
        transactions = fetch_transaction_data(headers, query_params)
        save_transactions(transactions, integration.id)

        return jsonify({"message": "Data fetched successfully"}), 200

    except Exception as e:
        print(f"Error fetching data: {e}")
        return jsonify({"message": "Error fetching data", "error": str(e)}), 500


# Fetch customer data
def fetch_customer_data(headers, query_params):
    url = f"{CUSTOBAR_BASE_URL}/data/customers/"
    customers = []
    counter = 0
    while url:
        response = requests.get(url, headers=headers, params=query_params if '?' not in url else None)
        print("Fetching URL:", url)

        if response.status_code != 200:
            print(f"Failed to fetch customers: {response.text}")
            raise Exception("Error fetching customer data")

        try:
            data = response.json()
            print(f"Received {len(data.get('customers', []))} customers")
            counter = counter + len(data.get('customers', []))
            print(f"Total count {counter} / {data.get('count', [])} customers")
        except ValueError as e:
            print(f"JSON Decode Error: {e}")
            raise Exception("Error decoding Custobar response")

        customers.extend(data.get('customers', []))
        url = data.get('next_url')  # Use absolute URL for the next batch

        time.sleep(1)  # Respect API rate limits

        break

    return customers

# Fetch transaction data
def fetch_transaction_data(headers, query_params):
    url = f"{CUSTOBAR_BASE_URL}/data/sales/"
    transactions = []

    counter = 0
    while url:
        response = requests.get(url, headers=headers, params=query_params if '?' not in url else None)
        print("Fetching URL:", url)

        if response.status_code != 200:
            print(f"Failed to fetch transactions: {response.text}")
            raise Exception("Error fetching transaction data")

        try:
            data = response.json()
            print(f"Received {len(data.get('sales', []))} transactions")
            counter = counter + len(data.get('sales', []))
            print(f"Total count {counter} / {data.get('count')} transactions")
        except ValueError as e:
            print(f"JSON Decode Error: {e}")
            raise Exception("Error decoding Custobar response")

        transactions.extend(data.get('sales', []))
        url = data.get('next_url')  # Use absolute URL for the next batch

        time.sleep(1)  # Respect API rate limits

        break

    return transactions

# Fetch event data
def fetch_event_data(headers, query_params):
    url = f"{CUSTOBAR_BASE_URL}/data/events/"
    events = []
    counter = 0
    while url:
        response = requests.get(url, headers=headers, params=query_params if '?' not in url else None)
        print("Fetching URL:", url)

        if response.status_code != 200:
            print(f"Failed to fetch events: {response.text}")
            raise Exception("Error fetching event data")

        try:
            data = response.json()
            print(f"Received {len(data.get('events', []))} events")
            counter = counter +  len(data.get('events', []))
            print(f"Received {counter} / {data.get('count', [])} events")

        except ValueError as e:
            print(f"JSON Decode Error: {e}")
            raise Exception("Error decoding Custobar response")

        events.extend(data.get('events', []))
        url = data.get('next_url')  # Use absolute URL for the next batch

        time.sleep(1)  # Respect API rate limits

        break

    return events

def save_customers(customers, integration_id):
    """Save or update customer data in the database."""
    for customer_data in customers:
        cb_id = customer_data.get('external_id')  # Fetch Custobar's external_id
        if not cb_id:
            continue  # Skip if no cb_id (external_id)

        # Check if customer already exists using the cb_id (which is now external_id)
        customer = Customer.query.filter_by(cb_id=cb_id, custobar_integration_id=integration_id).first()
        if not customer:
            # If not found, create a new customer
            customer = Customer(cb_id=cb_id, custobar_integration_id=integration_id)

        # Update customer data
        # Convert string dates to datetime objects, if the string is not empty or None
        if customer_data.get('date_joined'):
            customer.signup_date = datetime.strptime(customer_data.get('date_joined'), "%Y-%m-%dT%H:%M:%S")
        if customer_data.get('last_purchase_date'):
            customer.last_purchase_date = datetime.strptime(customer_data.get('last_purchase_date'),
                                                            "%Y-%m-%dT%H:%M:%S")
        if customer_data.get('last_action_date'):
            customer.last_action_date = datetime.strptime(customer_data.get('last_action_date'), "%Y-%m-%dT%H:%M:%S")

        if customer_data.get('last_login'):
            customer.last_login = datetime.strptime(customer_data.get('last_login'),
                                                          "%Y-%m-%dT%H:%M:%S")

        customer.can_email = customer_data.get('can_email')
        customer.city = customer_data.get('city')
        customer.country = customer_data.get('country')
        customer.gender = customer_data.get('gender')
        customer.language = customer_data.get('language')
        customer.tags = customer_data.get('tags')
        customer.mailing_lists = customer_data.get('mailing_lists')

        # Add or update the customer in the session
        db.session.add(customer)

    # Commit the changes to the database
    db.session.commit()


def save_transactions(transactions, integration_id):
    """Save or update transaction data in the database."""
    for transaction in transactions:
        cb_id = transaction.get('customer_id')  # Fetch the customer_id from the sales endpoint
        if not cb_id:
            continue  # Skip if no cb_id (customer_id)

        # Check if the transaction already exists by using the sale_external_id
        existing_transaction = Transaction.query.filter_by(
            custobar_integration_id=integration_id,
            cb_id=cb_id,  # Use cb_id to link the transaction to the customer
            sale_external_id=transaction.get("external_id")
        ).first()

        if existing_transaction:
            continue  # Skip existing transactions

        # Convert the transaction_date string to a datetime object
        transaction_date_str = transaction.get("date")
        if transaction_date_str:
            try:
                transaction_date = datetime.fromisoformat(transaction_date_str)
            except ValueError:
                print(f"Invalid date format for transaction: {transaction_date_str}")
                transaction_date = None
        else:
            transaction_date = None

        # Create new transaction
        new_transaction = Transaction(
            cb_id=cb_id,  # Use cb_id to link to customer
            sale_external_id=transaction.get("external_id"),
            custobar_integration_id=integration_id,
            transaction_date=transaction_date,
            product_ids=transaction.get("products", []),
            revenue=transaction.get("total"),
            action_type=transaction.get("state")  # Assuming you want to store state (complete, cancelled)
        )

        # Add new transaction to the session
        db.session.add(new_transaction)

    # Commit the changes to the database
    db.session.commit()

def save_events(events, integration_id):
    """Save or update event data in the database."""
    for event in events:
        cb_id = event.get('customer_id')  # Fetch the customer_id from the events endpoint
        if not cb_id:
            continue  # Skip if no cb_id (customer_id)

        # Convert the transaction_date string to a datetime object
        date_str = event.get("date")
        if date_str:
            try:
                event_date = datetime.fromisoformat(date_str)
            except ValueError:
                print(f"Invalid date format for transaction: {date_str}")
                event_date = None
        else:
            event_date = None

        utm_data = {
            "utm_source": event.get("utm_source", None),
            "utm_medium": event.get("utm_medium", None)
        }

        # Create new event
        new_event = Event(
            cb_id=cb_id,  # Use cb_id to link to customer
            event_type=event.get("type"),  # Event type (e.g. 'BROWSE', 'ORDER_SHIPPED', etc.)
            date=event_date,  # Event Date
            utm_data=utm_data,  # Optional additional event-specific data
            product_id=event.get("product_id"),
            path=event.get("path"),
            custobar_integration_id=integration_id
        )

        # Add new event to the session
        db.session.add(new_event)

    # Commit the changes to the database
    db.session.commit()