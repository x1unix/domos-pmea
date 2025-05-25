# Assignment Brief - Domos Founding Engineer

Build a **Property‑Manager Email (AI Powered) Assistant**: a small Python service that
connects to an email inbox, triages unread messages, generates response, and triggers
relevant workflows.
We expect you to spend 3-5 hours on this exercise (and provide details about what you would
do with more time).

## Minimum Functional Requirements

| #   | Requirement              | Details & Hints                                                                                                                                         |
|-----|--------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | Connect to an Inbox      | Gmail, feel free to use imaplib. You can spin up a throw-away account.                                                                              |
| 2   | Fetch Unread Messages    | Only recent.                                                                                                                                           |
| 3a  | Load relevant information| Assume we have access to all relevant information (balance, past conversations, etc.). You can mimic the data/requests for simplicity.              |
| 3b  | Generate a Draft Reply   | Input: raw email. Output: ready-to-send plain-text reply. Use whatever technique you like—rule-based, templating, LLM, etc., but explain your choice.|
| 3c  | Create Action Items      | e.g., create maintenance ticket, JSON file output is sufficient.                                                                                       |
| 3d  | Send Email               | Include relevant stakeholder if needed.                                                                                                                |

## Example emails from residents

Below are several examples of emails that property managers deal with:

1. **Subject:** help!  
   **Content:** Greenwich ave, I locked myself out and I need access to my apartment

2. **Subject:** rent  
   **Content:** Good night, I'm Wilkin Dan the tenant of 2000 Holland Av Apt 1F.  
   I'm writing because I received a message from you. I need to tell you, I have the money order for the payment, but I'm not going to send you until you fix the toilet. The apartment is in so bad condition.

3. **Subject:** Lease terms  
   **Content:** Hello, I’m writing on behalf of my sister Miki at 100 Holland Av Apt 2D. Can you let me know what is our monthly rent?

4. **Subject:** call me back please  
   **Content:** I’m available tomorrow 4pm.

## Why This Exercise?

The task mirrors Domos’ real‑world challenges—email ingestion, intelligent triage, and
lightweight workflow orchestration. We care less about polishing every edge and more about
your judgment, structure, and ability to communicate trade‑offs.
Feel free to ask clarifying questions before you start.
