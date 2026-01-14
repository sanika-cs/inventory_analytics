"""
Item Classification Model - Production Grade ML Pipeline
Handles DBSCAN clustering, KMeans, rule-based classification
For: uae.hydrotech inventory analytics system

Classification Types:
- FAST: High velocity, high revenue items (ABC-A, high turnover)
- SLOW: Low velocity, steady items (ABC-B/C, moderate turnover)
- MEDIUM: Mid-tier items
- NEW_ITEM: Recently launched (<90 days old)
- DEAD_STOCK: No sales for 180+ days
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from datetime import datetime, timedelta
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ItemClassificationModel:
    """
    Multi-algorithm item classification engine combining:
    1. DBSCAN clustering (anomaly detection + pattern recognition)
    2. KMeans clustering (velocity-based segmentation)
    3. Rule-based classification (business logic)
    4. Hybrid scoring system
    """

    def __init__(self, config=None):
        """Initialize with optional custom configuration"""
        self.config = config or self._default_config()
        self.scaler = StandardScaler()
        self.models_trained = False
        self.last_trained = None
        
    def _default_config(self):
        """Default configuration for UAEHydrotech"""
        return {
            "site": "uae.hydrotech",
            "currency": "AED",
            
            # FAST Classification Thresholds
            "fast_min_annual_sales_qty": 1000,
            "fast_min_turnover_ratio": 0.7,
            "fast_min_sales_velocity": 2.7,  # Units per day
            "fast_min_revenue_pct": 0.2,
            
            # SLOW Classification Thresholds
            "slow_max_sales_velocity": 2.7,
            "slow_min_consistency_score": 60,
            "slow_max_variability": 40,
            
            # NEW_ITEM Thresholds
            "new_item_max_age_days": 90,
            "new_item_learning_days": 180,
            
            # DEAD_STOCK Thresholds
            "dead_stock_min_days_no_sales": 180,
            "dead_stock_max_annual_sales": 10,
            
            # ML Model Parameters
            "dbscan_eps": 0.5,
            "dbscan_min_samples": 3,
            "kmeans_n_clusters": 3,
            "min_confidence_threshold": 0.65,
            
            # Holding Cost
            "holding_cost_pct_per_year": 0.20,  # 20% of inventory value per year
        }
    
    def classify_items(self, items_df, method="hybrid"):
        """
        Classify items using specified method
        
        Args:
            items_df: DataFrame with columns [item_code, annual_sales_qty, annual_sales_value, 
                                             current_stock, stock_value, item_age_days, 
                                             days_since_last_sale, created_date, last_sale_date]
            method: "dbscan", "kmeans", "rule_based", or "hybrid"
        
        Returns:
            DataFrame with classification results
        """
        logger.info(f"Starting item classification using {method} method")
        
        # Validate input
        items_df = items_df.copy()
        items_df = self._validate_and_prepare_data(items_df)
        
        if len(items_df) == 0:
            logger.warning("No valid items to classify")
            return pd.DataFrame()
        
        # Perform classifications
        if method == "dbscan":
            results = self._classify_dbscan(items_df)
        elif method == "kmeans":
            results = self._classify_kmeans(items_df)
        elif method == "rule_based":
            results = self._classify_rule_based(items_df)
        elif method == "hybrid":
            results = self._classify_hybrid(items_df)
        else:
            raise ValueError(f"Unknown classification method: {method}")
        
        self.last_trained = datetime.now()
        self.models_trained = True
        
        return results
    
    def _validate_and_prepare_data(self, df):
        """Validate and prepare data for classification"""
        required_cols = [
            'item_code', 'annual_sales_qty', 'annual_sales_value',
            'current_stock', 'stock_value', 'item_age_days',
            'days_since_last_sale', 'created_date'
        ]
        
        # Check for required columns
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            logger.warning(f"Missing columns: {missing}")
            df[missing] = 0
        
        # Clean data
        df = df.fillna(0)
        
        # Calculate derived metrics if not present
        if 'sales_velocity' not in df.columns:
            df['sales_velocity'] = df['annual_sales_qty'] / 365.0
        
        if 'turnover_ratio' not in df.columns:
            df['turnover_ratio'] = np.where(
                df['current_stock'] > 0,
                df['annual_sales_qty'] / df['current_stock'],
                0
            )
        
        if 'consistency_score' not in df.columns:
            df['consistency_score'] = 50  # Default, will be calculated properly
        
        # Remove items with zero annual sales for ML (except for DEAD_STOCK detection)
        df_valid = df[df['annual_sales_qty'] > 0].copy()
        
        return df_valid
    
    def _classify_dbscan(self, df):
        """
        DBSCAN Clustering - Density-based classification
        Groups similar items, identifies outliers (DEAD_STOCK, exceptional FAST items)
        """
        logger.info("Running DBSCAN clustering")
        
        # Prepare features for clustering
        features = df[[
            'sales_velocity',
            'turnover_ratio',
            'days_since_last_sale',
            'annual_sales_value'
        ]].values
        
        # Standardize features
        features_scaled = self.scaler.fit_transform(features)
        
        # Apply DBSCAN
        dbscan = DBSCAN(
            eps=self.config['dbscan_eps'],
            min_samples=self.config['dbscan_min_samples']
        )
        clusters = dbscan.fit_predict(features_scaled)
        
        df['cluster'] = clusters
        df['outlier'] = clusters == -1
        
        # Assign classifications based on clusters
        results = []
        for idx, row in df.iterrows():
            cluster_items = df[df['cluster'] == row['cluster']]
            
            classification = self._determine_classification_from_cluster(
                row, cluster_items
            )
            
            results.append(self._build_result_record(row, classification, "DBSCAN_CLUSTERING"))
        
        return pd.DataFrame(results)
    
    def _classify_kmeans(self, df):
        """
        KMeans Clustering - Velocity-based segmentation
        Groups items into velocity tiers: FAST, MEDIUM, SLOW
        """
        logger.info("Running KMeans clustering")
        
        # Prepare features
        features = df[[
            'sales_velocity',
            'turnover_ratio',
            'annual_sales_value'
        ]].values
        
        # Standardize
        features_scaled = self.scaler.fit_transform(features)
        
        # Apply KMeans
        kmeans = KMeans(
            n_clusters=self.config['kmeans_n_clusters'],
            random_state=42,
            n_init=10
        )
        df['cluster'] = kmeans.fit_predict(features_scaled)
        
        # Evaluate quality
        silhouette_avg = silhouette_score(features_scaled, df['cluster'])
        logger.info(f"KMeans Silhouette Score: {silhouette_avg:.3f}")
        
        # Assign classifications
        results = []
        for idx, row in df.iterrows():
            cluster_items = df[df['cluster'] == row['cluster']]
            avg_velocity = cluster_items['sales_velocity'].mean()
            
            if avg_velocity > self.config['fast_min_sales_velocity']:
                classification = 'FAST'
                confidence = min(95, 70 + (avg_velocity / 10))
            elif avg_velocity > 1.0:
                classification = 'MEDIUM'
                confidence = 75
            else:
                classification = 'SLOW'
                confidence = 75
            
            results.append(self._build_result_record(row, classification, "KMEANS_CLUSTERING", confidence))
        
        return pd.DataFrame(results)
    
    def _classify_rule_based(self, df):
        """
        Rule-based classification - Deterministic business logic
        Uses thresholds and equations to classify items
        """
        logger.info("Running rule-based classification")
        
        results = []
        for idx, row in df.iterrows():
            classification, confidence, reason = self._apply_business_rules(row)
            result = self._build_result_record(row, classification, "RULE_BASED", confidence)
            result['classification_reason'] = reason
            results.append(result)
        
        return pd.DataFrame(results)
    
    def _classify_hybrid(self, df):
        """
        Hybrid approach - Combines all methods with weighted voting
        1. Check rule-based first (deterministic rules)
        2. If borderline, use ML models
        3. Weight all votes with confidence
        """
        logger.info("Running hybrid classification (ensemble method)")
        
        results = []
        
        for idx, row in df.iterrows():
            # Step 1: Rule-based classification
            rule_class, rule_conf, rule_reason = self._apply_business_rules(row)
            
            # If high confidence rule-based classification, use it
            if rule_conf > 0.90:
                result = self._build_result_record(row, rule_class, "HYBRID", rule_conf)
                result['classification_reason'] = rule_reason
                results.append(result)
                continue
            
            # Step 2: Get DBSCAN classification
            # Create mini-dataset for DBSCAN
            mini_df = pd.DataFrame([row])
            dbscan_result = self._classify_dbscan(mini_df)
            if len(dbscan_result) > 0:
                dbscan_class = dbscan_result.iloc[0]['classification_type']
                dbscan_conf = dbscan_result.iloc[0]['classification_confidence'] / 100
            else:
                dbscan_class = rule_class
                dbscan_conf = 0.5
            
            # Step 3: Ensemble voting with weights
            votes = {
                rule_class: rule_conf * 0.5,  # Rule-based: 50% weight
                dbscan_class: dbscan_conf * 0.35,  # DBSCAN: 35% weight
            }
            
            # Add KMeans vote if applicable
            if row['sales_velocity'] > self.config['fast_min_sales_velocity']:
                votes['FAST'] = votes.get('FAST', 0) + 0.15
            
            # Winner is class with highest vote
            final_class = max(votes, key=votes.get)
            final_conf = (votes[final_class] / sum(votes.values())) * 100
            
            result = self._build_result_record(row, final_class, "HYBRID", final_conf)
            result['classification_reason'] = f"Ensemble: {rule_class}({rule_conf:.0%}) + DBSCAN({dbscan_conf:.0%}) → {final_class}"
            results.append(result)
        
        return pd.DataFrame(results)
    
    def _apply_business_rules(self, row):
        """
        Apply business rules for classification
        
        Returns:
            (classification, confidence, reason)
        """
        # Rule 1: NEW_ITEM (highest priority)
        if row['item_age_days'] < self.config['new_item_max_age_days']:
            return 'NEW_ITEM', 0.99, f"Item age {row['item_age_days']} days < {self.config['new_item_max_age_days']} threshold"
        
        # Rule 2: DEAD_STOCK (high priority)
        if (row['days_since_last_sale'] > self.config['dead_stock_min_days_no_sales'] or
            row['annual_sales_qty'] < self.config['dead_stock_max_annual_sales']):
            return 'DEAD_STOCK', 0.95, f"No sales for {row['days_since_last_sale']} days (threshold: {self.config['dead_stock_min_days_no_sales']})"
        
        # Rule 3: FAST (high velocity + high revenue)
        if (row['sales_velocity'] > self.config['fast_min_sales_velocity'] and
            row['turnover_ratio'] > self.config['fast_min_turnover_ratio']):
            confidence = min(99, 70 + (row['sales_velocity'] * 5) + (row['turnover_ratio'] * 10))
            return 'FAST', confidence / 100, f"Velocity {row['sales_velocity']:.2f} units/day, Turnover {row['turnover_ratio']:.2f}"
        
        # Rule 4: SLOW (low velocity + consistent demand)
        if (row['sales_velocity'] < 0.5 and
            row['days_since_last_sale'] < 60):
            return 'SLOW', 0.85, f"Low velocity ({row['sales_velocity']:.2f} units/day) but consistent (last sale {row['days_since_last_sale']} days ago)"
        
        # Rule 5: MEDIUM (default for mid-range items)
        return 'MEDIUM', 0.75, "Mid-range item characteristics"
    
    def _determine_classification_from_cluster(self, row, cluster_items):
        """Determine classification based on DBSCAN cluster characteristics"""
        if row['outlier']:
            # Outliers are typically DEAD_STOCK or exceptional FAST items
            if row['days_since_last_sale'] > 150:
                return 'DEAD_STOCK'
            elif row['sales_velocity'] > self.config['fast_min_sales_velocity'] * 1.5:
                return 'FAST'
            else:
                return 'SLOW'
        
        # Normal cluster member
        avg_velocity = cluster_items['sales_velocity'].mean()
        if avg_velocity > self.config['fast_min_sales_velocity']:
            return 'FAST'
        elif avg_velocity > 1.0:
            return 'MEDIUM'
        else:
            return 'SLOW'
    
    def _build_result_record(self, row, classification, method, confidence=None):
        """Build a classification result record"""
        
        if confidence is None:
            confidence = 75  # Default
        
        # Calculate recommended action
        recommended_action = self._recommend_action(row, classification)
        
        # Calculate holding cost
        holding_cost = row.get('stock_value', 0) * self.config['holding_cost_pct_per_year']
        
        return {
            'item_code': row.get('item_code', ''),
            'item_name': row.get('item_name', ''),
            'uom': row.get('uom', ''),
            'classification_type': classification,
            'classification_confidence': int(confidence),
            'classification_method': method,
            'annual_sales_qty': row.get('annual_sales_qty', 0),
            'annual_sales_value': row.get('annual_sales_value', 0),
            'sales_velocity': row.get('sales_velocity', 0),
            'turnover_ratio': row.get('turnover_ratio', 0),
            'holding_cost_annually': holding_cost,
            'current_stock': row.get('current_stock', 0),
            'stock_value': row.get('stock_value', 0),
            'days_of_stock': self._calculate_dos(row),
            'abc_category': self._determine_abc_category(row),
            'consistency_score': row.get('consistency_score', 50),
            'demand_variability': row.get('demand_variability', 0),
            'days_since_last_sale': row.get('days_since_last_sale', 0),
            'last_sale_date': row.get('last_sale_date', ''),
            'item_age_days': row.get('item_age_days', 0),
            'first_sale_date': row.get('first_sale_date', ''),
            'days_to_first_sale': row.get('days_to_first_sale', 0),
            'dormancy_status': self._determine_dormancy_status(row),
            'new_item_status': self._determine_new_item_status(row),
            'recommended_action': recommended_action['action'],
            'action_priority': recommended_action['priority'],
            'expected_impact': recommended_action['impact'],
            'model_version': '1.0.0-uae.hydrotech',
            'analysis_date': datetime.now().isoformat(),
        }
    
    def _calculate_dos(self, row):
        """Calculate Days Of Stock"""
        if row.get('sales_velocity', 0) > 0:
            return row.get('current_stock', 0) / row['sales_velocity']
        return 0
    
    def _determine_abc_category(self, row):
        """Determine ABC category based on revenue"""
        # This would be determined relative to total portfolio (simplified here)
        annual_value = row.get('annual_sales_value', 0)
        if annual_value > 100000:
            return 'A'
        elif annual_value > 20000:
            return 'B'
        else:
            return 'C'
    
    def _determine_dormancy_status(self, row):
        """Determine dormancy status based on days since last sale"""
        days = row.get('days_since_last_sale', 0)
        if days < 90:
            return 'ACTIVE'
        elif days < 180:
            return 'SLEEPY'
        elif days < 365:
            return 'DORMANT'
        else:
            return 'DEAD'
    
    def _determine_new_item_status(self, row):
        """Determine new item status based on age"""
        age = row.get('item_age_days', 0)
        if age < 30:
            return 'LAUNCH'
        elif age < 90:
            return 'LEARNING'
        elif age < 180:
            return 'GRADUATION'
        else:
            return 'ESTABLISHED'
    
    def _recommend_action(self, row, classification):
        """Generate action recommendation based on classification"""
        priority = 1
        action = 'MAINTAIN_STOCK'
        impact = 0
        
        if classification == 'FAST':
            action = 'INCREASE_STOCK'
            priority = 8
            impact = row.get('annual_sales_value', 0) * 0.10  # 10% increase potential
        
        elif classification == 'SLOW':
            dos = self._calculate_dos(row)
            if dos > 180:
                action = 'REDUCE_STOCK'
                priority = 5
                impact = -row.get('holding_cost_annually', 0) * 0.5
            else:
                action = 'MAINTAIN_STOCK'
                priority = 2
                impact = 0
        
        elif classification == 'DEAD_STOCK':
            action = 'LIQUIDATION'
            priority = 10
            impact = row.get('stock_value', 0) * 0.3  # Recover 30% through liquidation
        
        elif classification == 'NEW_ITEM':
            action = 'MARKET_MORE'
            priority = 7
            impact = row.get('annual_sales_value', 0) * 0.20  # Expected 20% growth
        
        return {
            'action': action,
            'priority': priority,
            'impact': impact
        }


def create_sample_data():
    """Create sample dataset for testing"""
    return pd.DataFrame({
        'item_code': ['HYD-001', 'HYD-002', 'HYD-003', 'HYD-004', 'HYD-005'],
        'item_name': ['Pump A', 'Valve B', 'Filter C', 'Seal D', 'Gasket E'],
        'uom': ['PCS', 'PCS', 'PCS', 'PCS', 'PCS'],
        'annual_sales_qty': [2500, 150, 800, 50, 1200],
        'annual_sales_value': [125000, 15000, 24000, 5000, 36000],
        'current_stock': [200, 100, 150, 500, 300],
        'stock_value': [10000, 10000, 4500, 25000, 9000],
        'item_age_days': [400, 200, 600, 30, 25],
        'days_since_last_sale': [2, 60, 200, 350, 1],
        'created_date': ['2023-01-01'] * 5,
        'sales_velocity': [6.8, 0.41, 2.19, 0.14, 3.29],
        'turnover_ratio': [12.5, 1.5, 5.3, 0.1, 4.0],
        'consistency_score': [85, 70, 50, 20, 80],
        'demand_variability': [15, 25, 45, 80, 20],
    })


if __name__ == "__main__":
    # Test the model
    model = ItemClassificationModel()
    
    test_data = create_sample_data()
    print("Sample Data:\n", test_data)
    
    # Test different methods
    for method in ["rule_based", "dbscan", "kmeans", "hybrid"]:
        print(f"\n{'='*80}")
        print(f"Classification using {method.upper()} method:")
        print(f"{'='*80}")
        
        results = model.classify_items(test_data, method=method)
        print(results[['item_code', 'classification_type', 'classification_confidence', 
                       'recommended_action', 'action_priority']])
