import unittest
from calculator import (
    calculate_minimum_payment, process_month,
    PaymentConfig, DerivedConfig, LoanState, SavingsState
)
import math

class TestCalculator(unittest.TestCase):
    def assertPaymentIsCorrect(self, amount: float, rate: float, months: int):
        """Helper to verify the payment fully amortizes the loan."""
        payment = calculate_minimum_payment(amount, rate, months)
        
        # Simulate the loan with the calculated payment
        balance = amount
        monthly_rate = rate / 12
        
        for _ in range(months):
            interest = balance * monthly_rate
            principal = payment - interest
            balance -= principal
        
        self.assertAlmostEqual(balance, 0, places=2, 
            msg=f"Payment {payment:.2f} does not fully amortize loan: {amount:.2f} @ {rate*100}% over {months} months")
        
        return payment

    def test_zero_interest(self):
        """Test loan with 0% interest."""
        amount = 12000
        months = 12
        payment = calculate_minimum_payment(amount, 0.0, months)
        self.assertEqual(payment, 1000.0)  # Should simply divide amount by months

    def test_standard_loan(self):
        """Test a typical mortgage-like loan."""
        amount = 100000
        rate = 0.05  # 5%
        months = 360  # 30 years
        
        payment = self.assertPaymentIsCorrect(amount, rate, months)
        
        # Known correct payment for these terms (verified with external calculator)
        expected = 536.82
        self.assertAlmostEqual(payment, expected, places=2)

    def test_short_term_loan(self):
        """Test a short-term loan with high interest."""
        amount = 10000
        rate = 0.12  # 12%
        months = 12
        
        payment = self.assertPaymentIsCorrect(amount, rate, months)
        
        # The exact payment that fully amortizes this loan is 888.49
        # (verified with multiple financial calculators)
        expected = 888.49
        self.assertAlmostEqual(payment, expected, places=2)

    def test_very_small_loan(self):
        """Test with very small numbers to check for floating point issues."""
        amount = 100
        rate = 0.01  # 1%
        months = 12
        
        payment = self.assertPaymentIsCorrect(amount, rate, months)
        self.assertTrue(payment > 0)

    def test_very_large_loan(self):
        """Test with very large numbers to check for overflow issues."""
        amount = 1000000000  # 1 billion
        rate = 0.03  # 3%
        months = 360
        
        payment = self.assertPaymentIsCorrect(amount, rate, months)
        self.assertTrue(payment > 0)

    def test_high_interest(self):
        """Test with very high interest rate."""
        amount = 10000
        rate = 0.30  # 30%
        months = 12
        
        payment = self.assertPaymentIsCorrect(amount, rate, months)
        self.assertTrue(payment > 0)

    def test_one_month_loan(self):
        """Test edge case of one-month loan."""
        amount = 1000
        rate = 0.12  # 12%
        months = 1
        
        payment = calculate_minimum_payment(amount, rate, months)
        expected = amount * (1 + rate/12)
        self.assertAlmostEqual(payment, expected, places=2)

    def test_input_validation(self):
        """Test invalid inputs."""
        with self.assertRaises(ValueError):
            calculate_minimum_payment(-1000, 0.05, 12)  # Negative amount
        
        with self.assertRaises(ValueError):
            calculate_minimum_payment(1000, -0.05, 12)  # Negative rate
        
        with self.assertRaises(ValueError):
            calculate_minimum_payment(1000, 0.05, 0)  # Zero months
        
        with self.assertRaises(ValueError):
            calculate_minimum_payment(1000, 0.05, -12)  # Negative months

class TestProcessMonth(unittest.TestCase):
    def setUp(self):
        """Set up common test configurations."""
        self.standard_config = PaymentConfig(
            loan_amount=100000.0,
            loan_rate=0.05,  # 5%
            loan_term_months=360,
            target_payment=600.0,
            minimum_payment=536.82,  # Known correct minimum payment
            investment_rate=0.07,  # 7%
            tax_rate=0.25,  # 25%
            investment_type='CD',
            monthly_savings_payment=100.0
        )
        
        self.derived = DerivedConfig(minimum_payment=536.82)
        
        # Initial states
        self.initial_loan = LoanState(
            balance=100000.0,
            total_interest_paid=0.0,
            total_principal_paid=0.0
        )
        
        self.initial_savings = SavingsState(
            balance=10000.0,
            total_returns=0.0,
            total_taxes_paid=0.0,
            total_pocket_money=0.0
        )

    def test_standard_payment(self):
        """Test a standard monthly payment with no savings usage."""
        config = self.standard_config
        config.monthly_savings_payment = 0  # Disable savings usage
        
        result = process_month(config, self.derived, self.initial_loan, self.initial_savings)
        
        # First month's interest at 5% APR
        expected_interest = 100000 * (0.05 / 12)  # $416.67
        expected_principal = 600 - expected_interest  # $183.33
        
        self.assertAlmostEqual(result.interest_payment, expected_interest, places=2)
        self.assertAlmostEqual(result.principal_payment, expected_principal, places=2)
        self.assertAlmostEqual(result.new_loan_state.balance, 100000 - expected_principal, places=2)
        
        # Check savings growth (returns calculated on initial balance)
        monthly_return = 10000 * (0.07 / 12)  # $58.33
        monthly_tax = monthly_return * 0.25  # $14.58
        self.assertAlmostEqual(result.investment_returns, monthly_return, places=2)
        self.assertAlmostEqual(result.tax_payment, monthly_tax, places=2)

    def test_payment_with_savings(self):
        """Test using additional payment from savings."""
        result = process_month(self.standard_config, self.derived, self.initial_loan, self.initial_savings)
        
        # First calculate interest
        expected_interest = 100000 * (0.05 / 12)  # $416.67
        
        # Regular payment covers interest first
        target_interest = expected_interest
        target_principal = 600 - expected_interest  # $183.33
        
        # Additional payment from savings goes to principal
        savings_principal = 100  # Full savings amount goes to principal
        total_principal = target_principal + savings_principal
        
        self.assertAlmostEqual(result.principal_payment, total_principal, places=2)
        
        # For CDs:
        # 1. Initial balance: 10000
        # 2. Monthly return: 10000 * (0.07 / 12) = 58.33
        # 3. Tax on return: 58.33 * 0.25 = 14.58
        # 4. Withdrawal: 100 (no tax on withdrawal for CDs)
        # Final balance: 10000 + 58.33 - 14.58 - 100 = 9943.75
        self.assertAlmostEqual(result.new_savings_state.balance, 
                             10000 + (10000 * 0.07 / 12) - (10000 * 0.07 / 12 * 0.25) - 100,
                             places=2)

    def test_stock_investment(self):
        """Test with stock investment type (taxes only on withdrawal)."""
        config = self.standard_config
        config.investment_type = 'STOCK'
        
        result = process_month(config, self.derived, self.initial_loan, self.initial_savings)
        
        # Monthly return calculated on balance after withdrawal
        withdrawal = 100  # Monthly savings payment
        tax = withdrawal * 0.25  # 25% tax on withdrawal
        remaining_balance = 10000 - withdrawal - tax
        monthly_return = remaining_balance * (0.07 / 12)  # Return on remaining balance
        
        self.assertAlmostEqual(result.investment_returns, monthly_return, places=2)
        self.assertAlmostEqual(result.new_savings_state.balance, 
                             remaining_balance + monthly_return,
                             places=2)
        
        # Tax should only be on withdrawn amount
        self.assertAlmostEqual(result.tax_payment, tax, places=2)

    def test_pocket_money(self):
        """Test pocket money calculation when paying less than minimum."""
        config = self.standard_config
        config.target_payment = 500  # Less than minimum payment
        config.monthly_savings_payment = 0  # No savings usage to simplify test
        
        result = process_month(config, self.derived, self.initial_loan, self.initial_savings)
        
        # Pocket money should be difference between minimum and target
        expected_pocket = 536.82 - 500
        self.assertAlmostEqual(result.pocket_money, expected_pocket, places=2)
        self.assertAlmostEqual(result.new_savings_state.total_pocket_money, expected_pocket, places=2)

    def test_loan_payoff(self):
        """Test behavior when loan is nearly paid off."""
        small_balance_loan = LoanState(
            balance=500.0,  # Small remaining balance
            total_interest_paid=50000.0,
            total_principal_paid=99500.0
        )
        
        result = process_month(self.standard_config, self.derived, small_balance_loan, self.initial_savings)
        
        # Should only pay what's needed to clear the loan
        self.assertAlmostEqual(result.new_loan_state.balance, 0, places=2)
        self.assertTrue(result.principal_payment + result.interest_payment < self.standard_config.target_payment)
        
        # Remaining target payment should go to savings
        expected_savings = result.savings_contribution
        self.assertGreater(expected_savings, 0)

    def test_zero_balance_investment(self):
        """Test behavior after loan is paid off."""
        paid_loan = LoanState(
            balance=0.0,
            total_interest_paid=50000.0,
            total_principal_paid=100000.0
        )
        
        result = process_month(self.standard_config, self.derived, paid_loan, self.initial_savings)
        
        # All target payment should go to savings
        self.assertEqual(result.savings_contribution, self.standard_config.target_payment)
        self.assertEqual(result.principal_payment, 0)
        self.assertEqual(result.interest_payment, 0)

    def test_insufficient_savings(self):
        """Test behavior when savings balance is too low for desired payment."""
        low_savings = SavingsState(
            balance=50.0,  # Not enough for full payment
            total_returns=0.0,
            total_taxes_paid=0.0,
            total_pocket_money=0.0
        )
        
        result = process_month(self.standard_config, self.derived, self.initial_loan, low_savings)
        
        # Calculate expected balance after returns
        monthly_return = 50.0 * (0.07 / 12)  # Return on initial balance
        tax = monthly_return * 0.25  # CD tax on returns
        
        # Should only use what's available
        max_withdrawal = 50.0  # Initial balance
        
        # Final balance should be: initial + returns - tax - withdrawal
        expected_balance = 50.0 + monthly_return - tax - max_withdrawal
        self.assertLessEqual(result.new_savings_state.balance, expected_balance)
        self.assertGreaterEqual(result.new_savings_state.balance, 0)

if __name__ == '__main__':
    unittest.main() 