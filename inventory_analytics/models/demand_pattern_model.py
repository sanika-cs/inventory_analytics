"""
Demand Pattern Analysis Model - SBC Method (Syntetos-Boylan-Croston)
Production-grade demand forecasting with safety stock calculations

For: uae.hydrotech inventory analytics
Features:
- SMOOTH vs ERRATIC vs INTERMITTENT vs LUMPY classification
- ADI (Average Demand Interval) & CV² (Coefficient of Variation²) metrics
- Automatic forecasting method selection
- Safety stock & ROP calculation
- Order recommendations
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
import logging
import json

logger = logging.getLogger(__name__)


class DemandPatternModel:
    """
    SBC (Syntetos-Boylan-Croston) Demand Pattern Classification
    Classifies items into 4 demand patterns and generates forecasts
    """
    
    def __init__(self, config=None):
        self.config = config or self._default_config()
        self.scaler = StandardScaler()
    
    def _default_config(self):
        """Default SBC configuration"""
        return {
            'site': 'uae.hydrotech',
            'currency': 'AED',
            
            # SBC Thresholds
            'adi_threshold': 1.32,          # ADI > 1.32 = Intermittent
            'cv2_threshold': 0.49,          # CV² > 0.49 = Erratic
            
            # Demand Pattern classification
            'smooth_adi_max': 1.32,
            'smooth_cv2_max': 0.49,
            
            'erratic_adi_max': 1.32,
            'erratic_cv2_min': 0.49,
            
            'intermittent_adi_min': 1.32,
            'intermittent_cv2_max': 0.49,
            
            'lumpy_adi_min': 1.32,
            'lumpy_cv2_min': 0.49,
            
            # Forecast parameters
            'forecast_periods': 30,          # 30-day forecast
            'service_level': 0.95,           # 95% service level
            'lead_time_days': 7,             # Default lead time
            'demand_history_days': 365,      # Use 365 days history
            
            # Safety stock
            'safety_stock_multiplier_smooth': 1.65,      # Z-score for 95% service level
            'safety_stock_multiplier_erratic': 2.33,
            'safety_stock_multiplier_intermittent': 2.33,
            'safety_stock_multiplier_lumpy': 2.58,
        }
    
    def classify_demand_patterns(self, items_df):
        """
        Classify items into demand patterns using SBC method
        
        Args:
            items_df: DataFrame with columns [item_code, monthly_sales_qty (12 months)]
        
        Returns:
            DataFrame with demand pattern results
        """
        logger.info("Starting demand pattern classification using SBC method")
        
        items_df = items_df.copy()
        
        results = []
        
        for idx, row in items_df.iterrows():
            # Calculate ADI and CV²
            monthly_sales = [row.get(f'month_{i}', 0) for i in range(1, 13)]
            
            adi, cv2, classification = self._classify_sbc(monthly_sales)
            
            # Generate forecast
            forecast_data = self._generate_forecast(monthly_sales, classification)
            
            # Calculate safety stock and ROP
            rop_data = self._calculate_rop(monthly_sales, classification)
            
            # Get recommendations
            recommendations = self._get_recommendations(row, classification, forecast_data)
            
            result = {
                'item_code': row.get('item_code'),
                'item_name': row.get('item_name'),
                'demand_pattern': classification,
                'adi': adi,
                'cv_squared': cv2,
                'avg_monthly_demand': np.mean(monthly_sales),
                'std_dev_demand': np.std(monthly_sales),
                'demand_variability': (np.std(monthly_sales) / np.mean(monthly_sales) * 100) if np.mean(monthly_sales) > 0 else 0,
                'forecast_30d': forecast_data['forecast_30d'],
                'confidence_interval_lower': forecast_data['ci_lower'],
                'confidence_interval_upper': forecast_data['ci_upper'],
                'forecast_method': forecast_data['method'],
                'reorder_point': rop_data['rop'],
                'safety_stock': rop_data['safety_stock'],
                'economic_order_qty': rop_data['eoq'],
                'recommended_order_qty': rop_data['recommended_qty'],
                'order_frequency': rop_data['order_frequency'],
                'recommendation': recommendations['action'],
                'recommendation_priority': recommendations['priority'],
            }
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def _classify_sbc(self, monthly_sales):
        """
        SBC Classification algorithm
        
        Returns:
            (ADI, CV², classification)
        """
        
        # Remove zeros for analysis
        non_zero_sales = [s for s in monthly_sales if s > 0]
        
        if not non_zero_sales:
            return 0, 0, 'LUMPY'
        
        # Calculate ADI (Average Demand Interval)
        # ADI = number of periods / number of periods with demand
        periods_with_demand = len(non_zero_sales)
        adi = 12 / periods_with_demand if periods_with_demand > 0 else 12
        
        # Calculate CV² (Coefficient of Variation²)
        mean_demand = np.mean(non_zero_sales)
        std_dev = np.std(non_zero_sales)
        cv = (std_dev / mean_demand) if mean_demand > 0 else 0
        cv2 = cv ** 2
        
        # SBC Classification
        if adi <= self.config['adi_threshold'] and cv2 <= self.config['cv2_threshold']:
            classification = 'SMOOTH'
        elif adi <= self.config['adi_threshold'] and cv2 > self.config['cv2_threshold']:
            classification = 'ERRATIC'
        elif adi > self.config['adi_threshold'] and cv2 <= self.config['cv2_threshold']:
            classification = 'INTERMITTENT'
        else:  # adi > 1.32 and cv2 > 0.49
            classification = 'LUMPY'
        
        return adi, cv2, classification
    
    def _generate_forecast(self, monthly_sales, classification):
        """
        Generate forecast based on demand pattern
        """
        
        data = {
            'method': '',
            'forecast_30d': 0,
            'ci_lower': 0,
            'ci_upper': 0,
        }
        
        avg_monthly = np.mean([s for s in monthly_sales if s > 0]) if any(monthly_sales) else 1
        
        if classification == 'SMOOTH':
            # Simple Moving Average for smooth demand
            data['forecast_30d'] = avg_monthly
            data['method'] = 'MOVING_AVERAGE'
            std_dev = np.std(monthly_sales)
            data['ci_lower'] = max(0, data['forecast_30d'] - 1.96 * std_dev)
            data['ci_upper'] = data['forecast_30d'] + 1.96 * std_dev
        
        elif classification == 'ERRATIC':
            # Weighted Average for erratic demand
            weights = [0.5, 0.3, 0.2]  # Recent weighted more
            recent = monthly_sales[-3:]
            data['forecast_30d'] = sum([recent[i] * weights[i] for i in range(min(3, len(recent)))])
            data['method'] = 'WEIGHTED_AVERAGE'
            data['ci_lower'] = max(0, data['forecast_30d'] * 0.5)
            data['ci_upper'] = data['forecast_30d'] * 1.5
        
        elif classification == 'INTERMITTENT':
            # Croston's method for intermittent demand
            non_zero = [s for s in monthly_sales if s > 0]
            if non_zero:
                data['forecast_30d'] = np.mean(non_zero) / len([s for s in monthly_sales if s > 0]) * 30
            data['method'] = 'CROSTONS'
            data['ci_lower'] = 0
            data['ci_upper'] = data['forecast_30d'] * 2
        
        elif classification == 'LUMPY':
            # Conservative forecast for lumpy demand
            data['forecast_30d'] = avg_monthly
            data['method'] = 'EXPONENTIAL_SMOOTHING'
            data['ci_lower'] = 0
            data['ci_upper'] = data['forecast_30d'] * 3
        
        return data
    
    def _calculate_rop(self, monthly_sales, classification):
        """
        Calculate Reorder Point (ROP) and Safety Stock
        ROP = (Average Daily Demand × Lead Time) + Safety Stock
        """
        
        avg_monthly = np.mean([s for s in monthly_sales if s > 0]) if any(monthly_sales) else 1
        avg_daily = avg_monthly / 30  # Convert to daily
        
        lead_time = self.config['lead_time_days']
        
        # Demand during lead time
        demand_during_lt = avg_daily * lead_time
        
        # Standard deviation for safety stock
        std_dev = np.std(monthly_sales)
        std_dev_lt = std_dev * np.sqrt(lead_time)
        
        # Select Z-score based on pattern
        z_scores = {
            'SMOOTH': self.config['safety_stock_multiplier_smooth'],
            'ERRATIC': self.config['safety_stock_multiplier_erratic'],
            'INTERMITTENT': self.config['safety_stock_multiplier_intermittent'],
            'LUMPY': self.config['safety_stock_multiplier_lumpy'],
        }
        
        z_score = z_scores.get(classification, 1.65)
        
        # Safety Stock
        safety_stock = z_score * std_dev_lt
        
        # ROP
        rop = demand_during_lt + safety_stock
        
        # Economic Order Quantity (EOQ)
        # EOQ = sqrt(2 * D * S / H)
        # D = annual demand, S = ordering cost, H = holding cost
        annual_demand = avg_monthly * 12
        ordering_cost = 50  # AED per order (assumption)
        holding_cost = 0.20  # 20% of unit value per year (assumption)
        
        eoq = np.sqrt((2 * annual_demand * ordering_cost) / (holding_cost * 1)) if annual_demand > 0 else 0
        
        # Order frequency
        if avg_monthly > 0:
            order_frequency = annual_demand / eoq if eoq > 0 else 12
        else:
            order_frequency = 0
        
        # Recommended order quantity (ROP + EOQ for next cycle)
        recommended_qty = max(eoq, rop)
        
        return {
            'rop': rop,
            'safety_stock': safety_stock,
            'eoq': eoq,
            'recommended_qty': recommended_qty,
            'order_frequency': order_frequency,
        }
    
    def _get_recommendations(self, row, classification, forecast_data):
        """Get action recommendations based on pattern"""
        
        recommendations = {
            'SMOOTH': {
                'action': 'REGULAR_ORDERING - Implement standard reorder cycle',
                'priority': 2,
                'details': [
                    'Stable demand allows for predictable ordering',
                    'Use ROP-based ordering system',
                    'Can negotiate long-term contracts with suppliers'
                ]
            },
            'ERRATIC': {
                'action': 'FLEXIBLE_ORDERING - Increase safety stock by 20-30%',
                'priority': 5,
                'details': [
                    'High demand variability requires buffer inventory',
                    'Monitor demand trends closely (weekly)',
                    'Consider multiple suppliers for flexibility'
                ]
            },
            'INTERMITTENT': {
                'action': 'PERIODIC_ORDERING - Use time-based ordering',
                'priority': 4,
                'details': [
                    'Sporadic demand but low variability',
                    'Implement periodic review ordering (every 4 weeks)',
                    'Keep minimum safety stock levels'
                ]
            },
            'LUMPY': {
                'action': 'SPECIAL_ORDERING - Collaborate on demand planning',
                'priority': 8,
                'details': [
                    'Highly unpredictable demand',
                    'Work with sales team on forecasts',
                    'Maintain high safety stock (40-50% above average)',
                    'Consider drop-shipping or make-to-order'
                ]
            }
        }
        
        return recommendations.get(classification, {'action': 'MAINTAIN_STOCK', 'priority': 5})


def create_sample_demand_data():
    """Create sample demand data for testing"""
    return pd.DataFrame({
        'item_code': ['HYD-001', 'HYD-002', 'HYD-003', 'HYD-004'],
        'item_name': ['Pump A', 'Valve B', 'Filter C', 'Seal D'],
        'month_1': [100, 50, 200, 10],
        'month_2': [110, 45, 190, 0],
        'month_3': [105, 55, 210, 50],
        'month_4': [120, 48, 200, 0],
        'month_5': [95, 52, 220, 0],
        'month_6': [115, 49, 180, 80],
        'month_7': [108, 51, 200, 0],
        'month_8': [112, 50, 210, 0],
        'month_9': [100, 48, 190, 120],
        'month_10': [110, 52, 200, 0],
        'month_11': [105, 49, 210, 0],
        'month_12': [115, 51, 195, 30],
    })


if __name__ == "__main__":
    model = DemandPatternModel()
    
    test_data = create_sample_demand_data()
    print("Sample Demand Data:\n", test_data)
    
    results = model.classify_demand_patterns(test_data)
    print("\n" + "="*100)
    print("Demand Pattern Classification Results:")
    print("="*100)
    print(results[['item_code', 'demand_pattern', 'adi', 'cv_squared', 'forecast_30d', 
                   'reorder_point', 'safety_stock', 'recommendation']].to_string())
