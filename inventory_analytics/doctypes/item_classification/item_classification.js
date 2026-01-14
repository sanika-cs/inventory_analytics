/**
 * Item Classification - JavaScript Handler
 * 
 * Frappe DocType handler for Item Classification
 * Features:
 * - Auto-loads item metrics from warehouse
 * - Runs ML classification on save
 * - Shows insights and recommendations
 * - Validates data quality
 * - Generates action items
 */

frappe.ui.form.on('Item Classification', {
    
    /**
     * Form Load - Initialize and fetch data
     */
    onload: function(frm) {
        console.log('Item Classification Form Loaded');
        
        // Set default values
        if (!frm.doc.analysis_date) {
            frm.set_value('analysis_date', frappe.datetime.now_datetime());
        }
        
        if (!frm.doc.model_version) {
            frm.set_value('model_version', '1.0.0-uae.hydrotech');
        }
        
        // Setup button groups
        setup_buttons(frm);
        setup_field_filters(frm);
    },
    
    /**
     * Item Code Change - Auto-fetch item details
     */
    item_code: function(frm) {
        if (frm.doc.item_code) {
            fetch_item_metrics(frm);
        }
    },
    
    /**
     * Before Save - Validate and run classification
     */
    before_save: function(frm) {
        // Validate required fields
        if (!frm.doc.item_code) {
            frappe.throw(__('Please select an item'));
        }
        
        if (!frm.doc.annual_sales_qty) {
            frappe.throw(__('Annual sales quantity is required'));
        }
        
        // Run classification
        run_classification(frm);
    },
    
    /**
     * After Save - Generate insights and recommendations
     */
    after_save: function(frm) {
        frappe.show_alert({
            message: __('Item Classification completed successfully'),
            indicator: 'green'
        });
        
        // Generate recommendations
        generate_recommendations(frm);
        
        // Refresh view
        frm.refresh();
    },
    
    /**
     * Validate button click
     */
    validate_data: function(frm) {
        frappe.call({
            method: 'inventory_analytics_app.doctypes.item_classification.item_classification.validate_item_data',
            args: {
                item_code: frm.doc.item_code
            },
            callback: function(r) {
                if (r.message) {
                    show_data_quality_report(r.message);
                }
            }
        });
    },
    
    /**
     * Run Classification button
     */
    run_classification: function(frm) {
        if (!frm.doc.item_code) {
            frappe.throw(__('Please select an item first'));
        }
        
        frappe.call({
            method: 'inventory_analytics_app.doctypes.item_classification.item_classification.run_classification',
            args: {
                item_code: frm.doc.item_code,
                method: 'hybrid'  // Use hybrid classification
            },
            callback: function(r) {
                if (r.message) {
                    const result = r.message;
                    
                    // Update form fields
                    frm.set_value({
                        'classification_type': result.classification_type,
                        'classification_confidence': result.classification_confidence,
                        'classification_method': result.classification_method,
                        'classification_reason': result.classification_reason,
                        'recommended_action': result.recommended_action,
                        'action_priority': result.action_priority,
                        'expected_impact': result.expected_impact,
                        'analysis_date': frappe.datetime.now_datetime(),
                    });
                    
                    // Show classification badge
                    show_classification_badge(frm);
                    
                    frappe.show_alert({
                        message: __(`Classification: <b>${result.classification_type}</b> (${result.classification_confidence}% confidence)`),
                        indicator: get_indicator_color(result.classification_type)
                    });
                }
            }
        });
    },
    
    /**
     * Fetch Current Stock button
     */
    fetch_current_stock: function(frm) {
        if (!frm.doc.item_code) {
            frappe.throw(__('Please select an item first'));
        }
        
        frappe.call({
            method: 'inventory_analytics_app.doctypes.item_classification.item_classification.get_item_stock',
            args: {
                item_code: frm.doc.item_code
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value({
                        'current_stock': r.message.qty,
                        'stock_value': r.message.value
                    });
                    
                    frappe.show_alert({
                        message: __(`Stock: ${r.message.qty} units, Value: AED ${r.message.value.toFixed(2)}`),
                        indicator: 'blue'
                    });
                }
            }
        });
    },
    
    /**
     * Generate Recommendations button
     */
    generate_insights: function(frm) {
        if (!frm.doc.classification_type) {
            frappe.throw(__('Please run classification first'));
        }
        
        frappe.call({
            method: 'inventory_analytics_app.doctypes.item_classification.item_classification.generate_insights',
            args: {
                doc: frm.doc
            },
            callback: function(r) {
                if (r.message) {
                    show_insights_dialog(r.message);
                }
            }
        });
    }
});


/**
 * Setup button group in form
 */
function setup_buttons(frm) {
    frm.add_custom_button(__('Validate Data'), function() {
        frm.call_method('validate_data');
    }).addClass('btn-info');
    
    frm.add_custom_button(__('Run Classification'), function() {
        frm.call_method('run_classification');
    }).addClass('btn-primary');
    
    frm.add_custom_button(__('Fetch Stock'), function() {
        frm.call_method('fetch_current_stock');
    }).addClass('btn-warning');
    
    frm.add_custom_button(__('Generate Insights'), function() {
        frm.call_method('generate_insights');
    }).addClass('btn-success');
}


/**
 * Setup field filters and dependencies
 */
function setup_field_filters(frm) {
    // Classification Type is read-only - set as read-only
    frm.set_df_property('classification_type', 'read_only', 1);
    frm.set_df_property('classification_confidence', 'read_only', 1);
    frm.set_df_property('classification_method', 'read_only', 1);
    frm.set_df_property('classification_reason', 'read_only', 1);
    
    // Show/hide sections based on classification
    frm.refresh_field('classification_type');
}


/**
 * Fetch item metrics from database
 */
function fetch_item_metrics(frm) {
    frappe.show_alert({
        message: __('Fetching item metrics...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'inventory_analytics_app.doctypes.item_classification.item_classification.get_item_metrics',
        args: {
            item_code: frm.doc.item_code
        },
        callback: function(r) {
            if (r.message) {
                const metrics = r.message;
                
                // Update all metrics
                frm.set_value({
                    'item_name': metrics.item_name,
                    'uom': metrics.uom,
                    'annual_sales_qty': metrics.annual_sales_qty,
                    'annual_sales_value': metrics.annual_sales_value,
                    'sales_velocity': metrics.sales_velocity,
                    'turnover_ratio': metrics.turnover_ratio,
                    'current_stock': metrics.current_stock,
                    'stock_value': metrics.stock_value,
                    'days_of_stock': metrics.days_of_stock,
                    'days_since_last_sale': metrics.days_since_last_sale,
                    'last_sale_date': metrics.last_sale_date,
                    'item_age_days': metrics.item_age_days,
                    'first_sale_date': metrics.first_sale_date,
                    'consistency_score': metrics.consistency_score,
                    'demand_variability': metrics.demand_variability,
                });
                
                frappe.show_alert({
                    message: __('Item metrics updated successfully'),
                    indicator: 'green'
                });
            }
        }
    });
}


/**
 * Run classification on the item
 */
function run_classification(frm) {
    frappe.call({
        method: 'inventory_analytics_app.doctypes.item_classification.item_classification.run_classification',
        args: {
            item_code: frm.doc.item_code,
            method: 'hybrid'
        },
        callback: function(r) {
            if (r.message) {
                const result = r.message;
                
                frm.set_value({
                    'classification_type': result.classification_type,
                    'classification_confidence': result.classification_confidence,
                    'classification_method': result.classification_method,
                    'classification_reason': result.classification_reason,
                    'recommended_action': result.recommended_action,
                    'action_priority': result.action_priority,
                    'expected_impact': result.expected_impact,
                    'analysis_date': frappe.datetime.now_datetime(),
                    'model_version': '1.0.0-uae.hydrotech',
                });
                
                show_classification_badge(frm);
            }
        }
    });
}


/**
 * Show classification badge with color
 */
function show_classification_badge(frm) {
    const classification = frm.doc.classification_type;
    const confidence = frm.doc.classification_confidence || 0;
    
    let badge_color = '#666';
    if (classification === 'FAST') badge_color = '#f44242';  // Red
    else if (classification === 'SLOW') badge_color = '#3498db';  // Blue
    else if (classification === 'MEDIUM') badge_color = '#f39c12';  // Orange
    else if (classification === 'DEAD_STOCK') badge_color = '#95a5a6';  // Gray
    else if (classification === 'NEW_ITEM') badge_color = '#2ecc71';  // Green
    
    frm.set_intro(`
        <div style="background: ${badge_color}; color: white; padding: 10px 15px; border-radius: 4px; margin-bottom: 10px;">
            <b>${classification}</b> | Confidence: ${confidence}% | ${frm.doc.classification_reason || 'Analysis pending'}
        </div>
    `);
}


/**
 * Generate insights and recommendations
 */
function generate_recommendations(frm) {
    const classification = frm.doc.classification_type;
    const action = frm.doc.recommended_action;
    const priority = frm.doc.action_priority || 0;
    const impact = frm.doc.expected_impact || 0;
    
    let insights = [];
    
    switch(classification) {
        case 'FAST':
            insights = [
                `This is a high-revenue, high-velocity item (${frm.doc.sales_velocity || 0} units/day)`,
                `Drives ${frm.doc.revenue_percentage || 0}% of total company revenue`,
                `Current Days of Stock: ${frm.doc.days_of_stock || 0} days`,
                `Recommendation: ${action} - Priority ${priority}/10`,
                `Expected impact: AED ${(impact || 0).toFixed(2)}`
            ];
            break;
            
        case 'SLOW':
            insights = [
                `This is a low-velocity item with consistent demand`,
                `Daily velocity: ${frm.doc.sales_velocity || 0} units/day`,
                `Demand consistency: ${frm.doc.consistency_score || 0}%`,
                `Current Days of Stock: ${frm.doc.days_of_stock || 0} days`,
                `Recommendation: ${action}`
            ];
            break;
            
        case 'DEAD_STOCK':
            insights = [
                `⚠️ WARNING: This item has not been sold for ${frm.doc.days_since_last_sale || 0} days`,
                `Stock age: ${frm.doc.stock_age_days || 0} days`,
                `Current stock value: AED ${(frm.doc.stock_value || 0).toFixed(2)}`,
                `Annual holding cost: AED ${(frm.doc.holding_cost_annually || 0).toFixed(2)}`,
                `URGENT ACTION REQUIRED: ${action}`,
                `Expected recovery value: AED ${(impact || 0).toFixed(2)}`
            ];
            break;
            
        case 'NEW_ITEM':
            insights = [
                `This is a newly launched item (${frm.doc.item_age_days || 0} days old)`,
                `Days to first sale: ${frm.doc.days_to_first_sale || 0} days`,
                `Current sales: ${frm.doc.annual_sales_qty || 0} units in launch phase`,
                `Life stage: ${frm.doc.new_item_status || 'LAUNCH'}`,
                `Recommendation: ${action} - expected ${((impact / frm.doc.annual_sales_value) * 100).toFixed(0)}% growth`
            ];
            break;
    }
    
    frm.add_custom_section('Insights', insights.map(i => `<p>${i}</p>`).join(''));
}


/**
 * Show classification badge indicator
 */
function get_indicator_color(classification) {
    const colors = {
        'FAST': 'red',
        'SLOW': 'blue',
        'MEDIUM': 'orange',
        'DEAD_STOCK': 'gray',
        'NEW_ITEM': 'green'
    };
    return colors[classification] || 'gray';
}


/**
 * Show data quality report dialog
 */
function show_data_quality_report(data) {
    let html = `
        <div style="font-family: monospace; padding: 10px;">
            <h5>Data Quality Report</h5>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f0f0f0;">
                    <th style="border: 1px solid #ddd; padding: 5px; text-align: left;">Metric</th>
                    <th style="border: 1px solid #ddd; padding: 5px; text-align: left;">Status</th>
                </tr>
    `;
    
    Object.keys(data).forEach(key => {
        const status = data[key] ? '✓' : '✗';
        const color = data[key] ? 'green' : 'red';
        html += `
            <tr>
                <td style="border: 1px solid #ddd; padding: 5px;">${key}</td>
                <td style="border: 1px solid #ddd; padding: 5px; color: ${color};"><b>${status}</b></td>
            </tr>
        `;
    });
    
    html += `</table></div>`;
    
    frappe.msgprint({
        title: __('Data Quality Report'),
        message: html
    });
}


/**
 * Show comprehensive insights dialog
 */
function show_insights_dialog(insights) {
    let html = `
        <div style="padding: 15px;">
            <h4>${insights.title}</h4>
            <p><b>Classification:</b> ${insights.classification}</p>
            <p><b>Confidence:</b> ${insights.confidence}%</p>
            <hr>
            <h5>Key Metrics:</h5>
            <ul>
    `;
    
    insights.metrics.forEach(metric => {
        html += `<li>${metric}</li>`;
    });
    
    html += `
            </ul>
            <hr>
            <h5>Recommendations:</h5>
            <ul>
    `;
    
    insights.recommendations.forEach(rec => {
        html += `<li>${rec}</li>`;
    });
    
    html += `
            </ul>
            <hr>
            <h5>Action Items:</h5>
            <ul>
    `;
    
    insights.actions.forEach(action => {
        html += `<li><b>${action.action}</b> - Priority ${action.priority}/10</li>`;
    });
    
    html += `</ul></div>`;
    
    frappe.msgprint({
        title: __('Item Classification Insights'),
        message: html,
        wide: true
    });
}
