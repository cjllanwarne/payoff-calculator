import unittest
from calculator import PaymentConfig
from simulation import run_simulation

class TestSimulation(unittest.TestCase):
    def test_five_year_cd_scenario(self):
        """Test a 5-year scenario with CD investment and excess to savings.
        
        Initial setup:
        - $50,000 loan at 5% APR
        - 5 year term
        - $1,000 target monthly payment
        - $10,000 initial savings
        - $2,000 lump sum payment
        - CD at 3% APR, 25% tax rate
        - Excess goes to savings
        
        Expected outcomes calculated:
        1. Monthly minimum payment = $943.56
        2. Monthly excess = $1,000 - $943.56 = $56.44 to savings
        3. Initial loan reduction = $2,000 (lump sum)
        4. CD returns = 3% APR on remaining $8,000 = $20/month pre-tax
        5. Tax on returns = $5/month
        """
        config = PaymentConfig(
            loan_amount=50000,
            loan_rate=0.05,  # 5% APR
            loan_term_months=60,
            target_payment=1000,
            initial_savings=10000,
            monthly_savings_payment=0,
            investment_rate=0.03,  # 3% APR
            tax_rate=0.25,  # 25% tax rate
            investment_type="CD",
            excess_to_savings=True
        )
        
        result = run_simulation(config=config, lump_sum=2000)
        
        # Test initial values
        self.assertAlmostEqual(result.loan_balance[0], 48000, 2)  # 50k - 2k lump sum
        self.assertAlmostEqual(result.savings_balance[0], 8000, 2)  # 10k - 2k lump sum
        
        # Test first month values (after lump sum)
        self.assertAlmostEqual(result.loan_payments[1], 943.56, 2)  # Minimum payment
        self.assertAlmostEqual(result.savings_contributions[1], 56.44, 2)  # Excess to savings
        self.assertAlmostEqual(result.pocket_money[1], 0, 2)  # No pocket money in first month
        
        # Test final values
        self.assertLess(result.loan_balance[-1], 100)  # Loan nearly paid off
        self.assertGreater(result.savings_balance[-1], 11500)  # Growth from excess + returns
        
    def test_one_year_stock_scenario(self):
        """Test a 1-year scenario with stock investment and no excess to savings.
        
        Setup:
        - $12,000 loan at 4% APR
        - 1 year term
        - Exactly minimum payment
        - $5,000 initial savings
        - No lump sum
        - Stock at 7% APR, 15% tax rate
        - No excess (minimum = target payment)
        """
        config = PaymentConfig(
            loan_amount=12000,
            loan_rate=0.04,
            loan_term_months=12,
            target_payment=1040.25,  # Calculated minimum payment
            initial_savings=5000,
            monthly_savings_payment=0,
            investment_rate=0.07,
            tax_rate=0.15,
            investment_type="STOCK",
            excess_to_savings=False
        )
        
        result = run_simulation(config=config, lump_sum=0)
        
        # Test that loan is paid off in exactly 12 months
        self.assertEqual(len(result.loan_balance), 12)
        self.assertLess(result.loan_balance[-1], 1)
        
        # Test that savings grew at expected rate (no withdrawals)
        expected_final_savings = 5000 * (1 + 0.07)  # One year of growth, no tax yet
        self.assertAlmostEqual(result.savings_balance[-1], expected_final_savings, 2)
        
    def test_thirty_year_mortgage_scenario(self):
        """Test a 30-year mortgage scenario with aggressive savings strategy.
        
        Setup:
        - $500,000 loan at 6% APR
        - 30 year term
        - $500 extra payment monthly
        - $100,000 initial savings
        - Stock at 8% APR, 20% tax rate
        - All excess to savings
        """
        config = PaymentConfig(
            loan_amount=500000,
            loan_rate=0.06,
            loan_term_months=360,
            target_payment=3500,  # About $500 more than minimum
            initial_savings=100000,
            monthly_savings_payment=0,
            investment_rate=0.08,
            tax_rate=0.20,
            investment_type="STOCK",
            excess_to_savings=True
        )
        
        result = run_simulation(config=config, lump_sum=0)
        
        # Test length of simulation
        self.assertEqual(len(result.loan_balance), 360)
        
        # Test that savings grew substantially
        self.assertGreater(result.savings_balance[-1], 100000)  # Should have grown significantly
        self.assertGreater(result.total_pocket_money, 0)  # Should have some pocket money
        
    def test_edge_case_zero_interest(self):
        """Test edge case with 0% interest rates."""
        config = PaymentConfig(
            loan_amount=10000,
            loan_rate=0.0,
            loan_term_months=12,
            target_payment=1000,
            initial_savings=1000,
            monthly_savings_payment=0,
            investment_rate=0.0,
            tax_rate=0.0,
            investment_type="CD",
            excess_to_savings=False
        )
        
        result = run_simulation(config=config, lump_sum=0)
        
        # Test that loan decreases linearly
        self.assertAlmostEqual(result.loan_balance[6], 5000, 2)  # Half paid at halfway point
        self.assertAlmostEqual(sum(result.interest_payments), 0, 2)  # No interest paid
        
    def test_edge_case_immediate_payoff(self):
        """Test edge case where savings can immediately pay off loan."""
        config = PaymentConfig(
            loan_amount=10000,
            loan_rate=0.05,
            loan_term_months=12,
            target_payment=1000,
            initial_savings=20000,
            monthly_savings_payment=0,
            investment_rate=0.03,
            tax_rate=0.25,
            investment_type="CD",
            excess_to_savings=True
        )
        
        result = run_simulation(config=config, lump_sum=10000)
        
        # Test immediate payoff
        self.assertEqual(len(result.loan_balance), 1)  # Only initial state
        self.assertAlmostEqual(result.loan_balance[0], 0, 2)  # Loan fully paid
        self.assertAlmostEqual(result.savings_balance[0], 10000, 2)  # Remaining savings

        # Savings after 12 months
        self.assertAlmostEqual(result.savings_balance[12], 10000 + 10000 * 0.03 / 12, 2)

if __name__ == '__main__':
    unittest.main() 