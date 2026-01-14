import frappe
import json
from frappe.utils import get_first_day, get_last_day, add_months, today
from datetime import timedelta

@frappe.whitelist()
def get_dashboard_data():
	"""
	Get all dashboard metrics for Inventory Analytics
	"""
	try:
		data = {
			"total_items": 0,
			"active_items": 0,
			"dead_stock_items": 0,
			"new_items": 0,
			"total_stock_value": 0,
			"dead_stock_value": 0,
			"below_rop": 0,
			"at_risk_items": 0,
			"classification_breakdown": {},
			"demand_pattern_breakdown": {},
			"health_status_breakdown": {},
			"critical_alerts": [],
			"top_dead_stock": [],
			"top_slow_items": [],
			"forecast_summary": {}
		}
		
		# Get classification counts
		classifications = frappe.db.sql("""
			SELECT classification, COUNT(*) as count, SUM(stock_value) as value
			FROM `tabItem Classification`
			GROUP BY classification
		""", as_dict=1)
		
		for row in classifications:
			data["classification_breakdown"][row.classification] = {
				"count": row.count,
				"value": row.value or 0
			}
			data["total_stock_value"] += row.value or 0
			
			if row.classification in ("FAST", "SLOW", "MEDIUM"):
				data["active_items"] += row.count
			elif row.classification == "DEAD_STOCK":
				data["dead_stock_items"] = row.count
				data["dead_stock_value"] = row.value or 0
			elif row.classification == "NEW_ITEM":
				data["new_items"] = row.count
		
		data["total_items"] = sum([v.get("count", 0) for v in data["classification_breakdown"].values()])
		
		# Get demand pattern breakdown
		patterns = frappe.db.sql("""
			SELECT demand_pattern, COUNT(*) as count
			FROM `tabDemand Pattern Analysis`
			GROUP BY demand_pattern
		""", as_dict=1)
		
		for row in patterns:
			data["demand_pattern_breakdown"][row.demand_pattern] = row.count
		
		# Get health status breakdown
		health = frappe.db.sql("""
			SELECT health_status, COUNT(*) as count
			FROM `tabNew Item Health Report`
			GROUP BY health_status
		""", as_dict=1)
		
		for row in health:
			data["health_status_breakdown"][row.health_status] = row.count
			if row.health_status in ("AT_RISK", "CRITICAL"):
				data["at_risk_items"] += row.count
		
		# Get items below ROP
		below_rop = frappe.db.sql("""
			SELECT COUNT(*) as count FROM `tabDemand Pattern Analysis`
			WHERE stock_status = 'BELOW_ROP'
		""", as_dict=1)
		
		data["below_rop"] = below_rop[0].count if below_rop else 0
		
		# Critical alerts - Items that need immediate attention
		critical_items = frappe.db.sql("""
			SELECT 'CRITICAL: Dead Stock' as alert_type, COUNT(*) as count
			FROM `tabDead Stock Analysis`
			WHERE priority = 'CRITICAL'
			UNION ALL
			SELECT 'URGENT: Below ROP' as alert_type, COUNT(*) as count
			FROM `tabDemand Pattern Analysis`
			WHERE stock_status = 'BELOW_ROP'
			UNION ALL
			SELECT 'RISK: New Item Critical' as alert_type, COUNT(*) as count
			FROM `tabNew Item Health Report`
			WHERE health_status = 'CRITICAL'
		""", as_dict=1)
		
		for row in critical_items:
			data["critical_alerts"].append({
				"alert": row.alert_type,
				"count": row.count
			})
		
		# Top dead stock items by recovery value
		top_dead = frappe.db.sql("""
			SELECT item_code, item_name, stock_value, recovery_value, age_years
			FROM `tabDead Stock Analysis`
			ORDER BY recovery_value DESC
			LIMIT 5
		""", as_dict=1)
		
		data["top_dead_stock"] = [
			{
				"item": f"{d.item_code} - {d.item_name}",
				"stock_value": d.stock_value,
				"recovery_value": d.recovery_value,
				"age": d.age_years
			}
			for d in top_dead
		]
		
		# Top slow moving items
		top_slow = frappe.db.sql("""
			SELECT item_code, item_name, stock_value, velocity_90d, days_of_stock
			FROM `tabItem Classification`
			WHERE classification = 'SLOW'
			ORDER BY stock_value DESC
			LIMIT 5
		""", as_dict=1)
		
		data["top_slow_items"] = [
			{
				"item": f"{s.item_code} - {s.item_name}",
				"stock_value": s.stock_value,
				"velocity": s.velocity_90d,
				"dos": s.days_of_stock
			}
			for s in top_slow
		]
		
		# Forecast summary
		forecast = frappe.db.sql("""
			SELECT 
				SUM(forecast_30d) as total_forecast,
				SUM(qty_30d) as actual_sales,
				AVG(forecast_mad) as avg_mad
			FROM `tabDemand Pattern Analysis`
		""", as_dict=1)
		
		if forecast:
			data["forecast_summary"] = {
				"forecast_30d": forecast[0].total_forecast or 0,
				"actual_30d": forecast[0].actual_sales or 0,
				"avg_mad": forecast[0].avg_mad or 0
			}
		
		return data
		
	except Exception as e:
		frappe.log_error(title="Dashboard Data Error", message=str(e))
		return {"error": str(e)}

@frappe.whitelist()
def get_classification_chart():
	"""Get item classification distribution chart data"""
	data = frappe.db.sql("""
		SELECT classification, COUNT(*) as count
		FROM `tabItem Classification`
		GROUP BY classification
	""", as_dict=1)
	
	return {
		"labels": [d.classification for d in data],
		"datasets": [{
			"label": "Items",
			"data": [d.count for d in data],
			"backgroundColor": ["#4CAF50", "#FFC107", "#F44336", "#2196F3", "#FF9800"]
		}]
	}

@frappe.whitelist()
def get_demand_pattern_chart():
	"""Get demand pattern distribution chart data"""
	data = frappe.db.sql("""
		SELECT demand_pattern, COUNT(*) as count
		FROM `tabDemand Pattern Analysis`
		GROUP BY demand_pattern
	""", as_dict=1)
	
	return {
		"labels": [d.demand_pattern for d in data],
		"datasets": [{
			"label": "Items",
			"data": [d.count for d in data],
			"backgroundColor": ["#10B981", "#F59E0B", "#3B82F6", "#EF4444"]
		}]
	}

@frappe.whitelist()
def get_health_status_chart():
	"""Get new items health status chart data"""
	data = frappe.db.sql("""
		SELECT health_status, COUNT(*) as count
		FROM `tabNew Item Health Report`
		GROUP BY health_status
	""", as_dict=1)
	
	return {
		"labels": [d.health_status for d in data],
		"datasets": [{
			"label": "Items",
			"data": [d.count for d in data],
			"backgroundColor": ["#10B981", "#FF9800", "#F44336"]
		}]
	}
