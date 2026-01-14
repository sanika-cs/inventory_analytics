import frappe
from frappe import _

def execute(filters=None):
	"""
	New Items Health Report - Shows new item performance and health
	"""
	if not filters:
		filters = {}
	
	columns = [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Days Old"), "fieldname": "days_since_creation", "fieldtype": "Int", "width": 80},
		{"label": _("Life Stage"), "fieldname": "life_stage", "fieldtype": "Data", "width": 100},
		{"label": _("Health Score"), "fieldname": "health_score", "fieldtype": "Int", "width": 100},
		{"label": _("Health Status"), "fieldname": "health_status", "fieldtype": "Data", "width": 100},
		{"label": _("Sales Perf"), "fieldname": "sales_performance_score", "fieldtype": "Int", "width": 100},
		{"label": _("Customer Acq"), "fieldname": "customer_acquisition_score", "fieldtype": "Int", "width": 100},
		{"label": _("Stock Adequacy"), "fieldname": "stock_adequacy_score", "fieldtype": "Int", "width": 100},
		{"label": _("Growth Score"), "fieldname": "growth_trend_score", "fieldtype": "Int", "width": 100},
		{"label": _("Target Achievement %"), "fieldname": "target_achievement_pct", "fieldtype": "Percent", "width": 120},
		{"label": _("Actual Sales (units)"), "fieldname": "actual_units", "fieldtype": "Float", "width": 120},
		{"label": _("Revenue (₹)"), "fieldname": "actual_revenue", "fieldtype": "Currency", "width": 120},
		{"label": _("Unique Customers"), "fieldname": "unique_customers", "fieldtype": "Int", "width": 120},
		{"label": _("Days of Stock"), "fieldname": "days_of_stock", "fieldtype": "Float", "width": 100},
		{"label": _("Growth %"), "fieldname": "growth_percentage", "fieldtype": "Percent", "width": 80},
		{"label": _("Action Priority"), "fieldname": "action_priority", "fieldtype": "Data", "width": 100},
	]
	
	data = []
	
	# Build filter conditions
	conditions = []
	if filters.get("health_status"):
		conditions.append(f"health_status = '{filters.get('health_status')}'")
	if filters.get("life_stage"):
		conditions.append(f"life_stage = '{filters.get('life_stage')}'")
	if filters.get("action_priority"):
		conditions.append(f"action_priority = '{filters.get('action_priority')}'")
	
	where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
	
	# Fetch data
	items = frappe.db.sql(f"""
		SELECT 
			item_code, item_name, days_since_creation, life_stage, health_score,
			health_status, sales_performance_score, customer_acquisition_score,
			stock_adequacy_score, growth_trend_score, target_achievement_pct,
			actual_units, actual_revenue, unique_customers, days_of_stock,
			growth_percentage, action_priority
		FROM `tabNew Item Health Report`
		{where_clause}
		ORDER BY health_score ASC, action_priority ASC
	""", as_dict=1)
	
	for item in items:
		data.append(item)
	
	return columns, data
