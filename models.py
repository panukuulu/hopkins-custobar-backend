from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Integer, String, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    integrations = db.relationship('CustobarIntegration', lazy=True)

# Integration Table
class CustobarIntegration(db.Model):
    __tablename__ = 'custobar_integrations'
    id = db.Column(db.Integer, primary_key=True)  # Integration ID
    api_key = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Establish relationship between CustobarIntegration and Customer
    customers = relationship('Customer', backref='custobar_integration', lazy=True)
    transactions = relationship('Transaction', backref='custobar_integration', lazy=True)
    events = relationship('Event', backref='custobar_integration', lazy=True)


# Customers Table
class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)  # Internal primary key
    cb_id = db.Column(db.String, unique=True, nullable=False)  # Customer's unique identifier from Custobar
    signup_date = db.Column(db.DateTime, nullable=True)  # SignupDate
    last_purchase_date = db.Column(db.DateTime, nullable=True)  # Last Purchase Date, join from Transactions
    last_action_date = db.Column(db.DateTime, nullable=True)  # Last Action Date, join from Events
    can_email = db.Column(db.Boolean, default=False)  # Whether the customer can be emailed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp
    custobar_integration_id = db.Column(db.Integer, db.ForeignKey('custobar_integrations.id'), nullable=False)
    city = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    last_login = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    mailing_lists = db.Column(db.JSON, nullable=True)


    # Relationships
    transactions = db.relationship('Transaction', back_populates='customer', lazy=True)
    events = db.relationship('Event', back_populates='customer', lazy=True)

    # Add any other customer-specific fields here



# Transactions Table
# Transactions Table
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    cb_id = db.Column(db.String, nullable=False)
    sale_external_id = db.Column(db.String, nullable=False)# Customer's ID from the sales endpoint
    product_ids = db.Column(db.JSON)  # Store ProductIDs array as JSON
    transaction_date = db.Column(db.DateTime, nullable=False)  # Date of transaction
    revenue = db.Column(db.Numeric(10, 2), nullable=False)  # Revenue of the transaction
    action_type = db.Column(db.String(50))  # Action type (e.g. view, add_to_cart, purchase)
    custobar_integration_id = db.Column(db.Integer, db.ForeignKey('custobar_integrations.id'), nullable=False)

    # Relationships
    cb_id = db.Column(db.String, db.ForeignKey('customers.cb_id'), nullable=False)  # Foreign key to Customer (using cb_id)
    customer = db.relationship('Customer', back_populates='transactions')

# Event Table (formerly Engagement Table)
class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    cb_id = db.Column(db.String, nullable=False)  # Customer's ID from the events endpoint
    event_type = db.Column(db.String(50), nullable=False)  # Event type (e.g. visit, subscribe)
    date = db.Column(db.DateTime, nullable=False)  # Event Date
    utm_data = db.Column(db.JSON, nullable=True)  # Optional additional event-specific data (e.g., UTM tags, etc.)
    product_id = db.Column(db.String(50), nullable=True)
    path = db.Column(db.String(50), nullable=True)
    custobar_integration_id = db.Column(db.Integer, db.ForeignKey('custobar_integrations.id'), nullable=False)

    # Relationships
    cb_id = db.Column(db.String, db.ForeignKey('customers.cb_id'), nullable=False)  # Foreign key to Customer (using cb_id)
    customer = db.relationship('Customer', back_populates='events')


# Metrics Table
class Metrics(db.Model):
    __tablename__ = 'metrics'

    id = db.Column(db.Integer, primary_key=True)
    campaign_type = db.Column(db.String(100), nullable=True)  # Can be None if not provided
    date = db.Column(db.Date, nullable=False)  # Store only the date part
    active_customers = db.Column(db.Integer, nullable=True)  # Can be None, Default None if not available
    new_customers = db.Column(db.Integer, nullable=True)  # Can be None, Default None if not available
    passive_customers = db.Column(db.Integer, nullable=True)  # Can be None, Default None if not available
    avg_purchase_revenue_per_customer = db.Column(db.Numeric(10, 2), nullable=True)  # Can be None
    avg_purchase_revenue_per_active_customer = db.Column(db.Numeric(10, 2), nullable=True)  # Can be None
    avg_purchase_size = db.Column(db.Numeric(10, 2), nullable=True)  # Can be None
    visitors_website_from_customers = db.Column(db.Integer, nullable=True)  # Can be None
    customer_lifetime_value_overall = db.Column(db.Numeric(10, 2), nullable=True)  # Can be None
    customer_lifetime_value_active_customers = db.Column(db.Numeric(10, 2), nullable=True)  # Can be None
    open_rate = db.Column(db.Numeric(5, 2), nullable=True)  # Can be None
    click_rate = db.Column(db.Numeric(5, 2), nullable=True)  # Can be None
    conversion_rate = db.Column(db.Numeric(5, 2), nullable=True)  # Can be None
    opt_outs = db.Column(db.Integer, nullable=True)  # Can be None

    # Foreign key relationship to CustobarIntegration
    custobar_integration_id = db.Column(db.Integer, db.ForeignKey('custobar_integrations.id'), nullable=False)

    # Relationship to CustobarIntegration
    custobar_integration = db.relationship('CustobarIntegration', backref='metrics', lazy=True)


class SegmentedMetrics(db.Model):
    __tablename__ = 'segmented_metrics'

    id = db.Column(db.Integer, primary_key=True)
    campaign_type = db.Column(db.String(100), nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    segment = db.Column(db.String(255), nullable=False)  # Segment (e.g., city, country, etc.)
    active_customers = db.Column(db.Integer, nullable=True)
    new_customers = db.Column(db.Integer, nullable=True)
    passive_customers = db.Column(db.Integer, nullable=True)
    total_revenue = db.Column(db.Numeric(10, 2), nullable=True)
    avg_purchase_revenue_per_customer = db.Column(db.Numeric(10, 2), nullable=True)
    avg_purchase_revenue_per_active_customer = db.Column(db.Numeric(10, 2), nullable=True)
    avg_purchase_size = db.Column(db.Numeric(10, 2), nullable=True)
    visitors_website_from_customers = db.Column(db.Integer, nullable=True)
    customer_lifetime_value_overall = db.Column(db.Numeric(10, 2), nullable=True)
    customer_lifetime_value_active_customers = db.Column(db.Numeric(10, 2), nullable=True)
    open_rate = db.Column(db.Numeric(5, 2), nullable=True)
    click_rate = db.Column(db.Numeric(5, 2), nullable=True)
    conversion_rate = db.Column(db.Numeric(5, 2), nullable=True)
    opt_outs = db.Column(db.Integer, nullable=True)
    clicks = db.Column(db.Integer, nullable=True)
    opens = db.Column(db.Integer, nullable=True)
    transactions = db.Column(db.Integer, nullable=True)

    # Foreign key relationship to CustobarIntegration
    custobar_integration_id = db.Column(db.Integer, db.ForeignKey('custobar_integrations.id'), nullable=False)

    # Relationship to CustobarIntegration
    custobar_integration = db.relationship('CustobarIntegration', backref='segmented_metrics', lazy=True)