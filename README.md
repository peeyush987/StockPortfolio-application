# Portfolio Management App

## Overview
This is a stock portfolio web application developed using **Flask**. It allows users to register, log in, buy and sell stocks, retrieve live stock quotes via the **Alpha Vantage API**, and track their transaction history. The application enables users to manage a virtual stock portfolio efficiently and securely.

## Features
- User Registration & Login (with session and password hashing)
- Real-time stock quotes (Alpha Vantage API)
- Buy and Sell stocks functionality
- View transaction history with time stamps
- Input validation and error handling
- Lightweight SQLite database

## About the Project
The Portfolio Management App is a simple, beginner-friendly stock trading simulation built with Flask. Upon registration, each user receives a virtual $10,000 in dummy funds to practice basic stock market transactions. 

Users can log in, view real-time stock quotes using the Alpha Vantage API, and perform buy/sell operations on available stocks. The app tracks user portfolios and logs all transactions, providing a basic history of trades.

This project is designed to demonstrate core web development concepts, including authentication, external API integration, CRUD operations, and transaction logging. The goal is to provide a functional and straightforward platform for learning how basic stock trading and web applications work.

## Tech Stack
- Python (Flask Framework)
- HTML5, CSS3, Bootstrap (Frontend)
- Jinja2 Templating Engine
- SQLite (Database)
- Alpha Vantage API (Stock data integration)

## Folder Structure
/portfolio-app
│── /static
│    └── style.css
│── /templates
|    |── apology.html
│    ├── index.html
│    ├── login.html
|    |── layout.html
│    ├── register.html
│    ├── quote.html
│    ├── buy.html
│    ├── sell.html
│    └── history.html
│── app.py
│── requirements.txt
│── README.md
│── /instance
└── finance.db

## Installation & Setup
1. Clone this repository
2. Create and activate a virtual environment
3. Install required dependencies
4. Add your **Alpha Vantage API key** inside `app.py` securely.
5. Run the Flask app

## Future Improvements

1. **User Dashboard & Portfolio Analytics**
   - Introduce a dashboard with charts and graphs to visualize the user's portfolio, profit/loss, and stock performance trends using libraries like Chart.js or Plotly.

2. **Deposit & Withdraw Virtual Funds**
   - Allow users to "top up" or "withdraw" virtual funds to simulate more realistic portfolio management and budgeting scenarios.

3. **Stock Price History & Candlestick Charts**
   - Integrate historical stock price data and display candlestick or line charts to help users make more informed buying and selling decisions.

4. **Enhanced Transaction History**
   - Add sorting and filtering capabilities (e.g., by date range, stock symbol, type of transaction) to improve usability when reviewing trade history.

5. **User Notifications**
   - Implement flash messages or even email notifications (via SMTP) to alert users of successful transactions, errors, or stock price alerts.

6. **Real Authentication with OAuth2**
   - Support login via Google, GitHub, or other OAuth providers for added convenience and security.

7. **Leaderboard**
   - Create a leaderboard system where users can compare their portfolio performance against other users to make the app more competitive.

8. **Deploy on Cloud**
   - Deploy the app to Heroku, Render, or a VPS so users can access it publicly. This will also involve setting up environment variables for API keys securely.

9. **Admin Panel**
   - Develop an admin interface to manage users, monitor activity, and adjust dummy funds if necessary.

10. **API Key Security**
    - Refactor the code to store API keys securely using environment variables and `.env` files to prevent exposure.

## Contact

Developed by Peeyush Bhandari 
**Email:** Peeyushbhandari26@gmail.com  
**LinkedIn:** https://www.linkedin.com/in/peeyush-bhandari-1645b2282/
