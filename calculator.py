from dataclasses import dataclass
from typing import Optional

@dataclass
class PaymentConfig:
    loan_amount: float
    loan_rate: float  # Annual rate as decimal (e.g. 0.05 for 5%)
    loan_term_months: int
    target_payment: float
    minimum_payment: float  # Added to track pocket money
    investment_rate: float  # Annual rate as decimal
    tax_rate: float  # Decimal (e.g. 0.25 for 25%)
    investment_type: str  # 'CD' or 'STOCK'
    monthly_savings_payment: float  # Amount to use from savings each month

@dataclass
class DerivedConfig:
    minimum_payment: float

@dataclass 
class LoanState:
    balance: float
    total_interest_paid: float
    total_principal_paid: float

@dataclass
class SavingsState:
    balance: float
    total_returns: float
    total_taxes_paid: float
    total_pocket_money: float  # Track cumulative pocket money

@dataclass
class MonthlyResult:
    new_loan_state: LoanState
    new_savings_state: SavingsState
    interest_payment: float
    principal_payment: float
    investment_returns: float
    tax_payment: float
    pocket_money: float  # Monthly pocket money
    savings_contribution: float  # Amount added to savings

def calculate_minimum_payment(amount: float, rate: float, months: int) -> float:
    """Calculate minimum monthly payment for a loan using standard amortization formula.
    
    Args:
        amount: Principal amount of the loan
        rate: Annual interest rate as decimal (e.g., 0.05 for 5%)
        months: Term of loan in months
        
    Returns:
        Monthly payment amount
        
    Raises:
        ValueError: If any input is invalid (negative or zero months)
    """
    if amount <= 0:
        raise ValueError("Loan amount must be positive")
    if rate < 0:
        raise ValueError("Interest rate cannot be negative")
    if months <= 0:
        raise ValueError("Loan term must be positive")
    
    if rate == 0:
        return amount / months
    
    monthly_rate = rate / 12
    numerator = amount * monthly_rate * (1 + monthly_rate)**months
    denominator = (1 + monthly_rate)**months - 1
    
    # Handle potential floating point precision issues
    if abs(denominator) < 1e-10:
        return amount * (1 + monthly_rate)
        
    return numerator / denominator

def process_month(
    config: PaymentConfig,
    derived: DerivedConfig,
    loan_state: LoanState,
    savings_state: SavingsState,
) -> MonthlyResult:
    """Process a single month of loan payments and savings.
    
    The function follows these steps:
    1. Calculate this month's interest
    2. Determine payment from regular income (up to target payment)
    3. Calculate investment returns and taxes (for CDs)
    4. If needed and available, use savings to pay more
    5. Calculate investment returns (for stocks)
    6. If loan is paid off, invest remaining target payment
    """
    # Monthly rates
    monthly_loan_rate = config.loan_rate / 12
    monthly_investment_rate = config.investment_rate / 12
    
    # Start with current state
    new_loan = LoanState(
        balance=loan_state.balance,
        total_interest_paid=loan_state.total_interest_paid,
        total_principal_paid=loan_state.total_principal_paid
    )
    new_savings = SavingsState(
        balance=savings_state.balance,
        total_returns=savings_state.total_returns,
        total_taxes_paid=savings_state.total_taxes_paid,
        total_pocket_money=savings_state.total_pocket_money
    )
    
    # Calculate this month's loan interest
    interest_this_month = new_loan.balance * monthly_loan_rate
    
    # First, allocate target payment to interest and principal
    total_needed = new_loan.balance + interest_this_month
    target_to_loan = min(config.target_payment, total_needed)
    target_interest = min(interest_this_month, target_to_loan)
    target_principal = target_to_loan - target_interest
    target_to_savings = config.target_payment - target_to_loan
    
    # Calculate investment returns for CDs (on initial balance)
    investment_returns = 0.0
    investment_tax = 0.0
    if new_savings.balance > 0 and config.investment_type == 'CD':
        # Calculate returns on initial balance
        investment_returns = new_savings.balance * monthly_investment_rate
        new_savings.total_returns += investment_returns
        # For CDs, tax is applied to returns immediately
        investment_tax = investment_returns * config.tax_rate
        new_savings.total_taxes_paid += investment_tax
    
    # Then, try to use additional payment from savings if available
    from_savings = 0.0
    savings_tax = 0.0
    if (new_loan.balance > 0 and 
        config.monthly_savings_payment > 0 and 
        new_savings.balance > 0):
        
        available_savings = new_savings.balance
        if config.investment_type == 'STOCK':
            # Only stocks are taxed on withdrawal
            available_savings = available_savings / (1 + config.tax_rate)
            
        # Use savings up to the monthly savings payment amount or what's needed
        remaining_needed = total_needed - target_to_loan
        from_savings = min(
            config.monthly_savings_payment,
            available_savings,
            remaining_needed if remaining_needed > 0 else 0.0
        )
        
        if from_savings > 0:
            if config.investment_type == 'STOCK':
                # Only stocks are taxed on withdrawal
                savings_tax = from_savings * config.tax_rate
                new_savings.total_taxes_paid += savings_tax
                new_savings.balance -= (from_savings + savings_tax)
            else:
                # CDs are not taxed on withdrawal
                new_savings.balance -= from_savings
    
    # Apply extra payment to loan
    if from_savings > 0:
        extra_interest = min(
            interest_this_month - target_interest,
            from_savings
        )
        extra_principal = from_savings - extra_interest
        
        target_interest += extra_interest
        target_principal += extra_principal
    
    # Calculate pocket money (difference between minimum and actual payments)
    actual_payment = target_interest + target_principal
    pocket_money = max(0, config.minimum_payment - actual_payment)
    new_savings.total_pocket_money += pocket_money
    
    # Update loan state
    new_loan.total_interest_paid += target_interest
    new_loan.total_principal_paid += target_principal
    new_loan.balance = max(0, new_loan.balance - target_principal)
    
    # Calculate investment returns for stocks (on remaining balance)
    if new_savings.balance > 0 and config.investment_type == 'STOCK':
        investment_returns = new_savings.balance * monthly_investment_rate
        new_savings.total_returns += investment_returns
    
    # If loan is paid off, invest the remaining target payment
    if new_loan.balance == 0:
        target_to_savings = config.target_payment - actual_payment
    
    # Add investment returns and savings contribution last
    new_savings.balance += investment_returns - investment_tax + target_to_savings
    
    return MonthlyResult(
        new_loan_state=new_loan,
        new_savings_state=new_savings,
        interest_payment=target_interest,
        principal_payment=target_principal,
        investment_returns=investment_returns,
        tax_payment=investment_tax + savings_tax,
        pocket_money=pocket_money,
        savings_contribution=target_to_savings
    ) 