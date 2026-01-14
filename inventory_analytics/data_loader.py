import frappe
import pandas as pd
import os
from datetime import datetime

class InventoryAnalyticsDataLoader:
	"""
	Loads analysis data from CSV files into ERPNext DocTypes
	"""
	
	def __init__(self):
		self.base_path = "/tmp"  # CSV files location
		self.stats = {
			"created": 0,
			"updated": 0,
			"errors": 0,
			"skipped": 0
		}
	
	def load_classification_data(self, file_path=None):
		"""Load Item Classification data"""
		if not file_path:
			file_path = f"{self.base_path}/dbscan_classification.csv"
		
		if not os.path.exists(file_path):
			frappe.msgprint(f"File not found: {file_path}", "Error")
			return
		
		frappe.msgprint(f"Loading classification data from {file_path}...")
		
		df = pd.read_csv(file_path)
		
		for idx, row in df.iterrows():
			try:
				# Check if record exists
				existing = frappe.db.exists("Item Classification", row["item_code"])
				
				if existing:
					doc = frappe.get_doc("Item Classification", row["item_code"])
					self.stats["updated"] += 1
				else:
					doc = frappe.new_doc("Item Classification")
					self.stats["created"] += 1
				
				# Map fields
				doc.item_code = row.get("item_code")
				doc.classification = row.get("classification")
				doc.velocity_90d = float(row.get("velocity_90d", 0))
				doc.turnover_rate = float(row.get("turnover_rate", 0))
				doc.qty_90d = float(row.get("qty_90d", 0))
				doc.transaction_count = int(row.get("transaction_count", 0))
				doc.avg_transaction_qty = float(row.get("avg_transaction_qty", 0))
				doc.days_of_stock = float(row.get("days_of_stock", 0))
				doc.total_qty_sold = float(row.get("total_qty_sold", 0))
				doc.total_sales_value = float(row.get("total_sales_value", 0))
				doc.last_sale_date = row.get("last_sale_date")
				doc.days_since_last_sale = int(row.get("days_since_last_sale", 0))
				doc.stock_value = float(row.get("stock_value", 0))
				doc.avg_valuation_rate = float(row.get("avg_valuation_rate", 0))
				doc.trend_30d = row.get("trend_30d", "FLAT")
				doc.growth_percentage = float(row.get("growth_percentage", 0))
				doc.analysis_date = datetime.now().strftime("%Y-%m-%d")
				
				doc.save(ignore_permissions=True)
				
			except Exception as e:
				self.stats["errors"] += 1
				frappe.log_error(
					title="Classification Import Error",
					message=f"Row {idx}: {str(e)}"
				)
		
		frappe.msgprint(
			f"Classification import complete: "
			f"Created: {self.stats['created']}, "
			f"Updated: {self.stats['updated']}, "
			f"Errors: {self.stats['errors']}"
		)
	
	def load_demand_pattern_data(self, file_path=None):
		"""Load Demand Pattern Analysis data"""
		if not file_path:
			file_path = f"{self.base_path}/demand_patterns.csv"
		
		if not os.path.exists(file_path):
			frappe.msgprint(f"File not found: {file_path}", "Error")
			return
		
		frappe.msgprint(f"Loading demand pattern data from {file_path}...")
		
		self.stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}
		df = pd.read_csv(file_path)
		
		for idx, row in df.iterrows():
			try:
				existing = frappe.db.exists("Demand Pattern Analysis", row["item_code"])
				
				if existing:
					doc = frappe.get_doc("Demand Pattern Analysis", row["item_code"])
					self.stats["updated"] += 1
				else:
					doc = frappe.new_doc("Demand Pattern Analysis")
					self.stats["created"] += 1
				
				doc.item_code = row.get("item_code")
				doc.classification = row.get("classification")
				doc.demand_pattern = row.get("demand_pattern")
				doc.adi = float(row.get("adi", 0))
				doc.cv_squared = float(row.get("cv_squared", 0))
				doc.demand_size = float(row.get("demand_size", 0))
				doc.qty_30d = float(row.get("qty_30d", 0))
				doc.forecast_30d = float(row.get("forecast_30d", 0))
				doc.forecast_mad = float(row.get("forecast_mad", 0))
				doc.safety_stock = float(row.get("safety_stock", 0))
				doc.reorder_point = float(row.get("reorder_point", 0))
				doc.recommended_order_qty = float(row.get("recommended_order_qty", 0))
				doc.stock_status = row.get("stock_status", "OK")
				doc.days_until_stockout = float(row.get("days_until_stockout", 999))
				doc.order_priority = row.get("order_priority", "LOW")
				doc.order_value = float(row.get("order_value", 0))
				doc.recommended_order_date = row.get("recommended_order_date")
				doc.avg_lead_time_days = int(row.get("avg_lead_time_days", 0))
				doc.analysis_date = datetime.now().strftime("%Y-%m-%d")
				
				doc.save(ignore_permissions=True)
				
			except Exception as e:
				self.stats["errors"] += 1
				frappe.log_error(
					title="Demand Pattern Import Error",
					message=f"Row {idx}: {str(e)}"
				)
		
		frappe.msgprint(
			f"Demand pattern import complete: "
			f"Created: {self.stats['created']}, "
			f"Updated: {self.stats['updated']}, "
			f"Errors: {self.stats['errors']}"
		)
	
	def load_new_items_health_data(self, file_path=None):
		"""Load New Items Health Report data"""
		if not file_path:
			file_path = f"{self.base_path}/new_items_health_report.csv"
		
		if not os.path.exists(file_path):
			frappe.msgprint(f"File not found: {file_path}", "Error")
			return
		
		frappe.msgprint(f"Loading new items health data from {file_path}...")
		
		self.stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}
		df = pd.read_csv(file_path)
		
		for idx, row in df.iterrows():
			try:
				existing = frappe.db.exists("New Item Health Report", row["item_code"])
				
				if existing:
					doc = frappe.get_doc("New Item Health Report", row["item_code"])
					self.stats["updated"] += 1
				else:
					doc = frappe.new_doc("New Item Health Report")
					self.stats["created"] += 1
				
				doc.item_code = row.get("item_code")
				doc.days_since_creation = int(row.get("days_since_creation", 0))
				doc.life_stage = row.get("life_stage", "LAUNCH")
				doc.health_score = int(row.get("health_score", 50))
				doc.sales_performance_score = int(row.get("sales_performance_score", 0))
				doc.customer_acquisition_score = int(row.get("customer_acquisition_score", 0))
				doc.stock_adequacy_score = int(row.get("stock_adequacy_score", 0))
				doc.growth_trend_score = int(row.get("growth_trend_score", 0))
				doc.target_units = float(row.get("target_units", 0))
				doc.actual_units = float(row.get("actual_units", 0))
				doc.target_achievement_pct = float(row.get("target_achievement_pct", 0))
				doc.unique_customers = int(row.get("unique_customers", 0))
				doc.customer_growth_pct = float(row.get("customer_growth_pct", 0))
				doc.days_of_stock = float(row.get("days_of_stock", 0))
				doc.stockout_risk = row.get("stockout_risk", "NONE")
				doc.growth_percentage = float(row.get("growth_percentage", 0))
				doc.trend_direction = row.get("trend_direction", "FLAT")
				doc.action_priority = row.get("action_priority", "LOW")
				doc.analysis_date = datetime.now().strftime("%Y-%m-%d")
				
				doc.save(ignore_permissions=True)
				
			except Exception as e:
				self.stats["errors"] += 1
				frappe.log_error(
					title="New Items Health Import Error",
					message=f"Row {idx}: {str(e)}"
				)
		
		frappe.msgprint(
			f"New items health import complete: "
			f"Created: {self.stats['created']}, "
			f"Updated: {self.stats['updated']}, "
			f"Errors: {self.stats['errors']}"
		)
	
	def load_dead_stock_data(self, file_path=None):
		"""Load Dead Stock Analysis data"""
		if not file_path:
			file_path = f"{self.base_path}/dead_stock_complete.csv"
		
		if not os.path.exists(file_path):
			frappe.msgprint(f"File not found: {file_path}", "Error")
			return
		
		frappe.msgprint(f"Loading dead stock data from {file_path}...")
		
		self.stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}
		df = pd.read_csv(file_path)
		
		for idx, row in df.iterrows():
			try:
				existing = frappe.db.exists("Dead Stock Analysis", row["item_code"])
				
				if existing:
					doc = frappe.get_doc("Dead Stock Analysis", row["item_code"])
					self.stats["updated"] += 1
				else:
					doc = frappe.new_doc("Dead Stock Analysis")
					self.stats["created"] += 1
				
				doc.item_code = row.get("item_code")
				doc.days_since_last_sale = int(row.get("days_since_last_sale", 0))
				doc.last_sale_date = row.get("last_sale_date")
				doc.age_years = float(row.get("age_years", 0))
				doc.stock_value = float(row.get("stock_value", 0))
				doc.original_value = float(row.get("original_value", 0))
				doc.holding_cost_total = float(row.get("holding_cost_total", 0))
				doc.holding_cost_annual = float(row.get("holding_cost_annual", 0))
				doc.liquidation_strategy = row.get("liquidation_strategy", "CLEARANCE")
				doc.discount_percentage = float(row.get("discount_percentage", 0))
				doc.recovery_percentage = float(row.get("recovery_percentage", 0))
				doc.recovery_value = float(row.get("recovery_value", 0))
				doc.liquidity_score = int(row.get("liquidity_score", 0))
				doc.timeline_months = int(row.get("timeline_months", 0))
				doc.priority = row.get("priority", "MEDIUM")
				doc.action_status = row.get("action_status", "PENDING")
				doc.analysis_date = datetime.now().strftime("%Y-%m-%d")
				
				doc.save(ignore_permissions=True)
				
			except Exception as e:
				self.stats["errors"] += 1
				frappe.log_error(
					title="Dead Stock Import Error",
					message=f"Row {idx}: {str(e)}"
				)
		
		frappe.msgprint(
			f"Dead stock import complete: "
			f"Created: {self.stats['created']}, "
			f"Updated: {self.stats['updated']}, "
			f"Errors: {self.stats['errors']}"
		)

@frappe.whitelist()
def load_all_analysis_data():
	"""Load all analysis data from CSV files"""
	loader = InventoryAnalyticsDataLoader()
	
	frappe.msgprint("Starting data import...")
	
	loader.load_classification_data()
	loader.load_demand_pattern_data()
	loader.load_new_items_health_data()
	loader.load_dead_stock_data()
	
	frappe.msgprint("All data import complete!")
	
	return {
		"status": "success",
		"message": "Data import completed successfully"
	}
