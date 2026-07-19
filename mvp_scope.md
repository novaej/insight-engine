# MVP Scope – Investment Insight API

## 1. MVP Objective
Validate that the system can generate **clear, useful, and explainable insights**  
about a small portfolio, using deterministic rules and natural language.

---

## 2. What the MVP Includes

### Functionality
- Analysis of stocks and ETFs
- Evaluation per asset
- Global portfolio evaluation
- Portfolio persistence (upsert on analyze, GET to retrieve, PUT to update and re-analyze)
- Daily insights
- Suggestion of alternatives
- Fixed user profile
- Manually entered portfolio
- Multi-language support (Azure Translator for AI-generated text)
- Parabolic SAR as a trend-confirming technical indicator

---

### Technology
- Backend-only  
- REST API  
- Python + FastAPI  
- PostgreSQL  
- Scheduled monitoring jobs (APScheduler) with Mailgun email alerts  
- External APIs for financial data  
- OpenAI API used only for textual explanation

---

## 3. What the MVP Does NOT Include

### Excluded Functionality
- Authentication / multiple users  
- Integration with brokers (e.g., XTB)  
- Purchase price / PnL tracking  
- Real-time alerts  
- Trading / execution  
- Cryptocurrencies  
- Advanced machine learning

---

## 4. MVP Assumptions

- Multi-user capable (email/password + bearer token), personal / experimental use  
- 1 portfolio per user  
- Max 20 distinct tickers (multiple purchase lots per ticker allowed)  
- Data may be delayed  
- Tolerance for imperfect data

---

## 5. Success Criteria

The MVP is successful if:  
- The user understands why they hold each asset  
- The system detects clear risks  
- Explanations are coherent and consistent  
- No buy/sell signals are generated  
- The user trusts the process more than the specific outcome

---

## 6. Future Evolution (outside MVP)

- Multi-user support  
- Authentication  
- Visual dashboards  
- Insight history  
- Temporal comparison  
- ETF-specific rules  
- Advanced automation
