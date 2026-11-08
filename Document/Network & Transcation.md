## Project Name: Network & Database Transaction

There are two major problem for banking face.

### **Fraud Detection Problem:** Network Timeout the system score fraud detection

Solution: 
When a user has a network timeout or electricity problem, the AI agent or human support should call the user directly by SIM call or message. The system should also save the user’s previous data for 5 hours. The AI agent should check the social and environmental situation too. For new customers, do not allow every simple option. For previous customers, use credit scoring and fraud detection, and use proxy variables from historical data. At the technical level, use a hierarchical human-AI triage model.

To help users, increase financial literacy so they can understand digital services and recognize unfair treatment. Also conduct a weekly or monthly check-in with users.

-------------
### **Exclusion Lock:** Database Concurrent Transaction,   (Read + Write) | (Write + Write)

Solution:
For the (Read + Write) solution, define two distributed databases. Set a separate timeout for the first write operation. If the first writer or user causes a delay, allow the second reader user to do only limited read operations.

For the (Write + Write) solution, allow both operations at the same time. Use two distributed databases, and let the transaction happen on the same database and the same account. If the serial order and transaction result are correct, and even the account balance is the same as before and after the final result, then allow the (Write + Write) operation.

Guarantee ACID properties across all APIs. Keep data accuracy at 10,000 per second for new users and 50,000 per second for the company. Balance updates and fraud checks should run at the same time without blocking each other. Use a universal transaction model such as Apache Ignite to guarantee ACID properties across all APIs. This allows balance updates and fraud checks to run together without blocking each other.
