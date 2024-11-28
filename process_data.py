from datetime import datetime, timedelta
from sqlalchemy import func
from models import CustobarIntegration, User, Customer, Transaction, db, Event, Metrics
import traceback

def calculate_metrics(integration_id):
    lookback = 3000
    """Calculate and populate the metrics for a given integration."""
    today = datetime.utcnow().date()  # Get today's date without time
    start_of_day = today

    print("starting calculation for " + str(today))

    try:
        # Query for the total active customers (customers who made at least one purchase in the last 30 days)
        active_customers = db.session.query(func.count(Customer.id)).join(Transaction).filter(
            Transaction.custobar_integration_id == integration_id,
            Transaction.transaction_date >= start_of_day - timedelta(days=lookback)  # Active within the last 30 days
        ).scalar()

        print("active customers done " + str(active_customers))

        # Query for new customers (customers who signed up within the last 30 days)
        new_customers = db.session.query(func.count(Customer.id)).filter(
            Customer.custobar_integration_id == integration_id,
            Customer.signup_date >= start_of_day - timedelta(days=lookback)
        ).scalar()

        print("new customers done " + str(new_customers))

        # Query for passive customers (total customers - active customers)
        total_customers = db.session.query(func.count(Customer.id)).filter(
            Customer.custobar_integration_id == integration_id
        ).scalar()

        print("total customers done " + str(total_customers))

        passive_customers = total_customers - active_customers

        print("passive customers done " + str(passive_customers))

        # Calculate Average Purchase Revenue per Customer
        avg_purchase_revenue_per_customer = db.session.query(func.sum(Transaction.revenue)).filter(
            Transaction.custobar_integration_id == integration_id
        ).scalar() / total_customers if total_customers else 0

        total_revenue = db.session.query(func.sum(Transaction.revenue)).filter(
            Transaction.custobar_integration_id == integration_id
        ).scalar()

        print("avg purchase done " + str(avg_purchase_revenue_per_customer))

        # Calculate Average Purchase Revenue per Active Customer
        avg_purchase_revenue_per_active_customer = db.session.query(func.sum(Transaction.revenue)).filter(
            Transaction.custobar_integration_id == integration_id,
            Transaction.transaction_date >= start_of_day - timedelta(days=lookback)
        ).scalar() / active_customers if active_customers else 0

        print("avg purchase per active done " + str(avg_purchase_revenue_per_active_customer))

        # Calculate Average Purchase Size (average transaction value)
        avg_purchase_size = db.session.query(func.sum(Transaction.revenue)).filter(
            Transaction.custobar_integration_id == integration_id
        ).scalar() / db.session.query(func.count(Transaction.id)).filter(
            Transaction.custobar_integration_id == integration_id
        ).scalar() if total_customers else 0

        print("avg purchase size done " + str(avg_purchase_size))

        # Visitors to website from customers (count events with event_type 'visit' from customers)
        visitors_website_from_customers = db.session.query(func.count(Event.id)).filter(
            Event.custobar_integration_id == integration_id,
            Event.event_type == 'visit'
        ).scalar()

        print("visitors to website done " + str(visitors_website_from_customers))

        # Customer Lifetime Value (Overall)
        customer_lifetime_value_overall = db.session.query(func.sum(Transaction.revenue)).filter(
            Transaction.custobar_integration_id == integration_id
        ).scalar() / total_customers if total_customers else 0

        print("CLV overall done " + str(customer_lifetime_value_overall))

        # Customer Lifetime Value (Active Customers)
        customer_lifetime_value_active_customers = db.session.query(func.sum(Transaction.revenue)).filter(
            Transaction.custobar_integration_id == integration_id,
            Transaction.transaction_date >= start_of_day - timedelta(days=lookback)
        ).scalar() / active_customers if active_customers else 0

        print("CLV active done " + str(customer_lifetime_value_active_customers))

        # Count the number of MAIL_OPEN events for this segment
        mail_open_count = db.session.query(func.count(Event.id)).filter(
            Event.custobar_integration_id == integration_id,
            Event.event_type == 'MAIL_OPEN',  # Filter for MAIL_OPEN event type
            Event.date >= start_of_day - timedelta(days=lookback)  # Events in the last 'lookback' days
        ).scalar() or 0

        # Count the number of MAIL_CLICK events for this segment
        mail_click_count = db.session.query(func.count(Event.id)).filter(
            Event.custobar_integration_id == integration_id,
            Event.event_type == 'MAIL_CLICK',  # Filter for MAIL_CLICK event type
            Event.date >= start_of_day - timedelta(days=lookback)  # Events in the last 'lookback' days
        ).scalar() or 0

        # Number of transactions in the last 30 days
        num_transactions = db.session.query(func.count(Transaction.id)).select_from(Customer).join(
            Transaction, Customer.cb_id == Transaction.cb_id).filter(
            Transaction.custobar_integration_id == integration_id,
            Transaction.transaction_date >= start_of_day - timedelta(days=lookback)
        ).scalar() or 1  # Prevent division by zero

        # Placeholder for actual open rate, click rate, conversion rate, opt-out calculation
        open_rate = 0

        # Calculate the click rate (MAIL_CLICK / MAIL_OPEN)
        click_rate = mail_click_count / mail_open_count if mail_open_count != 0 else 0

        # Calculate the conversion rate (Transactions / MAIL_CLICK)
        conversion_rate = num_transactions / mail_click_count if mail_click_count != 0 else 0

        opt_outs = 0

        # Check if metrics already exist for the date and integration_id
        existing_metrics = db.session.query(Metrics).filter(
            Metrics.date == today,
            Metrics.custobar_integration_id == integration_id
        ).first()

        if existing_metrics:
            # If metrics already exist, update the existing row
            existing_metrics.active_customers = active_customers
            existing_metrics.new_customers = new_customers
            existing_metrics.passive_customers = passive_customers
            existing_metrics.total_revenue = total_revenue
            existing_metrics.avg_purchase_revenue_per_customer = avg_purchase_revenue_per_customer
            existing_metrics.avg_purchase_revenue_per_active_customer = avg_purchase_revenue_per_active_customer
            existing_metrics.avg_purchase_size = avg_purchase_size
            existing_metrics.visitors_website_from_customers = visitors_website_from_customers
            existing_metrics.customer_lifetime_value_overall = customer_lifetime_value_overall
            existing_metrics.customer_lifetime_value_active_customers = customer_lifetime_value_active_customers
            existing_metrics.open_rate = open_rate
            existing_metrics.click_rate = click_rate
            existing_metrics.conversion_rate = conversion_rate
            existing_metrics.opt_outs = opt_outs
            existing_metrics.opens = mail_open_count
            existing_metrics.clicks = mail_click_count
            existing_metrics.transactions = num_transactions

        else:
            # If no existing metrics, create a new record
            metrics = Metrics(
                campaign_type="Email",  # Can be dynamic if you have different campaign types
                date=today,  # Use only the date part
                active_customers=active_customers if active_customers is not None else 0,
                new_customers=new_customers if new_customers is not None else 0,
                passive_customers=passive_customers if passive_customers is not None else 0,
                total_revenue=total_revenue if total_revenue is not None else 0,
                avg_purchase_revenue_per_customer=avg_purchase_revenue_per_customer if avg_purchase_revenue_per_customer is not None else 0,
                avg_purchase_revenue_per_active_customer=avg_purchase_revenue_per_active_customer if avg_purchase_revenue_per_active_customer is not None else 0,
                avg_purchase_size=avg_purchase_size if avg_purchase_size is not None else 0,
                visitors_website_from_customers=visitors_website_from_customers if visitors_website_from_customers is not None else 0,
                customer_lifetime_value_overall=customer_lifetime_value_overall if customer_lifetime_value_overall is not None else 0,
                customer_lifetime_value_active_customers=customer_lifetime_value_active_customers if customer_lifetime_value_active_customers is not None else 0,
                open_rate=open_rate if open_rate is not None else 0,
                click_rate=click_rate if click_rate is not None else 0,
                conversion_rate=conversion_rate if conversion_rate is not None else 0,
                opt_outs=opt_outs if opt_outs is not None else 0,
                custobar_integration_id=integration_id,
                opens=mail_open_count,
                clicks=mail_click_count,
                transactions=num_transactions
            )
            db.session.add(metrics)

        db.session.commit()

        print("Metrics populated successfully")

    except Exception as e:
        print(e)

    return {"message": "Metrics populated successfully"}


def update_last_action_and_purchase_dates():
    """Update the last_purchase_date and last_action_date for all customers."""
    try:
        # Step 1: Get the most recent transaction date for each customer
        print("Updating last purchase date for customers")

        # Get all customer `cb_id` values
        customer_cb_ids = db.session.query(Customer.cb_id).all()

        for customer_cb_id in customer_cb_ids:
            cb_id = customer_cb_id[0]  # Extract customer cb_id from tuple

            # Get the most recent transaction date for this customer (if any)
            last_purchase = db.session.query(func.max(Transaction.transaction_date)).filter(
                Transaction.cb_id == cb_id  # Using cb_id for identification
            ).scalar()

            # Get the most recent event date for this customer (if any)
            last_action = db.session.query(func.max(Event.date)).filter(
                Event.cb_id == cb_id  # Using cb_id for identification
            ).scalar()

            # Fetch the customer object by cb_id
            customer = Customer.query.filter_by(cb_id=cb_id).first()

            if customer:
                # Update the last_purchase_date
                if last_purchase:
                    customer.last_purchase_date = last_purchase

                # Update the last_action_date
                if last_action:
                    customer.last_action_date = last_action

                # Add the updated customer to the session
                db.session.add(customer)

        # Commit the changes
        db.session.commit()

        print("Last purchase and action dates updated for all customers")

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        print(f"Error updating last purchase and action dates: {e}")


from sqlalchemy import func
from datetime import datetime, timedelta
from models import db, Customer, Transaction, Event, SegmentedMetrics


##todo avg purchase size must be calculated from transactions table.
##todo avg. revenue per customer is 1000x too big
##todo clv should be calculated for all customers as well
##todo must be caculated daily, and  replaced

def calculate_segmented_metrics(integration_id):

    lookback = 3000
    """Calculate segmented metrics for the given Custobar integration."""

    print("Entered segmented metrics function")

    today = datetime.utcnow().date()  # Get today's date without time
    start_of_day = today

    # Define the segmentation fields
    # Define the segmentation fields
    segmentation_fields = ['city', 'country', 'gender', 'language', 'last_login', 'tags', 'mailing_lists']

    try:
        # Loop through each segmentation field and calculate the metrics
        for field in segmentation_fields:
            print(f"Calculating metrics for field in segmentation fields: {field}")

            # Get the distinct values for the current segmentation field
            segment_values = db.session.query(getattr(Customer, field)).distinct().all()

            for value in segment_values:
                # Convert the tuple to a simple value

                try:
                    print("Calculating metrics for segment value " + str(value[0]))
                    segment_value = value[0] if value[0] else 'Unknown'

                except TypeError as e:

                    print("error in segement value " + str(e))
                    segment_value = 'None'

                # Calculate the metrics for the segment
                active_customers = db.session.query(func.count(Customer.id)).select_from(Customer).join(
                    Transaction, Customer.cb_id == Transaction.cb_id).filter(
                    Transaction.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value,
                    Transaction.transaction_date >= start_of_day - timedelta(days=lookback)
                ).scalar() or 0

                print("Active customers: " + str(active_customers))

                # For new_customers (No need to join Transaction, just filter by signup_date)
                new_customers = db.session.query(func.count(Customer.id)).filter(
                    Customer.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value,
                    Customer.signup_date >= start_of_day - timedelta(days=lookback)
                    # New customers in the last 'lookback' days
                ).scalar() or 0

                print("New customers: " + str(new_customers))

                # For total_customers
                # For total_customers (No need to join Transaction, just count customers in the segment)
                total_customers = db.session.query(func.count(Customer.id)).filter(
                    Customer.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value
                ).scalar() or 0

                print("Total customers: " + str(total_customers))

                print("Made it to passive customers")

                passive_customers = total_customers - active_customers

                print("Passive customers: " + str(passive_customers))

                # Calculate Average Purchase Size (total revenue / number of purchases)
                # Calculate Average Purchase Size (total revenue / number of purchases)
                # Sum of revenue divided by the number of transactions (not number of customers)
                total_revenue_for_segment = db.session.query(func.sum(Transaction.revenue)).select_from(Customer).join(
                    Transaction, Customer.cb_id == Transaction.cb_id).filter(
                    Transaction.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value,
                    Transaction.transaction_date >= start_of_day - timedelta(days=lookback)
                ).scalar() or 0

                print("total_revenue_for_segment: " + str(total_revenue_for_segment))

                # Number of transactions in the last 30 days
                num_transactions = db.session.query(func.count(Transaction.id)).select_from(Customer).join(
                    Transaction, Customer.cb_id == Transaction.cb_id).filter(
                    Transaction.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value,
                    Transaction.transaction_date >= start_of_day - timedelta(days=lookback)
                ).scalar() or 1  # Prevent division by zero

                print("num_transactions: " + str(num_transactions))

                avg_purchase_revenue_per_transaction = total_revenue_for_segment / num_transactions or 0

                print("avg_purchase_size: " + str(avg_purchase_revenue_per_transaction))

                print("total_revenue_for_segment: " + str(total_revenue_for_segment))

                avg_purchase_revenue_per_customer = total_revenue_for_segment / total_customers if total_customers else 0
                print("avg_purchase_revenue_per_customer: " + str(avg_purchase_revenue_per_customer))

                avg_purchase_revenue_per_active_customer = (total_revenue_for_segment / active_customers) if active_customers else 0
                print("avg_purchase_revenue_per_active_customer: " + str(avg_purchase_revenue_per_active_customer))

                # Calculate Customer Lifetime Value (Overall) (total revenue / total customers in the period)
                total_revenue_for_clv = db.session.query(func.sum(Transaction.revenue)).select_from(Customer).join(
                    Transaction, Customer.cb_id == Transaction.cb_id).filter(
                    Transaction.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value
                ).scalar() or 0

                # Count total customers who had at least one transaction
                total_customers_for_clv = db.session.query(func.count(Customer.id)).select_from(Customer).join(
                    Transaction, Customer.cb_id == Transaction.cb_id).filter(
                    Transaction.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value
                ).scalar() or 1  # Prevent division by zero

                customer_lifetime_value_overall = total_revenue_for_clv / total_customers_for_clv

                print("Made it to customer_lifetime_value_active_customers")

                # Calculate Customer Lifetime Value (Active Customers) (total revenue / active customers)
                customer_lifetime_value_active_customers = db.session.query(func.sum(Transaction.revenue)).select_from(
                    Customer).join(
                    Transaction, Customer.cb_id == Transaction.cb_id).filter(
                    Transaction.custobar_integration_id == integration_id,
                    getattr(Customer, field) == segment_value,
                    Transaction.transaction_date >= start_of_day - timedelta(days=lookback)
                ).scalar() or 0

                # Calculate Customer Lifetime Value (Active Customers)
                customer_lifetime_value_active_customers = customer_lifetime_value_active_customers / active_customers if active_customers else 0

                print("Made it to visitors_website_from_customers")

                # Calculate Visitors to Website (unique BROWSE events in the last 30 days)
                visitors_website_from_customers = db.session.query(func.count(Event.id.distinct())).filter(
                    Event.custobar_integration_id == integration_id,
                    Event.event_type == 'BROWSE',
                    getattr(Customer, field) == segment_value,
                    Event.date >= start_of_day - timedelta(days=lookback)
                ).scalar() or 0

                # Count the number of MAIL_OPEN events for this segment
                mail_open_count = db.session.query(func.count(Event.id)).filter(
                    Event.custobar_integration_id == integration_id,
                    Event.event_type == 'MAIL_OPEN',  # Filter for MAIL_OPEN event type
                    getattr(Customer, field) == segment_value,
                    Event.date >= start_of_day - timedelta(days=lookback)  # Events in the last 'lookback' days
                ).scalar() or 0

                # Count the number of MAIL_CLICK events for this segment
                mail_click_count = db.session.query(func.count(Event.id)).filter(
                    Event.custobar_integration_id == integration_id,
                    Event.event_type == 'MAIL_CLICK',  # Filter for MAIL_CLICK event type
                    getattr(Customer, field) == segment_value,
                    Event.date >= start_of_day - timedelta(days=lookback)  # Events in the last 'lookback' days
                ).scalar() or 0

                # Placeholder for actual open rate, click rate, conversion rate, opt-out calculation
                open_rate = 0
                # Calculate the click rate (MAIL_CLICK / MAIL_OPEN)
                click_rate = mail_click_count / mail_open_count if mail_open_count != 0 else 0

                # Calculate the conversion rate (Transactions / MAIL_CLICK)
                conversion_rate = num_transactions / mail_click_count if mail_click_count != 0 else 0
                opt_outs = 0

                # Check if metrics already exist for this segment, date, and custobar_integration_id
                existing_metrics = db.session.query(SegmentedMetrics).filter(
                    SegmentedMetrics.date == today,
                    SegmentedMetrics.segment == f"{field}: {segment_value}",
                    SegmentedMetrics.custobar_integration_id == integration_id
                ).first()

                # If metrics exist, update them; otherwise, create a new one
                if existing_metrics:
                    existing_metrics.active_customers = active_customers
                    existing_metrics.new_customers = new_customers
                    existing_metrics.passive_customers = passive_customers
                    existing_metrics.total_revenue = total_revenue_for_segment
                    existing_metrics.avg_purchase_revenue_per_customer = avg_purchase_revenue_per_customer
                    existing_metrics.avg_purchase_revenue_per_active_customer = avg_purchase_revenue_per_active_customer
                    existing_metrics.avg_purchase_size = avg_purchase_revenue_per_transaction
                    existing_metrics.visitors_website_from_customers = visitors_website_from_customers
                    existing_metrics.customer_lifetime_value_overall = customer_lifetime_value_overall
                    existing_metrics.customer_lifetime_value_active_customers = customer_lifetime_value_active_customers
                    existing_metrics.open_rate = open_rate
                    existing_metrics.click_rate = click_rate
                    existing_metrics.conversion_rate = conversion_rate
                    existing_metrics.opt_outs = opt_outs
                    existing_metrics.opens = mail_open_count
                    existing_metrics.clicks = mail_click_count
                    existing_metrics.transactions = num_transactions

                else:
                    segmented_metrics = SegmentedMetrics(
                        campaign_type="Email",  # Can be dynamic if you have different campaign types
                        date=today,
                        segment=f"{field}: {segment_value}",
                        active_customers=active_customers,
                        new_customers=new_customers,
                        passive_customers=passive_customers,
                        total_revenue=total_revenue_for_segment,
                        avg_purchase_revenue_per_customer=avg_purchase_revenue_per_customer,
                        avg_purchase_revenue_per_active_customer=avg_purchase_revenue_per_active_customer,
                        avg_purchase_size=avg_purchase_revenue_per_transaction,
                        visitors_website_from_customers=visitors_website_from_customers,
                        customer_lifetime_value_overall=customer_lifetime_value_overall,
                        customer_lifetime_value_active_customers=customer_lifetime_value_active_customers,
                        open_rate=open_rate,
                        click_rate=click_rate,
                        conversion_rate=conversion_rate,
                        opt_outs=opt_outs,
                        custobar_integration_id=integration_id,
                        opens=mail_open_count,
                        clicks=mail_click_count,
                        transactions=num_transactions
                    )
                    db.session.add(segmented_metrics)

            # Commit the changes
            db.session.commit()
            print(f"Metrics for {field} segment populated successfully")

    except Exception as e:
        # Log the full traceback to the console
        print(f"Error calculating segmented metrics: {str(e)}")
        print(traceback.format_exc())  # Print the traceback for detailed error context

        # Re-raise the error so Flask can send it to the client
        raise

