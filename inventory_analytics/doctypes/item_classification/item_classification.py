"""
Item Classification DocType - Python Backend
Handles ML model inference, data loading, insights generation

For: uae.hydrotech inventory analytics system
"""

import frappe
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, date_diff
from datetime import datetime, timedelta
import json
import logging

# Import the ML model
try:
    from inventory_analytics_app.models.item_classification_model import ItemClassificationModel
except ImportError:
    ItemClassificationModel = None

logger = logging.getLogger(__name__)


class ItemClassification(Document):
    """
    DocType: Item Classification
    Manages item classification results and insights
    """
    
    def before_save(self):
        """
        Before save validation and classification
        """
        # Validate required fields
        if not self.item_code:
            frappe.throw("Item Code is required")
        
        # Fetch item details if not present
        if not self.item_name:
            self.fetch_item_details()
        
        # Load current metrics if empty
        if not self.annual_sales_qty:
            self.load_item_metrics()
        
        # Run classification
        self.run_classification()
    
    def after_insert(self):
        """
        After insert - generate insights and recommendations
        """
        self.generate_insights()
    
    def fetch_item_details(self):
        """Fetch item details from Item DocType"""
        try:
            item = frappe.get_doc('Item', self.item_code)
            self.item_name = item.item_name
            self.uom = item.stock_uom
        except frappe.DoesNotExistError:
            frappe.throw(f"Item {self.item_code} does not exist")
    
    def load_item_metrics(self):
        """Load item metrics from warehouse and sales"""
        try:
            # Get warehouse data
            warehouse_data = frappe.db.get_value(
                'Bin',
                {'item_code': self.item_code},
                ['actual_qty', 'valuation_rate'],
                as_dict=True
            )
            
            if warehouse_data:
                self.current_stock = warehouse_data.get('actual_qty', 0)
                self.stock_value = self.current_stock * warehouse_data.get('valuation_rate', 0)
            
            # Get sales data for last 365 days
            sales_data = get_sales_metrics(self.item_code)
            if sales_data:
                self.annual_sales_qty = sales_data.get('qty', 0)
                self.annual_sales_value = sales_data.get('value', 0)
                self.sales_velocity = sales_data.get('daily_velocity', 0)
                self.last_sale_date = sales_data.get('last_sale_date')
                self.days_since_last_sale = sales_data.get('days_since_last_sale', 0)
            
            # Calculate derived metrics
            self.calculate_derived_metrics()
            
        except Exception as e:
            logger.error(f"Error loading metrics for {self.item_code}: {str(e)}")
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics"""
        # Days of Stock
        if self.sales_velocity and self.sales_velocity > 0:
            self.days_of_stock = self.current_stock / self.sales_velocity
        else:
            self.days_of_stock = 0
        
        # Turnover Ratio
        if self.current_stock and self.current_stock > 0:
            self.turnover_ratio = self.annual_sales_qty / self.current_stock
        else:
            self.turnover_ratio = 0
        
        # Annual Holding Cost (20% of stock value)
        self.holding_cost_annually = self.stock_value * 0.20
        
        # Item Age
        try:
            item = frappe.get_doc('Item', self.item_code)
            item_created = get_datetime(item.creation)
            self.item_age_days = date_diff(datetime.now(), item_created)
            self.first_sale_date = get_first_sale_date(self.item_code)
            
            if self.first_sale_date:
                self.days_to_first_sale = date_diff(
                    self.first_sale_date, 
                    item_created
                )
        except Exception as e:
            logger.error(f"Error calculating item age: {str(e)}")
        
        # ABC Category (simplified - based on annual value)
        if self.annual_sales_value > 100000:
            self.abc_category = 'A'
        elif self.annual_sales_value > 20000:
            self.abc_category = 'B'
        else:
            self.abc_category = 'C'
        
        # Dormancy Status
        if self.days_since_last_sale < 90:
            self.dormancy_status = 'ACTIVE'
        elif self.days_since_last_sale < 180:
            self.dormancy_status = 'SLEEPY'
        elif self.days_since_last_sale < 365:
            self.dormancy_status = 'DORMANT'
        else:
            self.dormancy_status = 'DEAD'
        
        # New Item Status
        if self.item_age_days < 30:
            self.new_item_status = 'LAUNCH'
        elif self.item_age_days < 90:
            self.new_item_status = 'LEARNING'
        elif self.item_age_days < 180:
            self.new_item_status = 'GRADUATION'
        else:
            self.new_item_status = 'ESTABLISHED'
    
    def run_classification(self):
        """Run ML classification on the item"""
        try:
            if not ItemClassificationModel:
                logger.error("ML model not available, using rule-based classification")
                self.run_rule_based_classification()
                return
            
            # Prepare data for model
            data = {
                'item_code': self.item_code,
                'item_name': self.item_name,
                'uom': self.uom,
                'annual_sales_qty': self.annual_sales_qty or 0,
                'annual_sales_value': self.annual_sales_value or 0,
                'current_stock': self.current_stock or 0,
                'stock_value': self.stock_value or 0,
                'item_age_days': self.item_age_days or 0,
                'days_since_last_sale': self.days_since_last_sale or 0,
                'created_date': frappe.get_doc('Item', self.item_code).creation,
                'sales_velocity': self.sales_velocity or 0,
                'turnover_ratio': self.turnover_ratio or 0,
                'consistency_score': self.consistency_score or 50,
                'demand_variability': self.demand_variability or 0,
            }
            
            # Run hybrid classification
            model = ItemClassificationModel()
            import pandas as pd
            df = pd.DataFrame([data])
            results = model.classify_items(df, method='hybrid')
            
            if len(results) > 0:
                result = results.iloc[0].to_dict()
                
                # Update document
                self.classification_type = result.get('classification_type')
                self.classification_confidence = result.get('classification_confidence', 75)
                self.classification_method = result.get('classification_method')
                self.classification_reason = result.get('classification_reason', '')
                self.recommended_action = result.get('recommended_action')
                self.action_priority = result.get('action_priority', 5)
                self.expected_impact = result.get('expected_impact', 0)
                self.model_version = result.get('model_version')
            
        except Exception as e:
            logger.error(f"Error running ML classification: {str(e)}")
            self.run_rule_based_classification()
    
    def run_rule_based_classification(self):
        """Fallback: Rule-based classification"""
        
        # Rule 1: NEW_ITEM (highest priority)
        if self.item_age_days < 90:
            self.classification_type = 'NEW_ITEM'
            self.classification_confidence = 99
            self.classification_method = 'RULE_BASED'
            self.classification_reason = f"Item age {self.item_age_days} days < 90 threshold"
            self.recommended_action = 'MARKET_MORE'
            self.action_priority = 7
            return
        
        # Rule 2: DEAD_STOCK (high priority)
        if self.days_since_last_sale > 180 or self.annual_sales_qty < 10:
            self.classification_type = 'DEAD_STOCK'
            self.classification_confidence = 95
            self.classification_method = 'RULE_BASED'
            self.classification_reason = f"No sales for {self.days_since_last_sale} days (threshold: 180)"
            self.recommended_action = 'LIQUIDATION'
            self.action_priority = 10
            return
        
        # Rule 3: FAST (high velocity + high revenue)
        if self.sales_velocity > 2.7 and self.turnover_ratio > 0.7:
            self.classification_type = 'FAST'
            self.classification_confidence = 90
            self.classification_method = 'RULE_BASED'
            self.classification_reason = f"High velocity {self.sales_velocity:.2f} units/day, Turnover {self.turnover_ratio:.2f}"
            self.recommended_action = 'INCREASE_STOCK'
            self.action_priority = 8
            return
        
        # Rule 4: SLOW (low velocity + consistent)
        if self.sales_velocity < 0.5 and self.days_since_last_sale < 60:
            self.classification_type = 'SLOW'
            self.classification_confidence = 85
            self.classification_method = 'RULE_BASED'
            self.classification_reason = f"Low velocity ({self.sales_velocity:.2f} units/day) but consistent"
            self.recommended_action = 'MAINTAIN_STOCK'
            self.action_priority = 2
            return
        
        # Rule 5: MEDIUM (default)
        self.classification_type = 'MEDIUM'
        self.classification_confidence = 75
        self.classification_method = 'RULE_BASED'
        self.classification_reason = "Mid-range item characteristics"
        self.recommended_action = 'MAINTAIN_STOCK'
        self.action_priority = 5
    
    def generate_insights(self):
        """Generate insights based on classification"""
        try:
            insights = {
                'title': f"Classification: {self.classification_type}",
                'classification': self.classification_type,
                'confidence': self.classification_confidence,
                'metrics': self.get_key_metrics(),
                'recommendations': self.get_recommendations(),
                'actions': self.get_action_items()
            }
            
            # Store insights
            self.insights_json = json.dumps(insights)
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
    
    def get_key_metrics(self):
        """Get key metrics for insights"""
        metrics = []
        
        if self.classification_type == 'FAST':
            metrics = [
                f"High-revenue item: AED {self.annual_sales_value:,.0f}/year",
                f"Daily velocity: {self.sales_velocity:.2f} units/day",
                f"Turnover ratio: {self.turnover_ratio:.2f}",
                f"Days of stock: {self.days_of_stock:.1f} days",
                f"ABC Category: {self.abc_category}"
            ]
        
        elif self.classification_type == 'SLOW':
            metrics = [
                f"Steady demand: {self.annual_sales_qty} units/year",
                f"Daily velocity: {self.sales_velocity:.2f} units/day",
                f"Demand consistency: {self.consistency_score}%",
                f"Days of stock: {self.days_of_stock:.1f} days",
                f"Last sale: {self.days_since_last_sale} days ago"
            ]
        
        elif self.classification_type == 'DEAD_STOCK':
            metrics = [
                f"⚠️ No sales for {self.days_since_last_sale} days",
                f"Stock value: AED {self.stock_value:,.0f}",
                f"Annual holding cost: AED {self.holding_cost_annually:,.0f}",
                f"Stock age: {self.stock_age_days or 0} days",
                f"Dormancy: {self.dormancy_status}"
            ]
        
        elif self.classification_type == 'NEW_ITEM':
            metrics = [
                f"Item age: {self.item_age_days} days",
                f"Status: {self.new_item_status}",
                f"Days to first sale: {self.days_to_first_sale or 'Not sold yet'}",
                f"Current sales: {self.annual_sales_qty} units (launch phase)",
                f"Stock: {self.current_stock} units"
            ]
        
        return metrics
    
    def get_recommendations(self):
        """Get recommendations"""
        recommendations = []
        
        if self.classification_type == 'FAST':
            recommendations = [
                "Increase safety stock by 20-30%",
                "Implement more frequent reordering",
                "Negotiate better supplier terms",
                "Consider bulk purchasing discounts"
            ]
        
        elif self.classification_type == 'SLOW':
            dos = self.days_of_stock
            if dos > 180:
                recommendations = [
                    f"High Days of Stock ({dos:.0f} days) - reduce orders",
                    "Review with procurement",
                    "Consider sales promotion"
                ]
            else:
                recommendations = [
                    "Maintain current stock levels",
                    "Monitor demand trends",
                    "Plan quarterly reviews"
                ]
        
        elif self.classification_type == 'DEAD_STOCK':
            recommendations = [
                f"URGENT: Liquidate to recover AED {self.expected_impact:,.0f}",
                f"Holding costs: AED {self.holding_cost_annually:,.0f}/year",
                "Consider donation for tax benefit",
                "Update demand forecast"
            ]
        
        elif self.classification_type == 'NEW_ITEM':
            recommendations = [
                "Increase marketing efforts",
                f"Expected growth: {((self.expected_impact / max(self.annual_sales_value, 1)) * 100):.0f}%",
                "Monitor sales closely (weekly reviews)",
                "Gather customer feedback"
            ]
        
        return recommendations
    
    def get_action_items(self):
        """Get action items"""
        actions = []
        
        actions.append({
            'action': self.recommended_action,
            'priority': self.action_priority,
            'impact': f"AED {self.expected_impact:,.0f}",
            'date': frappe.utils.today()
        })
        
        # Add follow-up review
        actions.append({
            'action': 'SCHEDULE_REVIEW',
            'priority': 5,
            'impact': 'Data-driven insights',
            'date': frappe.utils.add_days(frappe.utils.today(), 30)
        })
        
        return actions


# API Methods

@frappe.whitelist()
def get_item_metrics(item_code):
    """
    API: Get item metrics
    Fetches comprehensive item metrics from various documents
    """
    try:
        # Get item
        item = frappe.get_doc('Item', item_code)
        
        # Get warehouse data
        warehouse_data = frappe.db.get_value(
            'Bin',
            {'item_code': item_code},
            ['actual_qty', 'valuation_rate'],
            as_dict=True
        ) or {}
        
        current_stock = warehouse_data.get('actual_qty', 0)
        valuation_rate = warehouse_data.get('valuation_rate', 0)
        stock_value = current_stock * valuation_rate
        
        # Get sales metrics
        sales_data = get_sales_metrics(item_code)
        
        annual_sales_qty = sales_data.get('qty', 0)
        annual_sales_value = sales_data.get('value', 0)
        sales_velocity = sales_data.get('daily_velocity', 0)
        
        days_of_stock = (current_stock / sales_velocity) if sales_velocity > 0 else 0
        turnover_ratio = (annual_sales_qty / current_stock) if current_stock > 0 else 0
        
        return {
            'item_code': item_code,
            'item_name': item.item_name,
            'uom': item.stock_uom,
            'annual_sales_qty': annual_sales_qty,
            'annual_sales_value': annual_sales_value,
            'sales_velocity': sales_velocity,
            'turnover_ratio': turnover_ratio,
            'current_stock': current_stock,
            'stock_value': stock_value,
            'days_of_stock': days_of_stock,
            'days_since_last_sale': sales_data.get('days_since_last_sale', 0),
            'last_sale_date': sales_data.get('last_sale_date'),
            'item_age_days': date_diff(datetime.now(), get_datetime(item.creation)),
            'first_sale_date': get_first_sale_date(item_code),
            'consistency_score': 50,  # Placeholder
            'demand_variability': 0,  # Placeholder
        }
    
    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        frappe.throw(f"Error fetching metrics: {str(e)}")


@frappe.whitelist()
def get_item_stock(item_code):
    """API: Get current item stock"""
    try:
        warehouse_data = frappe.db.get_value(
            'Bin',
            {'item_code': item_code},
            ['actual_qty', 'valuation_rate'],
            as_dict=True
        ) or {}
        
        qty = warehouse_data.get('actual_qty', 0)
        value = qty * warehouse_data.get('valuation_rate', 0)
        
        return {'qty': qty, 'value': value}
    
    except Exception as e:
        frappe.throw(f"Error fetching stock: {str(e)}")


@frappe.whitelist()
def run_classification(item_code, method='hybrid'):
    """API: Run classification on item"""
    try:
        doc = ItemClassification()
        doc.item_code = item_code
        doc.fetch_item_details()
        doc.load_item_metrics()
        
        if method == 'hybrid':
            doc.run_classification()
        elif method == 'rule_based':
            doc.run_rule_based_classification()
        else:
            doc.run_classification()
        
        return {
            'classification_type': doc.classification_type,
            'classification_confidence': doc.classification_confidence,
            'classification_method': doc.classification_method,
            'classification_reason': doc.classification_reason,
            'recommended_action': doc.recommended_action,
            'action_priority': doc.action_priority,
            'expected_impact': doc.expected_impact,
        }
    
    except Exception as e:
        logger.error(f"Error running classification: {str(e)}")
        frappe.throw(f"Error: {str(e)}")


@frappe.whitelist()
def generate_insights(doc_dict):
    """API: Generate insights"""
    try:
        doc = frappe.get_doc(doc_dict)
        doc.generate_insights()
        
        return json.loads(doc.insights_json)
    
    except Exception as e:
        frappe.throw(f"Error generating insights: {str(e)}")


@frappe.whitelist()
def validate_item_data(item_code):
    """API: Validate item data quality"""
    try:
        doc = ItemClassification()
        doc.item_code = item_code
        doc.load_item_metrics()
        
        return {
            'has_sales_data': bool(doc.annual_sales_qty),
            'has_stock_data': bool(doc.current_stock),
            'has_pricing': bool(doc.stock_value),
            'has_history': bool(doc.last_sale_date),
            'is_valid': all([
                doc.annual_sales_qty,
                doc.current_stock is not None,
                doc.stock_value
            ])
        }
    
    except Exception as e:
        frappe.throw(f"Error validating data: {str(e)}")


# Helper Functions

def get_sales_metrics(item_code):
    """Get sales metrics for last 365 days"""
    try:
        # Get sales invoices
        invoices = frappe.db.sql("""
            SELECT
                SUM(sii.qty) as total_qty,
                SUM(sii.amount) as total_value,
                MAX(si.posting_date) as last_sale_date
            FROM
                `tabSales Invoice Item` sii
            JOIN
                `tabSales Invoice` si ON sii.parent = si.name
            WHERE
                sii.item_code = %s
                AND si.posting_date >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
                AND si.docstatus = 1
        """, (item_code,), as_dict=True)
        
        if invoices and len(invoices) > 0:
            result = invoices[0]
            qty = result.get('total_qty') or 0
            value = result.get('total_value') or 0
            last_sale = result.get('last_sale_date')
            
            days_since_last_sale = date_diff(datetime.now(), last_sale) if last_sale else 999
            daily_velocity = qty / 365.0 if qty > 0 else 0
            
            return {
                'qty': qty,
                'value': value,
                'daily_velocity': daily_velocity,
                'last_sale_date': last_sale,
                'days_since_last_sale': days_since_last_sale
            }
    
    except Exception as e:
        logger.error(f"Error getting sales metrics: {str(e)}")
    
    return {'qty': 0, 'value': 0, 'daily_velocity': 0, 'last_sale_date': None, 'days_since_last_sale': 999}


def get_first_sale_date(item_code):
    """Get first sale date of item"""
    try:
        result = frappe.db.sql("""
            SELECT MIN(si.posting_date) as first_sale
            FROM `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON sii.parent = si.name
            WHERE sii.item_code = %s AND si.docstatus = 1
        """, (item_code,), as_dict=True)
        
        if result and result[0].get('first_sale'):
            return result[0]['first_sale']
    
    except Exception as e:
        logger.error(f"Error getting first sale date: {str(e)}")
    
    return None
