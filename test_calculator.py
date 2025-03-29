import unittest
from calculator import (
    calculate_minimum_payment, process_month,
    PaymentConfig, LoanState, SavingsState
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
            initial_savings=10000.0,
            monthly_savings_payment=100.0,
            investment_rate=0.07,  # 7%
            tax_rate=0.25,  # 25%
            investment_type='CD',
            excess_to_savings=False
        )
        
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
        
        result = process_month(config, self.initial_loan, self.initial_savings)
        
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
        result = process_month(self.standard_config, self.initial_loan, self.initial_savings)
        
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
        
        result = process_month(config, self.initial_loan, self.initial_savings)
        
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
        
        result = process_month(config, self.initial_loan, self.initial_savings)
        
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
        
        result = process_month(self.standard_config, small_balance_loan, self.initial_savings)
        
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
        
        result = process_month(self.standard_config, paid_loan, self.initial_savings)
        
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
        
        result = process_month(self.standard_config, self.initial_loan, low_savings)
        
        # Calculate expected balance after returns
        monthly_return = 50.0 * (0.07 / 12)  # Return on initial balance
        tax = monthly_return * 0.25  # CD tax on returns
        
        # Should only use what's available
        max_withdrawal = 50.0  # Initial balance
        
        # Final balance should be: initial + returns - tax - withdrawal
        expected_balance = 50.0 + monthly_return - tax - max_withdrawal
        self.assertLessEqual(result.new_savings_state.balance, expected_balance)
        self.assertGreaterEqual(result.new_savings_state.balance, 0)

    def test_reinvestment_after_payoff(self):
        """Test reinvestment behavior after loan is paid off."""
        # Start with a paid off loan
        paid_loan = LoanState(
            balance=0.0,
            total_interest_paid=50000.0,
            total_principal_paid=100000.0
        )
        
        # Initial savings with some returns already
        initial_savings = SavingsState(
            balance=20000.0,
            total_returns=1000.0,
            total_taxes_paid=250.0,
            total_pocket_money=0.0
        )
        
        result = process_month(self.standard_config, paid_loan, initial_savings)
        
        # All target payment should go to savings
        monthly_return = 20000 * (0.07 / 12)  # Return on initial balance
        tax = monthly_return * 0.25  # CD tax on returns
        expected_balance = (20000 + monthly_return - tax + 
                          self.standard_config.target_payment)
        
        self.assertAlmostEqual(result.new_savings_state.balance, expected_balance, places=2)
        self.assertAlmostEqual(result.savings_contribution, 
                             self.standard_config.target_payment, places=2)
        self.assertEqual(result.principal_payment, 0)
        self.assertEqual(result.interest_payment, 0)

    def test_maximum_savings_withdrawal(self):
        """Test that savings withdrawal respects monthly limit."""
        # Configure a high monthly savings payment
        config = self.standard_config
        config.monthly_savings_payment = 1000.0  # Try to withdraw more than needed
        
        # Create a small loan balance to test withdrawal limits
        small_loan = LoanState(
            balance=1000.0,
            total_interest_paid=0.0,
            total_principal_paid=0.0
        )
        
        result = process_month(config, small_loan, self.initial_savings)
        
        # Calculate maximum withdrawal needed
        monthly_interest = 1000.0 * (0.05 / 12)  # Interest on remaining balance
        total_needed = 1000.0 + monthly_interest  # Total needed to pay off loan
        from_target = min(600.0, total_needed)  # Amount from target payment
        max_needed = total_needed - from_target  # Maximum needed from savings
        
        # Should not withdraw more than needed
        self.assertLessEqual(result.principal_payment + result.interest_payment - 600.0,
                           max_needed)
        self.assertGreaterEqual(result.new_loan_state.balance, 0)

    def test_small_numbers_precision(self):
        """Test handling of very small numbers for returns and taxes."""
        # Use a paid off loan so all target payment goes to savings
        paid_loan = LoanState(
            balance=0.0,
            total_interest_paid=0.0,
            total_principal_paid=0.0
        )
        
        tiny_savings = SavingsState(
            balance=0.01,  # Very small balance
            total_returns=0.0,
            total_taxes_paid=0.0,
            total_pocket_money=0.0
        )
        
        result = process_month(self.standard_config, paid_loan, tiny_savings)
        
        # Verify no precision loss
        monthly_return = 0.01 * (0.07 / 12)  # Return on initial balance
        tax = monthly_return * 0.25  # Tax on returns
        expected_balance = 0.01 + monthly_return - tax + self.standard_config.target_payment
        
        self.assertAlmostEqual(result.new_savings_state.balance, expected_balance, places=8)
        self.assertGreaterEqual(result.new_savings_state.balance, 0)
        self.assertAlmostEqual(result.investment_returns, monthly_return, places=8)
        self.assertAlmostEqual(result.tax_payment, tax, places=8)

    def test_order_of_operations(self):
        """Test that returns, taxes, and withdrawals happen in correct order."""
        config = self.standard_config
        config.investment_type = 'CD'
        config.monthly_savings_payment = 100.0
        
        initial_savings = SavingsState(
            balance=1000.0,
            total_returns=0.0,
            total_taxes_paid=0.0,
            total_pocket_money=0.0
        )
        
        result = process_month(config, self.initial_loan, initial_savings)
        
        # For CDs:
        # 1. Calculate returns on initial balance
        monthly_return = 1000.0 * (0.07 / 12)
        # 2. Calculate tax on returns
        tax = monthly_return * 0.25
        # 3. Make withdrawal (no tax for CDs)
        withdrawal = 100.0
        # 4. Final balance
        expected_balance = 1000.0 + monthly_return - tax - withdrawal
        
        self.assertAlmostEqual(result.new_savings_state.balance, expected_balance, places=2)
        self.assertAlmostEqual(result.investment_returns, monthly_return, places=2)
        self.assertAlmostEqual(result.tax_payment, tax, places=2)

    def test_excess_to_principal(self):
        """Test that excess payment goes to principal when excess_to_savings is False."""
        config = self.standard_config
        config.target_payment = 1000.0  # More than minimum (536.82)
        config.excess_to_savings = False
        config.monthly_savings_payment = 0  # Disable savings usage to simplify test
        
        result = process_month(config, self.initial_loan, self.initial_savings)
        
        # First month's interest at 5% APR
        expected_interest = 100000 * (0.05 / 12)  # $416.67
        expected_principal = 1000 - expected_interest  # $583.33
        
        self.assertAlmostEqual(result.interest_payment, expected_interest, places=2)
        self.assertAlmostEqual(result.principal_payment, expected_principal, places=2)
        self.assertEqual(result.savings_contribution, 0)

    def test_excess_to_savings(self):
        """Test that excess payment goes to savings when excess_to_savings is True."""
        config = self.standard_config
        config.target_payment = 1000.0  # More than minimum (536.82)
        config.excess_to_savings = True
        config.monthly_savings_payment = 0  # Disable savings usage to simplify test
        
        result = process_month(config, self.initial_loan, self.initial_savings)
        
        # First month's interest at 5% APR
        expected_interest = 100000 * (0.05 / 12)  # $416.67
        expected_principal = config.minimum_payment - expected_interest  # $120.15
        expected_excess = config.target_payment - config.minimum_payment  # $463.18
        
        self.assertAlmostEqual(result.interest_payment, expected_interest, places=2)
        self.assertAlmostEqual(result.principal_payment, expected_principal, places=2)
        self.assertAlmostEqual(result.savings_contribution, expected_excess, places=2)
        
        # Verify savings balance includes the excess payment
        expected_savings = (
            10000 +  # Initial balance
            (10000 * 0.07 / 12) -  # Returns
            (10000 * 0.07 / 12 * 0.25) +  # Tax on returns
            expected_excess  # Excess payment
        )
        self.assertAlmostEqual(result.new_savings_state.balance, expected_savings, places=2)

    def test_excess_to_savings_with_savings_payment(self):
        """Test interaction between excess_to_savings and monthly_savings_payment."""
        config = self.standard_config
        config.target_payment = 1000.0  # More than minimum (536.82)
        config.excess_to_savings = True
        config.monthly_savings_payment = 100.0
        
        result = process_month(config, self.initial_loan, self.initial_savings)
        
        # When excess goes to savings, monthly_savings_payment should not be used
        expected_interest = 100000 * (0.05 / 12)  # $416.67
        expected_principal = config.minimum_payment - expected_interest  # $120.15
        expected_excess = config.target_payment - config.minimum_payment  # $463.18
        
        self.assertAlmostEqual(result.interest_payment, expected_interest, places=2)
        self.assertAlmostEqual(result.principal_payment, expected_principal, places=2)
        self.assertAlmostEqual(result.savings_contribution, expected_excess, places=2)
        
        # Verify no additional payment was taken from savings
        expected_savings = (
            10000 +  # Initial balance
            (10000 * 0.07 / 12) -  # Returns
            (10000 * 0.07 / 12 * 0.25) +  # Tax on returns
            expected_excess  # Excess payment
        )
        self.assertAlmostEqual(result.new_savings_state.balance, expected_savings, places=2)

if __name__ == '__main__':
    unittest.main() 