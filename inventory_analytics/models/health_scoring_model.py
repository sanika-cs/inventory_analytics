"""
New Items Health Scoring Model - Composite Health Metric
Production-grade health scoring for new product launches

For: uae.hydrotech inventory analytics
Features:
- 4-weighted component health score (0-100)
- Life stage tracking (LAUNCH → LEARNING → GRADUATION → ESTABLISHED)
- Early warning system for failing items
- Growth analysis and trend detection
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class HealthScoringModel:
    """
    New Items Health Score Model
    Composite metric combining 4 components with weighted scoring
    """
    
    def __init__(self, config=None):
        self.config = config or self._default_config()
    
    def _default_config(self):
        """Default health scoring configuration"""
        return {
            'site': 'uae.hydrotech',
            'currency': 'AED',
            
            # Health Score Weights (must sum to 1.0)
            'weight_sales_performance': 0.40,        # 40% - Sales vs targets
            'weight_customer_acquisition': 0.30,     # 30% - Customer growth
            'weight_stock_adequacy': 0.20,           # 20% - Right inventory level
            'weight_growth_trend': 0.10,             # 10% - Week-over-week growth
            
            # Sales Performance Thresholds
            'target_sales_pct_excellent': 1.20,      # > 120% of target = excellent
            'target_sales_pct_good': 0.95,           # 95-120% = good
            'target_sales_pct_fair': 0.70,           # 70-95% = fair
            'target_sales_pct_poor': 0.50,           # 50-70% = poor
            'target_sales_pct_critical': 0.30,       # < 30% = critical
            
            # Customer Acquisition Thresholds
            'min_customers_excellent': 50,           # 50+ customers = excellent
            'min_customers_good': 30,                # 30-50 = good
            'min_customers_fair': 15,                # 15-30 = fair
            'min_customers_poor': 5,                 # 5-15 = poor
            'min_customers_critical': 0,             # 0-5 = critical
            
            # Stock Adequacy (Days of Stock)
            'dos_optimal_min': 7,                    # Optimal: 7-60 days
            'dos_optimal_max': 60,
            'dos_warning_max': 90,                   # Warning: 60-90 days
            'dos_critical_max': 180,                 # Critical: > 90 days
            
            # Growth Trend
            'growth_excellent': 0.20,                # > 20% WoW = excellent
            'growth_good': 0.10,                     # 10-20% = good
            'growth_fair': 0.00,                     # 0-10% = fair (stable)
            'growth_poor': -0.10,                    # -10-0% = poor (declining)
            'growth_critical': -0.20,                # < -20% = critical (collapsing)
            
            # Life Stage Definitions (days)
            'launch_max_days': 30,                   # LAUNCH: < 30 days
            'learning_max_days': 90,                 # LEARNING: 30-90 days
            'graduation_max_days': 180,              # GRADUATION: 90-180 days
            # ESTABLISHED: > 180 days
            
            # Health Status Thresholds
            'health_critical_max': 30,               # 0-30 = CRITICAL
            'health_at_risk_max': 60,                # 30-60 = AT_RISK
            'health_healthy_min': 80,                # 80-100 = HEALTHY
            # 60-80 = CAUTION
        }
    
    def calculate_health_score(self, item_data):
        """
        Calculate composite health score for a new item
        
        Args:
            item_data: Dict with [
                item_code, item_name, item_age_days,
                actual_sales_qty, target_sales_qty,
                unique_customers, repeat_customers,
                current_stock, stock_value,
                avg_monthly_sales,
                sales_last_week, sales_prior_week,
                launch_date
            ]
        
        Returns:
            Dict with health_score, status, components, trends, recommendations
        """
        
        logger.info(f"Calculating health score for {item_data.get('item_code')}")
        
        # Calculate component scores
        sales_component = self._score_sales_performance(item_data)
        customer_component = self._score_customer_acquisition(item_data)
        stock_component = self._score_stock_adequacy(item_data)
        growth_component = self._score_growth_trend(item_data)
        
        # Calculate weighted composite score
        health_score = (
            (sales_component['score'] * self.config['weight_sales_performance']) +
            (customer_component['score'] * self.config['weight_customer_acquisition']) +
            (stock_component['score'] * self.config['weight_stock_adequacy']) +
            (growth_component['score'] * self.config['weight_growth_trend'])
        )
        
        # Determine health status
        health_status = self._get_health_status(health_score)
        
        # Determine life stage
        life_stage = self._get_life_stage(item_data.get('item_age_days', 0))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            health_score, health_status, life_stage, item_data
        )
        
        result = {
            'item_code': item_data.get('item_code'),
            'item_name': item_data.get('item_name'),
            'health_score': int(round(health_score)),
            'health_status': health_status,
            'life_stage': life_stage,
            'item_age_days': item_data.get('item_age_days', 0),
            
            # Component scores
            'sales_performance_score': int(round(sales_component['score'])),
            'sales_performance_reason': sales_component['reason'],
            
            'customer_acquisition_score': int(round(customer_component['score'])),
            'customer_acquisition_reason': customer_component['reason'],
            
            'stock_adequacy_score': int(round(stock_component['score'])),
            'stock_adequacy_reason': stock_component['reason'],
            
            'growth_trend_score': int(round(growth_component['score'])),
            'growth_trend_reason': growth_component['reason'],
            
            # Metrics
            'total_customers': item_data.get('unique_customers', 0),
            'repeat_customers_pct': (
                (item_data.get('repeat_customers', 0) / max(item_data.get('unique_customers', 1), 1)) * 100
            ),
            'sales_vs_target_pct': (
                (item_data.get('actual_sales_qty', 0) / max(item_data.get('target_sales_qty', 1), 1)) * 100
            ),
            'stock_adequacy_dos': self._calculate_dos(item_data),
            'growth_trend_pct': self._calculate_growth_trend(item_data),
            
            # Recommendations
            'recommended_action': recommendations['action'],
            'action_priority': recommendations['priority'],
            'key_metrics': recommendations['metrics'],
            'warning_flags': recommendations['warnings']
        }
        
        return result
    
    def _score_sales_performance(self, item_data):
        """
        Score 1: Sales Performance (40% weight)
        Actual vs Target achievement
        """
        
        actual = item_data.get('actual_sales_qty', 0)
        target = item_data.get('target_sales_qty', 1)
        
        sales_pct = actual / target if target > 0 else 0
        
        # Scale to 0-100
        if sales_pct >= self.config['target_sales_pct_excellent']:
            score = 100
            reason = f"Excellent: {sales_pct*100:.0f}% of target (>${self.config['target_sales_pct_excellent']*100:.0f}%)"
        elif sales_pct >= self.config['target_sales_pct_good']:
            score = 85
            reason = f"Good: {sales_pct*100:.0f}% of target ({self.config['target_sales_pct_good']*100:.0f}%-{self.config['target_sales_pct_excellent']*100:.0f}%)"
        elif sales_pct >= self.config['target_sales_pct_fair']:
            score = 60
            reason = f"Fair: {sales_pct*100:.0f}% of target ({self.config['target_sales_pct_fair']*100:.0f}%-{self.config['target_sales_pct_good']*100:.0f}%)"
        elif sales_pct >= self.config['target_sales_pct_poor']:
            score = 35
            reason = f"Poor: {sales_pct*100:.0f}% of target ({self.config['target_sales_pct_poor']*100:.0f}%-{self.config['target_sales_pct_fair']*100:.0f}%)"
        elif sales_pct >= self.config['target_sales_pct_critical']:
            score = 15
            reason = f"Critical: {sales_pct*100:.0f}% of target ({self.config['target_sales_pct_critical']*100:.0f}%-{self.config['target_sales_pct_poor']*100:.0f}%)"
        else:
            score = 0
            reason = f"Failing: {sales_pct*100:.0f}% of target (<{self.config['target_sales_pct_critical']*100:.0f}%)"
        
        return {'score': score, 'reason': reason}
    
    def _score_customer_acquisition(self, item_data):
        """
        Score 2: Customer Acquisition (30% weight)
        Unique customers and retention
        """
        
        unique_customers = item_data.get('unique_customers', 0)
        repeat_customers = item_data.get('repeat_customers', 0)
        
        # Scale to 0-100 based on unique customer count
        if unique_customers >= self.config['min_customers_excellent']:
            score = 100
            reason = f"Excellent: {unique_customers} unique customers (>{self.config['min_customers_excellent']})"
        elif unique_customers >= self.config['min_customers_good']:
            score = 85
            reason = f"Good: {unique_customers} unique customers"
        elif unique_customers >= self.config['min_customers_fair']:
            score = 60
            reason = f"Fair: {unique_customers} unique customers"
        elif unique_customers >= self.config['min_customers_poor']:
            score = 35
            reason = f"Poor: {unique_customers} unique customers"
        else:
            score = 15
            reason = f"Critical: {unique_customers} unique customers (<{self.config['min_customers_poor']})"
        
        # Bonus for retention
        if unique_customers > 0:
            retention_pct = repeat_customers / unique_customers
            if retention_pct > 0.5:
                score = min(100, score + 15)
                reason += f" | {retention_pct*100:.0f}% repeat customers (retention bonus)"
        
        return {'score': min(100, score), 'reason': reason}
    
    def _score_stock_adequacy(self, item_data):
        """
        Score 3: Stock Adequacy (20% weight)
        Right inventory level (not too much, not too little)
        """
        
        dos = self._calculate_dos(item_data)
        
        # Optimal range: 7-60 days
        if self.config['dos_optimal_min'] <= dos <= self.config['dos_optimal_max']:
            score = 100
            reason = f"Optimal: {dos:.0f} days of stock ({self.config['dos_optimal_min']}-{self.config['dos_optimal_max']} day range)"
        elif dos < self.config['dos_optimal_min']:
            # Stock too low
            stock_out_risk = ((self.config['dos_optimal_min'] - dos) / self.config['dos_optimal_min']) * 100
            score = max(30, 100 - stock_out_risk * 2)
            reason = f"Low Stock: {dos:.0f} days (<{self.config['dos_optimal_min']} days) - stockout risk"
        elif dos <= self.config['dos_warning_max']:
            # Stock moderately high
            score = 75
            reason = f"Caution: {dos:.0f} days of stock ({self.config['dos_optimal_max']}-{self.config['dos_warning_max']} day range)"
        elif dos <= self.config['dos_critical_max']:
            # Stock high
            score = 45
            reason = f"High Stock: {dos:.0f} days ({self.config['dos_warning_max']}-{self.config['dos_critical_max']} days) - high holding cost"
        else:
            # Stock very high
            score = 15
            reason = f"Excessive: {dos:.0f} days (>{self.config['dos_critical_max']} days) - excess inventory risk"
        
        return {'score': max(0, score), 'reason': reason}
    
    def _score_growth_trend(self, item_data):
        """
        Score 4: Growth Trend (10% weight)
        Week-over-week sales growth
        """
        
        growth_pct = self._calculate_growth_trend(item_data)
        
        # Scale to 0-100
        if growth_pct >= self.config['growth_excellent']:
            score = 100
            trend = "📈 Excellent Growth"
            reason = f"Excellent: +{growth_pct*100:.1f}% WoW growth (>{self.config['growth_excellent']*100:.0f}%)"
        elif growth_pct >= self.config['growth_good']:
            score = 85
            trend = "📈 Good Growth"
            reason = f"Good: +{growth_pct*100:.1f}% WoW growth"
        elif growth_pct >= self.config['growth_fair']:
            score = 70
            trend = "➡️ Stable"
            reason = f"Stable: {growth_pct*100:.1f}% WoW growth (0-{self.config['growth_good']*100:.0f}%)"
        elif growth_pct >= self.config['growth_poor']:
            score = 45
            trend = "📉 Declining"
            reason = f"Declining: {growth_pct*100:.1f}% WoW growth ({self.config['growth_poor']*100:.0f}%-0%)"
        elif growth_pct >= self.config['growth_critical']:
            score = 20
            trend = "📉📉 Steep Decline"
            reason = f"Steep Decline: {growth_pct*100:.1f}% WoW growth"
        else:
            score = 5
            trend = "⚠️ Collapsing"
            reason = f"Collapsing: {growth_pct*100:.1f}% WoW growth (<{self.config['growth_critical']*100:.0f}%)"
        
        return {'score': score, 'reason': reason}
    
    def _get_health_status(self, health_score):
        """Determine health status based on score"""
        if health_score <= self.config['health_critical_max']:
            return 'CRITICAL'
        elif health_score <= self.config['health_at_risk_max']:
            return 'AT_RISK'
        elif health_score < self.config['health_healthy_min']:
            return 'CAUTION'
        else:
            return 'HEALTHY'
    
    def _get_life_stage(self, item_age_days):
        """Determine life stage based on age"""
        if item_age_days <= self.config['launch_max_days']:
            return 'LAUNCH'
        elif item_age_days <= self.config['learning_max_days']:
            return 'LEARNING'
        elif item_age_days <= self.config['graduation_max_days']:
            return 'GRADUATION'
        else:
            return 'ESTABLISHED'
    
    def _calculate_dos(self, item_data):
        """Calculate Days of Stock"""
        current_stock = item_data.get('current_stock', 0)
        avg_monthly = item_data.get('avg_monthly_sales', 1)
        
        if avg_monthly > 0:
            return (current_stock / avg_monthly) * 30  # Convert to days
        return 0
    
    def _calculate_growth_trend(self, item_data):
        """Calculate week-over-week growth %"""
        sales_last_week = item_data.get('sales_last_week', 0)
        sales_prior_week = item_data.get('sales_prior_week', 1)
        
        if sales_prior_week > 0:
            return (sales_last_week - sales_prior_week) / sales_prior_week
        return 0
    
    def _generate_recommendations(self, health_score, health_status, life_stage, item_data):
        """Generate action recommendations"""
        
        recommendations = {
            'action': '',
            'priority': 5,
            'metrics': [],
            'warnings': []
        }
        
        # High priority for critical or at-risk items
        if health_status == 'CRITICAL':
            recommendations['action'] = 'URGENT_INTERVENTION_REQUIRED'
            recommendations['priority'] = 10
            recommendations['warnings'].append('Health score < 30 - item may fail')
            recommendations['warnings'].append('Review launch strategy and market positioning')
            recommendations['warnings'].append('Consider product adjustments or discontinuation')
        
        elif health_status == 'AT_RISK':
            recommendations['action'] = 'CLOSE_MONITORING_REQUIRED'
            recommendations['priority'] = 8
            recommendations['warnings'].append('Health score 30-60 - monitor closely')
            recommendations['warnings'].append('Increase marketing efforts')
            recommendations['warnings'].append('Gather customer feedback for improvements')
        
        elif health_status == 'CAUTION':
            recommendations['action'] = 'OPTIMIZE_INVENTORY'
            recommendations['priority'] = 5
            recommendations['warnings'].append('Health score 60-80 - needs optimization')
        
        else:  # HEALTHY
            recommendations['action'] = 'MAINTAIN_CURRENT_STRATEGY'
            recommendations['priority'] = 2
        
        # Life stage specific recommendations
        if life_stage == 'LAUNCH':
            recommendations['action'] = 'AGGRESSIVE_MARKETING'
            recommendations['priority'] = max(recommendations['priority'], 7)
            recommendations['metrics'].append('Focus on customer acquisition')
            recommendations['metrics'].append('Expected: 20-30% weekly growth')
        
        elif life_stage == 'LEARNING':
            recommendations['action'] = 'MARKET_EXPANSION'
            recommendations['priority'] = max(recommendations['priority'], 6)
            recommendations['metrics'].append('Scale marketing campaigns')
            recommendations['metrics'].append('Target new customer segments')
        
        elif life_stage == 'GRADUATION':
            recommendations['action'] = 'OPTIMIZE_SUPPLY_CHAIN'
            recommendations['priority'] = max(recommendations['priority'], 4)
            recommendations['metrics'].append('Optimize ordering and inventory')
            recommendations['metrics'].append('Stabilize supply from suppliers')
        
        else:  # ESTABLISHED
            recommendations['action'] = 'MAINTAIN_STANDARD_OPERATIONS'
            recommendations['priority'] = 2
            recommendations['metrics'].append('Monitor for market changes')
            recommendations['metrics'].append('Maintain competitive pricing')
        
        return recommendations


def create_sample_health_data():
    """Create sample health scoring data"""
    return pd.DataFrame({
        'item_code': ['HYD-001', 'HYD-002', 'HYD-003', 'HYD-004'],
        'item_name': ['Pump A', 'Valve B', 'Filter C', 'Seal D'],
        'item_age_days': [15, 45, 120, 200],
        'actual_sales_qty': [500, 280, 400, 800],
        'target_sales_qty': [400, 350, 500, 1000],
        'unique_customers': [35, 22, 45, 65],
        'repeat_customers': [15, 5, 20, 45],
        'current_stock': [200, 350, 800, 1200],
        'stock_value': [50000, 35000, 80000, 120000],
        'avg_monthly_sales': [150, 100, 200, 300],
        'sales_last_week': [60, 20, 50, 120],
        'sales_prior_week': [55, 35, 48, 110],
    })


if __name__ == "__main__":
    model = HealthScoringModel()
    
    test_data = create_sample_health_data()
    
    print("=" * 100)
    print("New Items Health Scoring Results")
    print("=" * 100)
    
    for idx, row in test_data.iterrows():
        result = model.calculate_health_score(row.to_dict())
        print(f"\n{result['item_code']} - {result['item_name']}")
        print(f"  Health Score: {result['health_score']}/100 ({result['health_status']})")
        print(f"  Life Stage: {result['life_stage']}")
        print(f"  Sales: {result['sales_performance_score']}/100 - {result['sales_performance_reason']}")
        print(f"  Customers: {result['customer_acquisition_score']}/100 - {result['unique_customers']} customers")
        print(f"  Stock: {result['stock_adequacy_score']}/100 - {result['stock_adequacy_dos']:.0f} DOS")
        print(f"  Growth: {result['growth_trend_score']}/100 - {result['growth_trend_pct']*100:.1f}% WoW")
        print(f"  Action: {result['recommended_action']} (Priority {result['action_priority']}/10)")
