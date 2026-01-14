import frappe
from frappe import _

def execute(filters=None):
	"""
	Demand Pattern Analysis Report - Shows demand patterns and forecast
	"""
	if not filters:
		filters = {}
	
	columns = [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Classification"), "fieldname": "classification", "fieldtype": "Data", "width": 100},
		{"label": _("Pattern"), "fieldname": "demand_pattern", "fieldtype": "Select", "width": 120},
		{"label": _("ADI"), "fieldname": "adi", "fieldtype": "Float", "width": 80},
		{"label": _("CV²"), "fieldname": "cv_squared", "fieldtype": "Float", "width": 80},
		{"label": _("Demand Size"), "fieldname": "demand_size", "fieldtype": "Float", "width": 100},
		{"label": _("Actual (30d)"), "fieldname": "qty_30d", "fieldtype": "Float", "width": 100},
		{"label": _("Forecast (30d)"), "fieldname": "forecast_30d", "fieldtype": "Float", "width": 120},
		{"label": _("Safety Stock"), "fieldname": "safety_stock", "fieldtype": "Float", "width": 100},
		{"label": _("ROP"), "fieldname": "reorder_point", "fieldtype": "Float", "width": 80},
		{"label": _("Current Stock"), "fieldname": "current_stock", "fieldtype": "Float", "width": 100},
		{"label": _("Stock Status"), "fieldname": "stock_status", "fieldtype": "Data", "width": 100},
		{"label": _("Order Qty"), "fieldname": "recommended_order_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Priority"), "fieldname": "order_priority", "fieldtype": "Select", "width": 100},
		{"label": _("Order Date"), "fieldname": "recommended_order_date", "fieldtype": "Date", "width": 100},
	]
	
	data = []
	
	# Build filter conditions
	conditions = []
	if filters.get("demand_pattern"):
		conditions.append(f"demand_pattern = '{filters.get('demand_pattern')}'")
	if filters.get("classification"):
		conditions.append(f"classification = '{filters.get('classification')}'")
	if filters.get("stock_status"):
		conditions.append(f"stock_status = '{filters.get('stock_status')}'")
	if filters.get("order_priority"):
		conditions.append(f"order_priority = '{filters.get('order_priority')}'")
	
	where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
	
	# Fetch data
	items = frappe.db.sql(f"""
		SELECT 
			item_code, item_name, classification, demand_pattern, adi, cv_squared,
			demand_size, qty_30d, forecast_30d, safety_stock, reorder_point,
			current_stock, stock_status, recommended_order_qty, order_priority,
			recommended_order_date
		FROM `tabDemand Pattern Analysis`
		{where_clause}
		ORDER BY order_priority, days_until_stockout ASC
	""", as_dict=1)
	
	for item in items:
		data.append(item)
	
	return columns, data
