import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List
import json
import os
from datetime import datetime

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
    'investment_type': "CD (taxed annually)",
    'tax_rate': 25.0,
    'config_name': 'default'  # Add default configuration name
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
        'config_name': st.session_state.config_name  # Save the configuration name
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

def calculate_monthly_payment(principal: float, annual_rate: float, months: int) -> float:
    """Calculate the minimum monthly payment for a loan."""
    if annual_rate == 0:
        return principal / months
    
    monthly_rate = annual_rate / 12 / 100
    return principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)

def calculate_monthly_investment_return(principal: float, annual_rate: float) -> float:
    """Calculate monthly investment return based on annual rate."""
    monthly_rate = annual_rate / 12 / 100
    return principal * monthly_rate

def run_analysis(
    debt_amount: float,
    debt_interest: float,
    months: int,
    monthly_payment: float,  # This is the minimum required payment
    target_payment: float,   # This is what the user wants to pay out of pocket
    initial_savings: float,
    lump_sum: float,  # Initial lump sum payoff
    monthly_savings_payment: float,  # Additional monthly payment from savings
    investment_rate: float,
    tax_rate: float,
    is_cd: bool
) -> Tuple[List[float], List[float], List[float], List[float], List[float], List[float], List[float], List[float], float]:
    """Run the debt vs investment analysis."""
    
    # Initialize arrays to store monthly values
    loan_balance = []
    savings_balance = []
    pocket_money_balance = []  # New array to track cumulative pocket money
    loan_payments = []
    principal_payments = []
    interest_payments = []
    savings_contributions = []
    pocket_money = []  # New array to track monthly pocket money
    
    # Apply initial lump sum payment from savings
    current_debt = debt_amount
    current_savings = initial_savings
    current_pocket_money = 0  # Track cumulative pocket money
    
    if lump_sum > 0:
        actual_lump_sum = min(lump_sum, current_savings)
        actual_lump_sum = min(actual_lump_sum, current_debt)  # Don't pay more than debt
        current_debt -= actual_lump_sum
        current_savings -= actual_lump_sum
        
        # Record initial lump sum payment
        loan_payments.append(actual_lump_sum)
        principal_payments.append(actual_lump_sum)
        interest_payments.append(0)
        savings_contributions.append(0)
        pocket_money.append(0)  # No pocket money from lump sum
        loan_balance.append(current_debt)
        savings_balance.append(current_savings)
        pocket_money_balance.append(current_pocket_money)
    
    monthly_debt_rate = debt_interest / 12 / 100
    monthly_investment_rate = investment_rate / 12 / 100
    
    # If loan is already paid off by lump sum, just accumulate savings
    if current_debt <= 0:
        for month in range(1 if lump_sum > 0 else 0, months):
            # Calculate pocket money (difference between minimum payment and target payment)
            month_pocket_money = max(0, monthly_payment - target_payment)
            current_pocket_money += month_pocket_money
            
            # Calculate investment returns and taxes
            if current_savings > 0:
                investment_return = current_savings * monthly_investment_rate
                if is_cd:
                    tax = investment_return * tax_rate / 100
                    investment_return -= tax
                current_savings += investment_return
            
            # Add target payment to savings since loan is paid off
            current_savings += target_payment
            
            # Record monthly values
            loan_balance.append(0)
            savings_balance.append(current_savings)
            pocket_money_balance.append(current_pocket_money)
            loan_payments.append(0)
            principal_payments.append(0)
            interest_payments.append(0)
            savings_contributions.append(target_payment)
            pocket_money.append(month_pocket_money)
            
        return (loan_balance, savings_balance, pocket_money_balance, loan_payments, principal_payments, 
                interest_payments, savings_contributions, pocket_money, current_pocket_money)
    
    # Continue with regular monthly payments if loan is not paid off
    for month in range(1 if lump_sum > 0 else 0, months):
        # Calculate interest on debt
        interest_charge = current_debt * monthly_debt_rate
        
        # Calculate investment returns and taxes
        if current_savings > 0:
            investment_return = current_savings * monthly_investment_rate
            if is_cd:
                tax = investment_return * tax_rate / 100
                investment_return -= tax
            current_savings += investment_return
        
        # Calculate total required payment for this month
        required_payment = min(monthly_payment, current_debt + interest_charge)
        
        # If loan will be paid off this month, adjust required payment
        if required_payment >= current_debt + interest_charge:
            required_payment = current_debt + interest_charge
            
        # First, allocate target payment to required loan payment
        target_to_loan = min(target_payment, required_payment)
        target_interest = min(interest_charge, target_to_loan)
        target_principal = target_to_loan - target_interest
        target_to_savings = target_payment - target_to_loan
        
        # Then, try to use additional payment from savings if there's any loan left
        from_savings = 0
        if current_debt > 0 and monthly_savings_payment > 0 and current_savings > 0:
            from_savings = min(
                monthly_savings_payment,
                current_savings,
                current_debt + interest_charge - target_to_loan
            )
            current_savings -= from_savings
        
        # Any remaining required payment must come out of pocket
        remaining_required = required_payment - target_to_loan
        additional_out_of_pocket = max(0, remaining_required - from_savings)
        
        # Calculate total out-of-pocket payment for this month
        total_out_of_pocket = target_to_loan + additional_out_of_pocket
        
        # Calculate pocket money (difference between minimum payment and total out-of-pocket)
        month_pocket_money = max(0, monthly_payment - total_out_of_pocket)
        current_pocket_money += month_pocket_money
        
        # Total payment breakdown for stacked chart (only showing out-of-pocket amounts)
        interest_portion = target_interest + (additional_out_of_pocket * interest_charge / required_payment if required_payment > 0 else 0)
        principal_portion = target_principal + (additional_out_of_pocket * (1 - interest_charge / required_payment) if required_payment > 0 else 0)
        savings_portion = target_to_savings
        
        # Record payments
        interest_payments.append(interest_portion)
        principal_payments.append(principal_portion)
        loan_payments.append(target_to_loan + from_savings + additional_out_of_pocket)
        savings_contributions.append(savings_portion)
        pocket_money.append(month_pocket_money)
        
        # Update balances
        current_debt = current_debt + interest_charge - (target_to_loan + from_savings + additional_out_of_pocket)
        current_savings += target_to_savings
        
        # Store balances
        loan_balance.append(max(0, current_debt))
        savings_balance.append(current_savings)
        pocket_money_balance.append(current_pocket_money)
        
        # If loan is fully paid, switch to savings mode for remaining months
        if current_debt <= 0:
            remaining_months = months - len(loan_balance)
            for _ in range(remaining_months):
                # Calculate pocket money (difference between minimum payment and target payment)
                month_pocket_money = max(0, monthly_payment - target_payment)
                current_pocket_money += month_pocket_money
                
                if current_savings > 0:
                    investment_return = current_savings * monthly_investment_rate
                    if is_cd:
                        tax = investment_return * tax_rate / 100
                        investment_return -= tax
                    current_savings += investment_return
                
                current_savings += target_payment
                
                loan_balance.append(0)
                savings_balance.append(current_savings)
                pocket_money_balance.append(current_pocket_money)
                loan_payments.append(0)
                principal_payments.append(0)
                interest_payments.append(0)
                savings_contributions.append(target_payment)
                pocket_money.append(month_pocket_money)
            break
            
    return (loan_balance, savings_balance, pocket_money_balance, loan_payments, principal_payments, 
            interest_payments, savings_contributions, pocket_money, current_pocket_money)

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
    min_monthly_payment = calculate_monthly_payment(
        st.session_state.debt_amount,
        st.session_state.debt_interest,
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
    
    st.radio(
        "Investment Type",
        ["CD (taxed annually)", "Stocks (taxed at withdrawal)"],
        key='investment_type'
    )
    is_cd = st.session_state.investment_type == "CD (taxed annually)"
    
    tax_label = "Annual Investment Tax Rate (%)" if is_cd else "Capital Gains Tax Rate (%)"
    st.number_input(
        tax_label,
        min_value=0.0,
        max_value=50.0,
        step=0.1,
        key='tax_rate'
    )

# Run analysis
(loan_balance, savings_balance, pocket_money_balance, loan_payments, principal_payments, 
 interest_payments, savings_contributions, pocket_money, total_pocket_money) = run_analysis(
    debt_amount=st.session_state.debt_amount,
    debt_interest=st.session_state.debt_interest,
    months=months,
    monthly_payment=min_monthly_payment,
    target_payment=st.session_state.target_payment,
    initial_savings=st.session_state.initial_savings,
    lump_sum=st.session_state.lump_sum,
    monthly_savings_payment=st.session_state.monthly_savings_payment,
    investment_rate=st.session_state.investment_rate,
    tax_rate=st.session_state.tax_rate,
    is_cd=is_cd
)

# Create plots
st.subheader("Balance Over Time")
fig1, ax1 = plt.subplots(figsize=(10, 6))
months_range = range(1, months + 1)
years_range = [m/12 for m in months_range]  # Convert months to years
ax1.plot(years_range, loan_balance, label='Loan Balance', color='red')
ax1.plot(years_range, savings_balance, label='Savings Balance', color='green')
ax1.plot(years_range, pocket_money_balance, label='Pocket Money', color='purple')  # Add pocket money line
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
principal_array = np.array(principal_payments)
interest_array = np.array(interest_payments)
savings_array = np.array(savings_contributions)
pocket_money_array = np.array(pocket_money)  # Add pocket money array

# Create the stacked plot with arrays in the correct order
ax2.stackplot(years_range,
             [pocket_money_array, savings_array, interest_array, principal_array],  # Add pocket money to stack
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
total_interest = sum(interest_payments)
total_principal = sum(principal_payments)
total_savings_contribution = sum(savings_contributions)
final_savings = savings_balance[-1]

col3, col4, col5, col6, col7 = st.columns(5)  # Added a column for pocket money
with col3:
    st.metric("Total Interest Paid", f"${total_interest:,.2f}")
with col4:
    st.metric("Total Principal Paid", f"${total_principal:,.2f}")
with col5:
    st.metric("Total Savings Contribution", f"${total_savings_contribution:,.2f}")
with col6:
    st.metric("Final Savings Balance", f"${final_savings:,.2f}")
with col7:
    st.metric("Total Pocket Money", f"${total_pocket_money:,.2f}")  # Add pocket money metric 