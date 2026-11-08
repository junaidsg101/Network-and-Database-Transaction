# Project_Define.md - Product Requirements Document (PRD)

## 1. Product Vision & Objective
To build an AI Agentic Fintech Application that ensures fair, inclusive, and highly secure financial services. The product leverages ML Ops and advanced database architectures to eliminate "discrimination laundering" (where infrastructure failures are penalized as fraud) and to guarantee zero data-loss in high-concurrency transaction environments.

## 2. Problem Statements

### Problem 1: Fraud Detection & Network Timeouts (Discrimination Laundering)
Fintech algorithms use historical proxy variables for credit scoring and fraud detection. In regions with poor infrastructure (e.g., rural Nigeria), network timeouts or electricity drops cause transaction failures. The system incorrectly flags these infrastructure weaknesses as individual dishonesty or fraud, rejecting accounts and pushing rural users out of the digital economy.

### Problem 2: Database Concurrent Transaction Exclusion Locks
In high-traffic fintech systems, multiple processes attempt to read and write to the same data (e.g., account balance) simultaneously. 
*   **Read + Write Conflicts:** Traditional locks slow down the system. If eventual consistency is used, parallel transactions might read outdated balances, leading to overdrafts.
*   **Write + Write Conflicts:** Parallel writes can cause double-spending and severe financial loss if not strictly serialized and verified.

## 3. Proposed Solutions & Product Logic

### Solution 1: Agentic AI Intervention for Network Timeouts
Instead of instantly rejecting a user for a timeout, the system will deploy an AI Agent to intervene:
*   **Direct Communication:** The AI agent (or human fallback) will initiate a direct SIM call or SMS to the user to verify intent.
*   **Session Persistence:** The user's previous state and data will be saved in a temporary cache for 5 hours to prevent data loss.
*   **Contextual Awareness:** The system will check social and environmental proxy variables (e.g., regional network outage data) to distinguish between infrastructure failure and actual fraud.
*   **Tiered Access:** 
    *   *New Customers:* Simple options are restricted until verified.
    *   *Returning Customers:* Historical proxy variables are used for seamless, frictionless verification.
*   **Hierarchical Triage:** A Human-AI triage model will handle escalations.
*   **Financial Literacy:** The system will mandate weekly/monthly check-ins to educate users on digital fairness and recognize unfair treatment.

### Solution 2: Distributed Database & ACID Guarantees
To handle concurrent transactions without blocking or losing data:
*   **Read + Write Strategy:** The system uses two distributed databases. A separate timeout is set for the first write operation. If the writer delays, the second reader is granted "Limited Read" access (viewing only the last known safe balance) to prevent overdrafts.
*   **Write + Write Strategy:** Both write operations are allowed to execute in parallel on the same database and account. The system strictly verifies the serial order and transaction results. The final account balance is mathematically reconciled against the pre-transaction state before committing.
*   **Technology Stack:** Apache Ignite will be used as the universal transaction model to guarantee strict ACID properties across all APIs.
*   **Performance Targets:** Balance updates and fraud checks will run concurrently without blocking. The system will guarantee 10,000 Transactions Per Second (TPS) for new users and 50,000 TPS for the overall company.

## 4. Feature Requirements

### 4.1 AI Agentic Features
*   **Timeout Interceptor:** Detects network timeouts and triggers the AI agent workflow.
*   **Communication Agent:** Capable of triggering telephony (SIM calls) and SMS gateways.
*   **Environmental Context Engine:** Ingests third-party data regarding regional network stability and power grid status.
*   **Triage Router:** Routes complex or highly ambiguous cases from the AI agent to human support staff.

### 4.2 ML Ops & Fraud Detection Features
*   **Proxy Variable Engine:** Analyzes historical data to score returning users without relying on real-time network stability.
*   **Literacy Tracker:** Schedules and tracks user engagement with financial literacy modules.

### 4.3 Database & Backend Features
*   **Distributed Lock Manager:** Manages the 5-hour session cache and enforces the "Limited Read" state during write delays.
*   **Parallel Write Reconciler:** Executes parallel writes and runs the post-transaction mathematical verification.
*   **Apache Ignite Integration:** Manages the in-memory data grid to ensure ACID compliance at high throughput.

## 5. Non-Functional Requirements

*   **Performance:** 
    *   New User Throughput: 10,000 TPS.
    *   Company-wide Throughput: 50,000 TPS.
    *   Fraud check and balance update latency: < 50ms (non-blocking).
*   **Reliability:** 99.99% uptime for the core transaction ledger.
*   **Data Integrity:** 100% ACID compliance. Zero tolerance for double-spending or overdrafts due to race conditions.
*   **Fairness & Compliance:** The fraud model must pass regular audits to ensure infrastructure metrics (like timeout rates) are not weighted as negative behavioral traits (preventing discrimination laundering).

## 6. System Architecture Overview (High-Level)

1.  **Frontend Layer:** React/TypeScript UI providing real-time feedback on transaction states, limited-read modes, and AI agent interventions.
2.  **API Gateway:** Routes requests, handles rate limiting, and directs timeout events to the Agentic AI layer.
3.  **Agentic AI & ML Ops Layer:** 
    *   Hosts the Hierarchical Triage Model.
    *   Manages the 5-hour Redis/Cache session state.
    *   Interfaces with Telephony/SMS providers.
4.  **Transaction Processing Layer:** 
    *   Hosts the Parallel Write Reconciler.
    *   Manages the Distributed Read/Write Lock logic.
5.  **Data Layer:** 
    *   **Apache Ignite:** Primary distributed in-memory database for ACID transactions and high TPS.
    *   **Secondary Distributed DB:** Used for fallback reads and historical proxy variable storage.

## 7. Success Metrics

*   **Reduction in False Positives:** 90% decrease in fraud flags caused by network timeouts in rural/low-infrastructure areas.
*   **Transaction Success Rate:** Increase in successful transaction completions for users experiencing intermittent connectivity.
*   **Zero Financial Leakage:** 0 instances of overdraft or double-spending caused by concurrent transaction race conditions.
*   **User Literacy Engagement:** > 60% completion rate of the monthly/weekly financial literacy check-ins.