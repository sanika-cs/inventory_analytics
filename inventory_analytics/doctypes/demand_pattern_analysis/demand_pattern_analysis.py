"""
Demand Pattern Analysis DocType - Python Backend
Implements SBC method for demand forecasting

For: uae.hydrotech inventory analytics
"""

import frappe
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, date_diff
from datetime import datetime, timedelta
import json
import numpy as np
import logging

# Import model
try:
    from inventory_analytics_app.models.demand_pattern_model import DemandPatternModel
except ImportError:
    DemandPatternModel = None

logger = logging.getLogger(__name__)


class DemandPatternAnalysis(Document):
    """
    DocType: Demand Pattern Analysis
    Analyzes demand patterns using Syntetos-Boylan-Croston method
    """
    
    def before_save(self):
        """Before save - validate and analyze"""
        if not self.item_code:
            frappe.throw("Item Code is required")
        
        if not self.demand_pattern:
            self.analyze_demand_pattern()
    
    def analyze_demand_pattern(self):
        """Analyze demand pattern using SBC method"""
        try:
            if not DemandPatternModel:
                logger.error("ML model not available")
                return
            
            # Get monthly sales
            monthly_sales = [
                self.month_1_sales or 0,
                self.month_2_sales or 0,
                self.month_3_sales or 0,
                self.month_4_sales or 0,
                self.month_5_sales or 0,
                self.month_6_sales or 0,
                self.month_7_sales or 0,
                self.month_8_sales or 0,
                self.month_9_sales or 0,
                self.month_10_sales or 0,
                self.month_11_sales or 0,
                self.month_12_sales or 0,
            ]
            
            model = DemandPatternModel()
            adi, cv2, classification = model._classify_sbc(monthly_sales)
            
            self.demand_pattern = classification
            self.adi = adi
            self.cv_squared = cv2
            
            # Calculate metrics
            non_zero = [s for s in monthly_sales if s > 0]
            if non_zero:
                self.avg_monthly_demand = np.mean(non_zero)
                self.demand_variability = (np.std(monthly_sales) / np.mean(monthly_sales) * 100) if np.mean(monthly_sales) > 0 else 0
                self.total_annual_demand = sum(monthly_sales)
            
            # Generate forecast
            forecast = model._generate_forecast(monthly_sales, classification)
            self.forecast_30d = forecast['forecast_30d']
            self.forecast_method = forecast['method']
            self.confidence_interval_lower = forecast['ci_lower']
            self.confidence_interval_upper = forecast['ci_upper']
            
            # Calculate ROP
            rop_data = model._calculate_rop(monthly_sales, classification)
            self.reorder_point = rop_data['rop']
            self.safety_stock = rop_data['safety_stock']
            self.economic_order_qty = rop_data['eoq']
            self.recommended_order_qty = rop_data['recommended_qty']
            self.order_frequency = rop_data['order_frequency']
            
            # Get recommendations
            recommendations = model._get_recommendations({}, classification, forecast)
            self.recommended_action = recommendations['action']
            self.action_priority = recommendations['priority']
            
        except Exception as e:
            logger.error(f"Error analyzing demand pattern: {str(e)}")
            frappe.throw(f"Error: {str(e)}")


# API Methods

@frappe.whitelist()
def get_demand_history(item_code):
    """
    Get 12-month demand history for an item
    """
    try:
        history = {
            'total_annual': 0,
            'avg_monthly': 0
        }
        
        # Get sales for last 12 months
        monthly_data = frappe.db.sql("""
            SELECT
                MONTH(si.posting_date) as month,
                SUM(sii.qty) as qty
            FROM
                `tabSales Invoice Item` sii
            JOIN
                `tabSales Invoice` si ON sii.parent = si.name
            WHERE
                sii.item_code = %s
                AND si.posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                AND si.docstatus = 1
            GROUP BY
                MONTH(si.posting_date)
        """, (item_code,), as_dict=True)
        
        # Initialize all months
        for i in range(1, 13):
            history[f'month_{i}'] = 0
        
        # Fill in data
        total = 0
        for row in monthly_data:
            month = row['month']
            qty = row['qty']
            history[f'month_{month}'] = qty
            total += qty
        
        history['total_annual'] = total
        history['avg_monthly'] = total / 12 if total > 0 else 0
        
        return history
    
    except Exception as e:
        frappe.throw(f"Error fetching demand history: {str(e)}")


@frappe.whitelist()
def analyze_demand_pattern(item_code, monthly_sales=None):
    """
    API: Analyze demand pattern for item
    """
    try:
        if not DemandPatternModel:
            frappe.throw("ML model not available")
        
        # Parse monthly_sales if string
        if isinstance(monthly_sales, str):
            import json
            monthly_sales = json.loads(monthly_sales)
        
        if not monthly_sales:
            # Fetch from history
            history = get_demand_history(item_code)
            monthly_sales = [history[f'month_{i}'] for i in range(1, 13)]
        
        model = DemandPatternModel()
        adi, cv2, classification = model._classify_sbc(monthly_sales)
        
        # Generate reason
        reason = get_classification_reason(adi, cv2, classification)
        
        return {
            'demand_pattern': classification,
            'adi': adi,
            'cv_squared': cv2,
            'demand_variability': (np.std(monthly_sales) / np.mean(monthly_sales) * 100) if np.mean(monthly_sales) > 0 else 0,
            'reason': reason
        }
    
    except Exception as e:
        frappe.throw(f"Error: {str(e)}")


@frappe.whitelist()
def calculate_rop(demand_pattern, monthly_sales=None, lead_time_days=7):
    """
    API: Calculate ROP and safety stock
    """
    try:
        if not DemandPatternModel:
            frappe.throw("ML model not available")
        
        if isinstance(monthly_sales, str):
            import json
            monthly_sales = json.loads(monthly_sales)
        
        model = DemandPatternModel()
        model.config['lead_time_days'] = lead_time_days
        
        rop_data = model._calculate_rop(monthly_sales or [0]*12, demand_pattern)
        
        return rop_data
    
    except Exception as e:
        frappe.throw(f"Error calculating ROP: {str(e)}")


@frappe.whitelist()
def get_forecast_chart(item_code, demand_pattern):
    """
    API: Get forecast chart data
    """
    try:
        # Generate forecast data
        history = get_demand_history(item_code)
        monthly_sales = [history[f'month_{i}'] for i in range(1, 13)]
        
        model = DemandPatternModel()
        forecast = model._generate_forecast(monthly_sales, demand_pattern)
        
        # Prepare chart data
        days = list(range(1, 31))
        daily_forecast = [forecast['forecast_30d'] / 30 for _ in days]
        
        return {
            'data': [
                {
                    'x': days,
                    'y': daily_forecast,
                    'type': 'scatter',
                    'name': 'Daily Forecast',
                    'fill': 'tozeroy'
                },
                {
                    'x': days,
                    'y': [forecast['ci_upper'] / 30 for _ in days],
                    'type': 'scatter',
                    'name': 'Upper CI',
                    'line': {'dash': 'dash'},
                    'visible': 'legendonly'
                },
                {
                    'x': days,
                    'y': [forecast['ci_lower'] / 30 for _ in days],
                    'type': 'scatter',
                    'name': 'Lower CI',
                    'line': {'dash': 'dash'},
                    'visible': 'legendonly'
                }
            ],
            'layout': {
                'title': f'30-Day Demand Forecast - {demand_pattern} Pattern',
                'xaxis': {'title': 'Day'},
                'yaxis': {'title': 'Daily Demand'},
                'height': 400
            }
        }
    
    except Exception as e:
        frappe.throw(f"Error generating forecast chart: {str(e)}")


def get_classification_reason(adi, cv2, classification):
    """Get explanation for demand pattern classification"""
    
    reasons = {
        'SMOOTH': f"Regular, predictable demand (ADI: {adi:.2f}, CV²: {cv2:.3f})",
        'ERRATIC': f"Variable demand with high volatility (ADI: {adi:.2f}, CV²: {cv2:.3f})",
        'INTERMITTENT': f"Infrequent but consistent demand (ADI: {adi:.2f}, CV²: {cv2:.3f})",
        'LUMPY': f"Chaotic B2B demand pattern (ADI: {adi:.2f}, CV²: {cv2:.3f})"
    }
    
    return reasons.get(classification, "Unknown pattern")
