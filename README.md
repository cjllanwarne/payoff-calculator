# Debt Payoff vs Investment Calculator

This Streamlit application helps you analyze the trade-off between paying off debt and investing money. It calculates and visualizes how different payment strategies affect your loan balance and potential investment returns over time.

## Features

- Input your loan details including remaining debt, interest rate, and term
- Set up investment parameters including returns and tax considerations
- Compare different payment strategies with lump sum and monthly payments
- Visualize loan balance vs savings over time
- See detailed breakdown of principal and interest payments
- Support for different investment types (CDs vs Stocks) with appropriate tax handling

## Installation

1. Clone this repository
2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the Streamlit app:
```bash
streamlit run app.py
```

The application will open in your default web browser. Enter your loan and investment details to see the analysis.

## Input Parameters

### Loan Details
- Remaining debt amount
- Debt interest rate
- Loan term in years
- Target monthly payment (can be more or less than minimum payment)

### Investment Details
- Lump sum payoff amount
- Lump sum payment timing
- Anticipated investment return rate
- Investment type (CD or Stocks)
- Applicable tax rate

## Analysis

The calculator shows:
1. Balance over time for both loan and savings
2. Monthly payment breakdown between principal and interest
3. Summary statistics including total interest paid and final savings balance

## Notes

- All calculations assume monthly compounding
- CD investments are taxed monthly on earned interest
- Stock investments are taxed only when money is withdrawn for loan payments
- The calculator assumes all excess payments (above minimum) go to savings when the loan is paid off 

## How the Calculation Works

The calculator performs a month-by-month analysis of debt payoff with optional investment of savings, following a "debt first" approach. Here's how it works:

### Initial Setup
1. Calculate minimum monthly payment based on loan amount, term, and interest rate
2. Process any initial lump sum payment to reduce principal
3. Determine monthly payment capacity (can be above minimum payment)
4. Set up tracking for any existing savings that could be used for debt

### Monthly Analysis Loop
For each month until the loan is paid off:

1. Calculate interest for the month based on current balance
2. Apply the desired target monthly payment as part of the monthly payment
   - First portion covers interest
   - Remainder reduces principal
3. If savings are available and configured to be used:
   - Apply additional payment from savings
   - Reduce available savings accordingly (after accounting for withdrawal tax, if applicable)
4. Apply any remaining minimum payment as part of the monthly payment
5. Track:
   - Remaining loan balance
   - Total interest paid
   - Total principal paid
   - Total savings contributions
   - Total pocket money (difference between target and minimum payments)
   - Remaining savings (if any)

### Post-Debt-Payoff Phase
Once the loan is paid off:
1. Redirect former debt payments to investments, up to the target monthly payment
2. Calculate investment returns (compounded monthly)
3. Apply appropriate taxes based on investment type:
   - CDs: Monthly tax on interest earned
   - Stocks: Tax only on withdrawals

### Final Analysis
- Total time to debt freedom
- Total interest paid on loan
- Final investment balance
- Net worth impact

```mermaid
flowchart TD
    A[Start] --> B[Calculate Minimum Payment]
    B --> C[Apply Initial Lump Sum]
    C --> D[Begin Monthly Analysis]
    
    D --> E[Calculate Monthly Interest]
    E --> F[Apply Monthly Payment]
    F --> G[Reduce Principal]
    
    G --> H{Have Available<br>Savings?}
    H -->|Yes| I[Apply Extra<br>Payment from Savings]
    H -->|No| J[Next Month]
    I --> J
    
    J --> K{Loan Paid Off?}
    K -->|No| D
    K -->|Yes| L[Begin Investment Phase]
    
    L --> M[Invest Former<br>Debt Payments]
    M --> N[Calculate Returns<br>& Apply Taxes]
    N --> O[Update Investment<br>Balance]
    O --> P{Term Complete?}
    P -->|No| M
    P -->|Yes| Q[Generate Final Report]
    Q --> R[End]
``` 
