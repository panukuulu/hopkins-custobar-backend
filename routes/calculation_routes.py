from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from process_data import calculate_metrics, update_last_action_and_purchase_dates, calculate_segmented_metrics  # Assuming this function is defined elsewhere


calculation_bp = Blueprint('calculation_bp', __name__)


@calculation_bp.route('/<int:integration_id>/populate_metrics', methods=['POST'])
@jwt_required()
def populate_metrics(integration_id):
    """Populate the metrics table for a specific integration."""
    try:
        # Calculate the metrics using the integration_id
        print("Calculating metrics")

        result = calculate_metrics(integration_id)

        print("Done calculating metrics")

        result = calculate_segmented_metrics(integration_id)

        print("Done calculating segmented metrics")

        # After calculating and saving metrics
        update_last_action_and_purchase_dates()  # Call the function to update the dates

        print("Done calculating last action data")

        return jsonify({"message": "Metrics populated successfully"}), 200

    except Exception as e:
        return jsonify({"message": "Error populating metrics", "error": str(e)}), 500