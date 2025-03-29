from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentConfig:
    loan_amount: float
    loan_rate: float  # Annual rate as decimal (e.g. 0.05 for 5%)
    loan_term_months: int
    target_payment: float
    initial_savings: float
    minimum_payment: float  # Added to track pocket money
    investment_rate: float  # Annual rate as decimal
    tax_rate: float  # Decimal (e.g. 0.25 for 25%)
    investment_type: str  # 'CD' or 'STOCK'
    monthly_savings_payment: float  # Amount to use from savings each month
    excess_to_savings: bool = False  # If True, excess goes to savings. If False, to principal.

    def __init__(
        self,
        loan_amount: float,
        loan_rate: float,  # as decimal
        loan_term_months: int,
        target_payment: float,
        initial_savings: float,
        monthly_savings_payment: float,
        investment_rate: float,  # as decimal
        tax_rate: float,  # as decimal
        investment_type: str,
        excess_to_savings: bool
    ):
        """Create a PaymentConfig instance from simulation parameters."""
        
        # Calculate minimum payment
        min_payment = calculate_minimum_payment(loan_amount, loan_rate, loan_term_months)
        
        self.loan_amount = loan_amount
        self.loan_rate = loan_rate
        self.loan_term_months = loan_term_months
        self.target_payment = target_payment
        self.initial_savings = initial_savings
        self.minimum_payment = min_payment
        self.investment_rate = investment_rate
        self.tax_rate = tax_rate
        self.investment_type = investment_type
        self.monthly_savings_payment = monthly_savings_payment
        self.excess_to_savings = excess_to_savings


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
    loan_state: LoanState,
    savings_state: SavingsState
) -> MonthlyResult:
    """Process one month of payments and calculate new state."""
    # Calculate monthly rates using compound interest formula
    monthly_loan_rate = (1 + config.loan_rate)**(1/12) - 1
    monthly_investment_rate = (1 + config.investment_rate)**(1/12) - 1
    
    # Calculate this month's interest using the correct monthly rate
    monthly_interest = loan_state.balance * monthly_loan_rate
    
    # Calculate payment amounts
    total_needed = loan_state.balance + monthly_interest
    payment_from_income = min(config.target_payment, total_needed)
    
    # Handle excess payment based on configuration
    excess_payment = max(0, config.target_payment - config.minimum_payment)
    savings_contribution = 0.0
    
    if config.excess_to_savings and excess_payment > 0 and loan_state.balance > 0:
        # Route excess to savings instead of principal
        payment_from_income = min(config.minimum_payment, payment_from_income)
        savings_contribution = excess_payment
    
    # Calculate principal and interest portions
    interest_payment = min(monthly_interest, payment_from_income)
    principal_payment = payment_from_income - interest_payment
    
    # Handle investment returns and taxes
    monthly_return = 0.0
    tax_payment = 0.0
    savings_payment = 0.0
    
    if savings_state.balance > 0:
        if config.investment_type == 'CD':
            # For CDs:
            # 1. Calculate return on initial balance using correct monthly rate
            monthly_return = savings_state.balance * monthly_investment_rate
            # 2. Calculate tax on returns
            tax_payment = monthly_return * config.tax_rate
            # 3. Calculate savings payment (no tax on withdrawal)
            if loan_state.balance > 0 and not config.excess_to_savings:
                savings_payment = min(
                    config.monthly_savings_payment,
                    savings_state.balance,
                    loan_state.balance - principal_payment
                )
                if savings_payment > 0:
                    principal_payment += savings_payment
        else:  # STOCK
            # For stocks:
            # 1. Calculate withdrawal and tax
            if loan_state.balance > 0 and not config.excess_to_savings:
                savings_payment = min(
                    config.monthly_savings_payment,
                    savings_state.balance,
                    loan_state.balance - principal_payment
                )
                if savings_payment > 0:
                    tax_payment = savings_payment * config.tax_rate
                    principal_payment += savings_payment
            
            # 2. Calculate return on remaining balance using correct monthly rate
            remaining_balance = savings_state.balance - savings_payment - tax_payment
            monthly_return = remaining_balance * monthly_investment_rate
    
    # Update loan state
    new_loan_balance = loan_state.balance - principal_payment
    new_loan_state = LoanState(
        balance=new_loan_balance,
        total_interest_paid=loan_state.total_interest_paid + interest_payment,
        total_principal_paid=loan_state.total_principal_paid + principal_payment
    )
    
    # Calculate pocket money (if paying less than minimum)
    pocket_money = max(0, config.minimum_payment - config.target_payment)
    
    # If loan is paid off, contribute remaining target payment to savings
    if new_loan_balance == 0 and payment_from_income < config.target_payment:
        savings_contribution = config.target_payment - payment_from_income
    
    # Update savings state
    new_savings_balance = (
        savings_state.balance +
        monthly_return -
        tax_payment -
        savings_payment +
        savings_contribution
    )
    
    new_savings_state = SavingsState(
        balance=new_savings_balance,
        total_returns=savings_state.total_returns + monthly_return,
        total_taxes_paid=savings_state.total_taxes_paid + tax_payment,
        total_pocket_money=savings_state.total_pocket_money + pocket_money
    )
    
    return MonthlyResult(
        new_loan_state=new_loan_state,
        new_savings_state=new_savings_state,
        interest_payment=interest_payment,
        principal_payment=principal_payment,
        investment_returns=monthly_return,
        tax_payment=tax_payment,
        pocket_money=pocket_money,
        savings_contribution=savings_contribution
    ) 