from dataclasses import dataclass
from typing import List, Tuple
from calculator import (
    PaymentConfig, DerivedConfig, LoanState, SavingsState, MonthlyResult,
    calculate_minimum_payment, process_month
)

@dataclass
class SimulationResult:
    loan_balance: List[float]
    savings_balance: List[float]
    pocket_money_balance: List[float]
    loan_payments: List[float]
    principal_payments: List[float]
    interest_payments: List[float]
    savings_contributions: List[float]
    pocket_money: List[float]
    total_pocket_money: float

def run_simulation(
    debt_amount: float,
    debt_interest: float,  # as percentage
    loan_term_months: int,
    target_payment: float,
    initial_savings: float,
    lump_sum: float,
    monthly_savings_payment: float,
    investment_rate: float,  # as percentage
    tax_rate: float,  # as percentage
    is_cd: bool,
) -> SimulationResult:
    """Run the full debt vs investment simulation."""
    
    # Convert percentage rates to decimals
    debt_rate = debt_interest / 100
    inv_rate = investment_rate / 100
    tax_rate_decimal = tax_rate / 100
    
    # Calculate minimum payment
    min_payment = calculate_minimum_payment(debt_amount, debt_rate, loan_term_months)
    
    # Initialize configuration
    config = PaymentConfig(
        loan_amount=debt_amount,
        loan_rate=debt_rate,
        loan_term_months=loan_term_months,
        target_payment=target_payment,
        minimum_payment=min_payment,
        investment_rate=inv_rate,
        tax_rate=tax_rate_decimal,
        investment_type='CD' if is_cd else 'STOCK',
        monthly_savings_payment=monthly_savings_payment
    )
    
    derived = DerivedConfig(minimum_payment=min_payment)
    
    # Initialize state
    loan_state = LoanState(
        balance=debt_amount,
        total_interest_paid=0.0,
        total_principal_paid=0.0
    )
    
    savings_state = SavingsState(
        balance=initial_savings,
        total_returns=0.0,
        total_taxes_paid=0.0,
        total_pocket_money=0.0
    )
    
    # Apply initial lump sum if available
    if lump_sum > 0 and initial_savings > 0:
        actual_lump_sum = min(lump_sum, initial_savings, debt_amount)
        loan_state.balance -= actual_lump_sum
        loan_state.total_principal_paid += actual_lump_sum
        savings_state.balance -= actual_lump_sum
    
    # Initialize result arrays
    result = SimulationResult(
        loan_balance=[loan_state.balance],
        savings_balance=[savings_state.balance],
        pocket_money_balance=[savings_state.total_pocket_money],
        loan_payments=[actual_lump_sum if lump_sum > 0 else 0.0],
        principal_payments=[actual_lump_sum if lump_sum > 0 else 0.0],
        interest_payments=[0.0],
        savings_contributions=[0.0],
        pocket_money=[0.0],
        total_pocket_money=0.0
    )
    
    # Run month-by-month simulation
    for _ in range(1 if lump_sum > 0 else 0, loan_term_months):
        monthly_result = process_month(config, derived, loan_state, savings_state)
        
        # Update state
        loan_state = monthly_result.new_loan_state
        savings_state = monthly_result.new_savings_state
        
        # Record results
        result.loan_balance.append(loan_state.balance)
        result.savings_balance.append(savings_state.balance)
        result.pocket_money_balance.append(savings_state.total_pocket_money)
        result.loan_payments.append(monthly_result.interest_payment + monthly_result.principal_payment)
        result.principal_payments.append(monthly_result.principal_payment)
        result.interest_payments.append(monthly_result.interest_payment)
        result.savings_contributions.append(monthly_result.savings_contribution)
        result.pocket_money.append(monthly_result.pocket_money)
    
    result.total_pocket_money = savings_state.total_pocket_money
    return result 