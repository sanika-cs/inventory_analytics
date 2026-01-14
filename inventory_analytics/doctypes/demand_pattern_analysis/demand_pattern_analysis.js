/**
 * Demand Pattern Analysis - JavaScript Handler
 * Frappe DocType for demand forecasting and ROP calculations
 * 
 * For: uae.hydrotech inventory analytics
 */

frappe.ui.form.on('Demand Pattern Analysis', {
    
    /**
     * Form Load
     */
    onload: function(frm) {
        console.log('Demand Pattern Form Loaded');
        
        if (!frm.doc.analysis_date) {
            frm.set_value('analysis_date', frappe.datetime.now_datetime());
        }
        
        setup_demand_buttons(frm);
        setup_field_visibility(frm);
    },
    
    /**
     * Item Code Change
     */
    item_code: function(frm) {
        if (frm.doc.item_code) {
            load_demand_history(frm);
        }
    },
    
    /**
     * Before Save
     */
    before_save: function(frm) {
        if (!frm.doc.item_code) {
            frappe.throw(__('Please select an item'));
        }
        
        run_demand_analysis(frm);
    },
    
    /**
     * After Save
     */
    after_save: function(frm) {
        frappe.show_alert({
            message: __('Demand Pattern analysis saved successfully'),
            indicator: 'green'
        });
    }
});


/**
 * Setup buttons
 */
function setup_demand_buttons(frm) {
    frm.add_custom_button(__('Load History'), function() {
        load_demand_history(frm);
    }).addClass('btn-info');
    
    frm.add_custom_button(__('Analyze Pattern'), function() {
        run_demand_analysis(frm);
    }).addClass('btn-primary');
    
    frm.add_custom_button(__('Calculate ROP'), function() {
        calculate_rop(frm);
    }).addClass('btn-warning');
    
    frm.add_custom_button(__('Show Forecast'), function() {
        show_forecast_chart(frm);
    }).addClass('btn-success');
}


/**
 * Setup field visibility based on demand pattern
 */
function setup_field_visibility(frm) {
    frm.set_df_property('demand_pattern', 'read_only', 1);
    frm.set_df_property('adi', 'read_only', 1);
    frm.set_df_property('cv_squared', 'read_only', 1);
}


/**
 * Load 12-month demand history
 */
function load_demand_history(frm) {
    if (!frm.doc.item_code) {
        frappe.throw(__('Please select an item'));
    }
    
    frappe.call({
        method: 'inventory_analytics_app.doctypes.demand_pattern_analysis.demand_pattern_analysis.get_demand_history',
        args: {
            item_code: frm.doc.item_code
        },
        callback: function(r) {
            if (r.message) {
                const history = r.message;
                
                // Set monthly sales
                for (let i = 0; i < 12; i++) {
                    const field = `month_${i+1}_sales`;
                    if (frm.fields_dict[field]) {
                        frm.set_value(field, history[`month_${i+1}`] || 0);
                    }
                }
                
                frm.set_value('total_annual_demand', history.total_annual || 0);
                frm.set_value('avg_monthly_demand', history.avg_monthly || 0);
                
                frappe.show_alert({
                    message: __('Demand history loaded'),
                    indicator: 'blue'
                });
            }
        }
    });
}


/**
 * Run SBC demand pattern analysis
 */
function run_demand_analysis(frm) {
    frappe.call({
        method: 'inventory_analytics_app.doctypes.demand_pattern_analysis.demand_pattern_analysis.analyze_demand_pattern',
        args: {
            item_code: frm.doc.item_code,
            monthly_sales: get_monthly_sales(frm)
        },
        callback: function(r) {
            if (r.message) {
                const result = r.message;
                
                frm.set_value({
                    'demand_pattern': result.demand_pattern,
                    'adi': result.adi,
                    'cv_squared': result.cv_squared,
                    'demand_variability': result.demand_variability,
                    'classification_reason': result.reason
                });
                
                show_pattern_indicator(frm);
                
                frappe.show_alert({
                    message: __(`Pattern: <b>${result.demand_pattern}</b>`),
                    indicator: 'blue'
                });
            }
        }
    });
}


/**
 * Calculate ROP and safety stock
 */
function calculate_rop(frm) {
    frappe.call({
        method: 'inventory_analytics_app.doctypes.demand_pattern_analysis.demand_pattern_analysis.calculate_rop',
        args: {
            demand_pattern: frm.doc.demand_pattern,
            monthly_sales: get_monthly_sales(frm),
            lead_time_days: frm.doc.lead_time_days || 7
        },
        callback: function(r) {
            if (r.message) {
                const rop = r.message;
                
                frm.set_value({
                    'reorder_point': rop.rop,
                    'safety_stock': rop.safety_stock,
                    'economic_order_qty': rop.eoq,
                    'recommended_order_qty': rop.recommended_qty
                });
                
                show_rop_summary(frm);
            }
        }
    });
}


/**
 * Get monthly sales from form
 */
function get_monthly_sales(frm) {
    const sales = [];
    for (let i = 1; i <= 12; i++) {
        const field = `month_${i}_sales`;
        if (frm.fields_dict[field]) {
            sales.push(frm.doc[field] || 0);
        }
    }
    return sales;
}


/**
 * Show demand pattern indicator
 */
function show_pattern_indicator(frm) {
    const pattern = frm.doc.demand_pattern;
    
    let color = '#666';
    let description = '';
    
    if (pattern === 'SMOOTH') {
        color = '#2ecc71';
        description = 'Predictable, stable demand';
    } else if (pattern === 'ERRATIC') {
        color = '#f39c12';
        description = 'Variable demand with high volatility';
    } else if (pattern === 'INTERMITTENT') {
        color = '#3498db';
        description = 'Infrequent, sporadic demand';
    } else if (pattern === 'LUMPY') {
        color = '#e74c3c';
        description = 'Chaotic B2B demand pattern';
    }
    
    frm.set_intro(`
        <div style="background: ${color}; color: white; padding: 10px 15px; border-radius: 4px;">
            <b>Demand Pattern: ${pattern}</b><br>
            ${description}<br>
            ADI: ${(frm.doc.adi || 0).toFixed(2)} | CV²: ${(frm.doc.cv_squared || 0).toFixed(3)}
        </div>
    `);
}


/**
 * Show ROP summary
 */
function show_rop_summary(frm) {
    const summary = `
        <div style="background: #ecf0f1; padding: 15px; border-radius: 4px; margin: 10px 0;">
            <h5>Reorder Point Summary</h5>
            <table style="width: 100%;">
                <tr>
                    <td><b>Reorder Point (ROP):</b></td>
                    <td>${(frm.doc.reorder_point || 0).toFixed(0)} units</td>
                </tr>
                <tr>
                    <td><b>Safety Stock:</b></td>
                    <td>${(frm.doc.safety_stock || 0).toFixed(0)} units</td>
                </tr>
                <tr>
                    <td><b>Economic Order Qty (EOQ):</b></td>
                    <td>${(frm.doc.economic_order_qty || 0).toFixed(0)} units</td>
                </tr>
                <tr>
                    <td><b>Recommended Order Qty:</b></td>
                    <td><b>${(frm.doc.recommended_order_qty || 0).toFixed(0)} units</b></td>
                </tr>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __('ROP Calculation'),
        message: summary
    });
}


/**
 * Show forecast chart
 */
function show_forecast_chart(frm) {
    if (!frm.doc.forecast_30d) {
        frappe.throw(__('Please calculate forecast first'));
    }
    
    frappe.call({
        method: 'inventory_analytics_app.doctypes.demand_pattern_analysis.demand_pattern_analysis.get_forecast_chart',
        args: {
            item_code: frm.doc.item_code,
            demand_pattern: frm.doc.demand_pattern
        },
        callback: function(r) {
            if (r.message) {
                const chart_data = r.message;
                
                let html = `
                    <div style="width: 100%; height: 400px;" id="forecast-chart"></div>
                    <p><small>Forecast based on ${frm.doc.demand_pattern} pattern analysis</small></p>
                `;
                
                frappe.msgprint({
                    title: __('30-Day Demand Forecast'),
                    message: html,
                    wide: true,
                    on_close: function() {
                        // Render chart
                        if (window.Plotly) {
                            Plotly.newPlot('forecast-chart', chart_data.data, chart_data.layout);
                        }
                    }
                });
            }
        }
    });
}
