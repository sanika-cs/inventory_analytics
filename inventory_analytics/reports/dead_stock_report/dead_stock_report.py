import frappe
from frappe import _

def execute(filters=None):
	"""
	Dead Stock Analysis Report - Shows dead stock and liquidation strategy
	"""
	if not filters:
		filters = {}
	
	columns = [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Days Dead"), "fieldname": "days_since_last_sale", "fieldtype": "Int", "width": 100},
		{"label": _("Age (years)"), "fieldname": "age_years", "fieldtype": "Float", "width": 80},
		{"label": _("Last Sale"), "fieldname": "last_sale_date", "fieldtype": "Date", "width": 100},
		{"label": _("Current Stock"), "fieldname": "current_stock", "fieldtype": "Float", "width": 100},
		{"label": _("Stock Value (₹)"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 120},
		{"label": _("Original Value (₹)"), "fieldname": "original_value", "fieldtype": "Currency", "width": 130},
		{"label": _("Holding Cost (₹)"), "fieldname": "holding_cost_total", "fieldtype": "Currency", "width": 130},
		{"label": _("Strategy"), "fieldname": "liquidation_strategy", "fieldtype": "Data", "width": 120},
		{"label": _("Discount %"), "fieldname": "discount_percentage", "fieldtype": "Percent", "width": 100},
		{"label": _("Recovery %"), "fieldname": "recovery_percentage", "fieldtype": "Percent", "width": 100},
		{"label": _("Recovery Value (₹)"), "fieldname": "recovery_value", "fieldtype": "Currency", "width": 140},
		{"label": _("Liquidity Score"), "fieldname": "liquidity_score", "fieldtype": "Int", "width": 120},
		{"label": _("Timeline (m)"), "fieldname": "timeline_months", "fieldtype": "Int", "width": 100},
		{"label": _("Priority"), "fieldname": "priority", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "action_status", "fieldtype": "Data", "width": 100},
	]
	
	data = []
	
	# Build filter conditions
	conditions = []
	if filters.get("priority"):
		conditions.append(f"priority = '{filters.get('priority')}'")
	if filters.get("liquidation_strategy"):
		conditions.append(f"liquidation_strategy = '{filters.get('liquidation_strategy')}'")
	if filters.get("action_status"):
		conditions.append(f"action_status = '{filters.get('action_status')}'")
	
	where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
	
	# Fetch data
	items = frappe.db.sql(f"""
		SELECT 
			item_code, item_name, days_since_last_sale, age_years, last_sale_date,
			current_stock, stock_value, original_value, holding_cost_total,
			liquidation_strategy, discount_percentage, recovery_percentage,
			recovery_value, liquidity_score, timeline_months, priority, action_status
		FROM `tabDead Stock Analysis`
		{where_clause}
		ORDER BY priority, recovery_value DESC
	""", as_dict=1)
	
	for item in items:
		data.append(item)
	
	return columns, data
