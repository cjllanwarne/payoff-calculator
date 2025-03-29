import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List
import json
import os
from datetime import datetime
from simulation import run_simulation
from calculator import calculate_minimum_payment, PaymentConfig

st.set_page_config(
    page_title="Debt Payoff vs Investment Calculator",
    layout="wide"
)

# Initialize session state for all inputs if they don't exist
DEFAULTS = {
    'debt_amount': 100000.0,
    'debt_interest': 5.0,
    'loan_term_years': 30,
    'target_payment': 0.0,  # Will be set to min_monthly_payment
    'initial_savings': 0.0,  # Add initial savings default
    'lump_sum': 0.0,
    'lump_sum_month': 0,
    'monthly_savings_payment': 0.0,  # New default for monthly payment from savings
    'investment_rate': 7.0,
    'investment_type': "CD",
    'tax_rate': 25.0,
    'config_name': 'default',  # Add default configuration name
    'excess_to_savings': True  # Add default for excess_to_savings
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

def save_config():
    """Save current configuration to JSON file"""
    config = {
        'debt_amount': st.session_state.debt_amount,
        'debt_interest': st.session_state.debt_interest,
        'loan_term_years': st.session_state.loan_term_years,
        'target_payment': st.session_state.target_payment,
        'initial_savings': st.session_state.initial_savings,
        'lump_sum': st.session_state.lump_sum,
        'lump_sum_month': st.session_state.lump_sum_month,
        'monthly_savings_payment': st.session_state.monthly_savings_payment,
        'investment_rate': st.session_state.investment_rate,
        'investment_type': st.session_state.investment_type,
        'tax_rate': st.session_state.tax_rate,
        'config_name': st.session_state.config_name,
        'excess_to_savings': st.session_state.excess_to_savings
    }
    
    # Create configs directory if it doesn't exist
    os.makedirs('configs', exist_ok=True)
    
    # Use the config name in the filename
    safe_name = "".join(c for c in st.session_state.config_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_name:
        safe_name = 'default'
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'configs/{safe_name}_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(config, f, indent=4)
    
    return filename

def load_config(filename):
    """Load configuration from JSON file"""
    with open(filename, 'r') as f:
        config = json.load(f)
    
    # Extract config name from filename if not in config
    if 'config_name' not in config:
        base_name = os.path.basename(filename)
        name_parts = base_name.split('_')[:-2]  # Remove timestamp and .json
        config['config_name'] = '_'.join(name_parts) if name_parts else 'default'
    
    # Store the config in a temporary session state variable
    st.session_state.temp_config = config
    # Force a rerun to apply the new config
    st.rerun()

# Page title
st.title("Debt Payoff vs Investment Calculator")

# Add configuration management at the top
st.sidebar.subheader("Configuration Management")

# If we have a temp config, apply it before creating widgets
if 'temp_config' in st.session_state:
    config = st.session_state.temp_config
    # Remove temp config to prevent infinite rerun
    del st.session_state.temp_config
    # Update all other session state values
    for key, value in config.items():
        if key != 'config_name':  # Skip config_name as it will be handled by the widget
            setattr(st.session_state, key, value)
    # Pre-set the config_name for the text input
    st.session_state['config_name'] = config['config_name']

# Configuration name input
st.sidebar.text_input(
    "Configuration Name",
    key='config_name',
    help="Enter a name for your configuration"
)

# Save current configuration
if st.sidebar.button("Save Current Configuration"):
    saved_file = save_config()
    st.sidebar.success(f"Configuration saved as {st.session_state.config_name}")

# Reset to defaults button
if st.sidebar.button("Reset to Defaults"):
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.rerun()

# Load configuration
config_files = []
if os.path.exists('configs'):
    config_files = [f for f in os.listdir('configs') if f.endswith('.json')]

if config_files:
    # Format the config files to show the name and timestamp
    def format_config_name(filename):
        parts = filename.replace('.json', '').split('_')
        timestamp = '_'.join(parts[-2:])
        name = '_'.join(parts[:-2]) if len(parts) > 2 else 'default'
        return f"{name} ({timestamp})"
    
    selected_config = st.sidebar.selectbox(
        "Select configuration to load",
        config_files,
        format_func=format_config_name
    )
    
    if st.sidebar.button("Load Selected Configuration"):
        load_config(os.path.join('configs', selected_config))

# Create two columns for inputs
col1, col2 = st.columns(2)

with col1:
    st.subheader("Loan Details")
    st.number_input(
        "Remaining Debt Amount ($)",
        min_value=0.0,
        step=1000.0,
        key='debt_amount'
    )
    st.number_input(
        "Debt Interest Rate (%)",
        min_value=0.0,
        max_value=30.0,
        step=0.1,
        key='debt_interest'
    )
    st.number_input(
        "Loan Term (Years)",
        min_value=1,
        max_value=30,
        step=1,
        key='loan_term_years'
    )
    
    # Calculate minimum monthly payment
    months = st.session_state.loan_term_years * 12
    min_monthly_payment = calculate_minimum_payment(
        st.session_state.debt_amount,
        st.session_state.debt_interest / 100,  # Convert from percentage to decimal
        months
    )
    
    st.write(f"Minimum Monthly Payment: ${min_monthly_payment:.2f}")
    
    # Initialize target_payment if it's the default value
    if st.session_state.target_payment == 0.0:
        st.session_state.target_payment = min_monthly_payment
    
    st.number_input(
        "Total Payment Target per Month ($)",
        min_value=0.0,
        step=100.0,
        key='target_payment'
    )
    
    # Add excess to savings checkbox in loan details section
    st.checkbox(
        "Route Excess to Savings",
        key='excess_to_savings',
        help="If checked, any payment above minimum goes to savings. If unchecked, it goes to loan principal."
    )

with col2:
    st.subheader("Investment Details")
    st.number_input(
        "Initial Savings ($)",
        min_value=0.0,
        step=1000.0,
        key='initial_savings'
    )
    st.number_input(
        "Initial Lump Sum Payoff ($)",  # Initial lump sum payment
        min_value=0.0,
        step=1000.0,
        key='lump_sum'
    )
    st.number_input(
        "Additional Monthly Payment from Savings ($)",  # Ongoing monthly payment
        min_value=0.0,
        step=100.0,
        key='monthly_savings_payment'  # New session state key
    )
    
    st.number_input(
        "Anticipated Investment Return Rate (% Annual)",
        min_value=0.0,
        max_value=25.0,
        step=0.1,
        key='investment_rate'
    )
    
    # Map display values to storage values
    investment_type_map = {
        "CD (taxed annually)": "CD",
        "Stocks (taxed at withdrawal)": "STOCK"
    }
    
    # Display radio with descriptions but store simple values
    selected_display = st.radio(
        "Investment Type",
        list(investment_type_map.keys()),
        index=0 if st.session_state.investment_type == "CD" else 1
    )
    # Update session state with the mapped value
    st.session_state.investment_type = investment_type_map[selected_display]
    
    is_cd = st.session_state.investment_type == "CD"
    
    tax_label = "Annual Investment Tax Rate (%)" if is_cd else "Capital Gains Tax Rate (%)"
    st.number_input(
        tax_label,
        min_value=0.0,
        max_value=50.0,
        step=0.1,
        key='tax_rate'
    )

# Run analysis
config = PaymentConfig(
    loan_amount=st.session_state.debt_amount,
    loan_rate=st.session_state.debt_interest,
    loan_term_months=months,
    target_payment=st.session_state.target_payment,
    initial_savings=st.session_state.initial_savings,
    monthly_savings_payment=st.session_state.monthly_savings_payment,
    investment_rate=st.session_state.investment_rate,
    tax_rate=st.session_state.tax_rate,
    investment_type=st.session_state.investment_type,
    excess_to_savings=st.session_state.excess_to_savings
)

result = run_simulation(
    config=config,
    lump_sum=st.session_state.lump_sum
)

# Create plots
st.subheader("Balance Over Time")
fig1, ax1 = plt.subplots(figsize=(10, 6))
# Adjust months_range to match the length of result arrays
months_range = range(len(result.loan_balance))
years_range = [m/12 for m in months_range]  # Convert months to years
ax1.plot(years_range, result.loan_balance, label='Loan Balance', color='red')
ax1.plot(years_range, result.savings_balance, label='Savings Balance', color='green')
ax1.plot(years_range, result.pocket_money_balance, label='Pocket Money', color='purple')
ax1.set_xlabel('Years')
ax1.set_ylabel('Balance ($)')
ax1.legend()
ax1.grid(True)
# Format x-axis to show whole years
ax1.xaxis.set_major_locator(plt.MultipleLocator(5))  # Show tick every 5 years
ax1.xaxis.set_minor_locator(plt.MultipleLocator(1))  # Minor tick every year
st.pyplot(fig1)

st.subheader("Monthly Payments Breakdown")
fig2, ax2 = plt.subplots(figsize=(10, 6))

# Convert to numpy arrays for easier manipulation
principal_array = np.array(result.principal_payments)
interest_array = np.array(result.interest_payments)
savings_array = np.array(result.savings_contributions)
pocket_money_array = np.array(result.pocket_money)

# Create the stacked plot with arrays in the correct order
ax2.stackplot(years_range,
             [pocket_money_array, savings_array, interest_array, principal_array],
             labels=['Pocket Money', 'Savings Contribution', 'Interest', 'Principal'],
             colors=['purple', 'green', 'orange', 'blue'])
ax2.set_xlabel('Years')
ax2.set_ylabel('Amount ($)')
# Set y-axis limit to slightly above the higher of minimum payment or target payment
y_max = max(min_monthly_payment, st.session_state.target_payment) * 1.1  # 10% margin
ax2.set_ylim(0, y_max)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
ax2.legend(loc='upper right')
ax2.grid(True)
# Format x-axis to show whole years
ax2.xaxis.set_major_locator(plt.MultipleLocator(5))
ax2.xaxis.set_minor_locator(plt.MultipleLocator(1))
st.pyplot(fig2)

# Summary statistics
st.subheader("Summary")
total_interest = sum(result.interest_payments)
total_principal = sum(result.principal_payments)
total_savings_contribution = sum(result.savings_contributions)
final_savings = result.savings_balance[-1]

col3, col4, col5, col6, col7 = st.columns(5)
with col3:
    st.metric("Total Interest Paid", f"${total_interest:,.2f}")
with col4:
    st.metric("Total Principal Paid", f"${total_principal:,.2f}")
with col5:
    st.metric("Total Savings Contribution", f"${total_savings_contribution:,.2f}")
with col6:
    st.metric("Final Savings Balance", f"${final_savings:,.2f}")
with col7:
    st.metric("Total Pocket Money", f"${result.total_pocket_money:,.2f}") 