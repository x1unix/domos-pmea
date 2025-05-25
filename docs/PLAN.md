# Property Manager Email Assistant - Implementation Plan

## Project Overview

The Property Manager Email Assistant is a Python-based **daemon service** that automates email communication for property management systems. The service monitors an email inbox, processes incoming messages using an AI agent, generates appropriate responses, and triggers relevant actions based on the email content and agent decisions. This plan focuses on a simplified version suitable for a rapid prototype.

## High-level approach

RAG receives a message from client via email.

RAG can request additional information for context using tool calls and/or ask additional information from user.

If user requests some action (call me, etc.) - RAG should create and forward mail to property manager.

## Technology Stack

### Core Components

1. **Python 3.13+** - Main programming language.
2. **Pydantic** - For data validation and settings management (e.g., email credentials, LLM API keys).
3. **asyncio** - For asynchronous programming support.

### Email Integration

- **aioimaplib** - For asynchronous IMAP email access and monitoring.
- **aiosmtplib** - For asynchronous SMTP email sending.
- **email** (Python built-in) - For email parsing.

### AI/NLP Components

- **LangChain** - For AI workflow orchestration, prompt management, agent creation, and tool integration. Alternatively, use the LLM's native function/tool calling capabilities.

### Local Persistence (Optional for PoC)

- **SQLite** (Python built-in `sqlite3`) - For minimal state persistence (e.g., tracking processed email IDs to avoid reprocessing).

### Development & Quality

- **yaml** - For managing secrets like API keys and email credentials.
- **pytest** - For unit testing (as time permits).
- **black, flake8, mypy** - For code quality (use as time permits).

## System Architecture

### Components Overview

1. **Async Email Monitor**
    - Asynchronously connects to the IMAP server to monitor for new emails.
    - Uses `aioimaplib` for non-blocking email operations.
    - Parses email content (sender, subject, body, basic attachments if feasible).
    - Passes new emails to the AI Processing Agent.
    - Marks emails as read or moves them after processing.

2. **AI Processing Agent**
    - Utilizes an LLM (e.g., Gemini) configured as an agent with access to predefined tools.
    - Analyzes email content to understand intent, extract key information, and decide on next steps.
    - Can invoke tools to perform actions like drafting a reply, categorizing the email, or logging information.

3. **Async Tool Executor & Action Handler**
    - A set of async Python functions (tools) that the AI agent can call.
    - Examples: `async def draft_reply(email_content, query)`, `async def categorize_email(email_content)`, `async def log_maintenance_request(details)`.
    - Handles the asynchronous execution of these tools, which might include sending an email via SMTP.

   #### Detailed Tool Definitions

    1. **`async def get_property_tenant_details(address: Optional[str] = None, tenant_name: Optional[str] = None, tenant_email: Optional[str] = None, property_id: Optional[int] = None) -> dict`**
        - **Purpose**: Retrieves detailed information about a property and its tenant from a data source (e.g., `data/properties_db.json`). This is crucial for identifying the sender, their address, rent details, and the relevant stakeholder/property manager.
        - **Motivation/Reasoning**: This tool is essential for satisfying Requirement #3a ("Load relevant information"). It allows the AI to understand who the sender is, what property they are associated with, their current rent, and who the responsible property manager/stakeholder is. This context is vital for personalizing responses (e.g., addressing the tenant by name, confirming their address for a lockout) and for routing issues or information correctly (e.g., knowing the monthly rent for a query, or the stakeholder to notify). It supports handling example emails like "rent", "Lease terms", and "help!".
        - **Parameters**:
            - `address` (Optional\[str]): Full or partial address of the property.
            - `tenant_name` (Optional\[str]): Name of the tenant.
            - `tenant_email` (Optional\[str]): Email address of the tenant.
            - `property_id` (Optional\[int]): Unique identifier for the property.
            (At least one parameter should be provided for lookup.)
        - **Returns**: A list of dictionaries, where each dictionary closely matches the structure in `data/properties_db.json`: `property_id`, `building_number`, `street_name`, `city`, `unit`, `tenant` (an object with `name`, `email`, `phone`), `stakeholder_email`, `monthly_rent_usd_cents`. Returns an empty list (`[]`) if no matching properties are found.

    2. **`async def draft_ai_reply(original_email_body: str, original_email_subject: str, sender_email: str, identified_intent: str, context_data: Optional[dict] = None, proposed_actions: Optional[list[str]] = None, tone: str = "professional and helpful") -> dict`**
        - **Purpose**: Generates a context-aware, ready-to-send plain-text email reply using an LLM. This tool takes the analyzed information and crafts a suitable response.
        - **Motivation/Reasoning**: This directly addresses Requirement #3b ("Generate a Draft Reply"). The AI agent needs a mechanism to formulate responses. This tool provides that capability, allowing the agent to use the original email's content, its identified intent, and any fetched contextual data (like property details) to generate a relevant and helpful reply. It's a core component for automating communication.
        - **Parameters**:
            - `original_email_body` (str): The content of the incoming email.
            - `original_email_subject` (str): The subject of the incoming email.
            - `sender_email` (str): The email address of the original sender.
            - `identified_intent` (str): The main purpose of the email as understood by the agent (e.g., "maintenance_request", "rent_inquiry", "access_issue").
            - `context_data` (Optional[dict]): A dictionary containing contextual information for drafting the reply. Expected structure: `{"property_details": List[dict] | None, "chat_id": str}`. `property_details` is the result from `get_property_tenant_details`.
            - `proposed_actions` (Optional\[list\[str]]): A list of actions the AI has decided to take or has taken (e.g., "Maintenance ticket for 'broken toilet' has been created.").
            - `tone` (Optional\[str]): Desired tone of the reply (e.g., "empathetic", "formal").
        - **Returns**: A dictionary with `subject` and `body` for the reply email.

    3. **`async def create_maintenance_ticket(property_id: int, tenant_email: str, issue_description: str, urgency: str = "medium") -> dict`**
        - **Purpose**: Creates a structured maintenance ticket for issues reported by tenants (e.g., "fix the toilet"). As per requirements, JSON output is sufficient.
        - **Motivation/Reasoning**: This tool fulfills part of Requirement #3c ("Create Action Items"). Many tenant emails will involve requests for repairs or reporting issues (like the "rent" email example with the broken toilet). This tool allows the AI to translate such a request into a structured action item (a maintenance ticket), which can then be logged or passed to a maintenance system/personnel.
        - **Parameters**:
            - `property_id` (int): The ID of the property where the issue is located.
            - `tenant_email` (str): The email of the tenant reporting the issue (used for identification and contact).
            - `issue_description` (str): A clear description of the maintenance problem.
            - `urgency` (Optional\[str]): The urgency level (e.g., "low", "medium", "high").
        - **Returns**: A dictionary confirming the ticket creation, including a `ticket_id` (can be a simple unique ID for PoC), `status` (e.g., "open"), and the details provided.

    4. **`async def schedule_manager_task(task_type: str, description: str, tenant_email: Optional[str] = None, property_id: Optional[int] = None, due_date_time_iso: Optional[str] = None, manager_email: Optional[str] = None) -> dict`**
        - **Purpose**: Creates a task for a human property manager, such as calling a tenant back, reviewing a specific situation, or forwarding an email that requires direct human attention.
        - **Motivation/Reasoning**: This is another key aspect of Requirement #3c ("Create Action Items") and aligns with the high-level approach that if the AI cannot fully resolve an issue, it should escalate or forward it to a human. Example emails like "help! I locked myself out" or "call me back please" often require direct human intervention. This tool allows the AI to create a task for the property manager, ensuring these requests are not dropped and are acted upon.
        - **Parameters**:
            - `task_type` (str): Type of task (e.g., "callback_request", "information_forward", "urgent_review").
            - `description` (str): Detailed description of the task (e.g., "Tenant locked out, needs access assistance." or "Call Wilkin Dan at 2000 Holland Av Apt 1F regarding rent and toilet.").
            - `tenant_email` (Optional\[str]): Email of the tenant related to the task.
            - `property_id` (Optional\[int]): Property ID related to the task.
            - `due_date_time_iso` (Optional\[str]): Suggested due date/time in ISO format (e.g., "2024-07-28T16:00:00Z" for "tomorrow 4pm").
            - `manager_email` (Optional\[str]): Specific manager to assign; if None, could default to `stakeholder_email` from property data.
        - **Returns**: A dictionary confirming task creation, including a `task_id` and `status`.

    5. **`async def send_email(to_address: str, subject:str, body: str, cc_addresses: Optional[list[str]] = None, bcc_addresses: Optional[list[str]] = None) -> dict`**:
        - **Purpose**: Sends an email using the configured SMTP service (e.g., `aiosmtplib`). This tool would be called after a reply is drafted or if a direct email needs to be sent based on agent logic.
        - **Motivation/Reasoning**: This tool is necessary to satisfy Requirement #3d ("Send Email"). After a reply is drafted by `draft_ai_reply` or if the AI needs to send a notification (e.g., confirming a maintenance ticket or a scheduled task), this tool provides the mechanism to actually dispatch the email to the tenant or other stakeholders.
        - **Parameters**:
            - `to_address` (str): Primary recipient's email address.
            - `subject` (str): Subject line of the email.
            - `body` (str): Plain-text body of the email.
            - `cc_addresses` (Optional\[list\[str]]): List of CC recipients.
            - `bcc_addresses` (Optional\[list\[str]]): List of BCC recipients.
        - **Returns**: A dictionary with `status` ("sent" or "failed") and `message_id` if successful.

## Implementation Steps (Focus: Rapid Prototype ~4-6 hours)

### 1. Environment & Configuration (0.5 - 1 hour)

    *   Set up project directory, virtual environment (`venv`).
    *   Install initial dependencies (e.g., `google-generativeai`, `langchain`, `python-dotenv`, `pydantic`, `aioimaplib`, `aiosmtplib`).
    *   Create `.env` file for credentials (IMAP, SMTP, LLM API key).
    *   Define Pydantic models for configuration.

### 2. Async Email Connectivity (1 - 1.5 hours)

    *   Implement async IMAP connection using `aioimaplib` to monitor for new emails.
    *   Parse basic email details (From, Subject, Body) using the `email` library.
    *   Implement async SMTP functionality using `aiosmtplib` to send emails.
    *   Async function to mark emails as read.
    *   Set up async event loop and worker pool.

### 3. AI Agent & Async Tools (1.5 - 2.5 hours)

    *   Set up connection to the chosen LLM (e.g., Gemini).
    *   Design a core prompt for the AI agent to triage emails and decide on actions.
    *   Define 1-2 simple async tools using LangChain or native LLM function calling (e.g., `draft_reply_tool`, `summarize_email_tool`).
    *   Implement the logic for the agent to process an email and invoke a tool.
    *   The `draft_reply_tool` would use the LLM to generate a response draft.

### 4. Async Daemon Loop & Logging (0.5 - 1 hour)

    *   Create an async main loop for the daemon that:
        *   Asynchronously monitors for new emails.
        *   Processes them through the AI agent.
        *   Handles basic error logging.
    *   (Optional) Basic SQLite integration to track processed email IDs.
    *   Implement graceful shutdown handling for async operations.

## Key Features (Simplified for PoC)

### Email Processing

- Triage of unread emails.
- AI-driven intent understanding and information extraction.
- Marking emails as read/processed.

### Response Generation

- AI-generated draft responses based on email content.
- Ability to send generated responses.

### Action Triggering

- Agent invoking simple, predefined Python functions (tools) based on email analysis.

## Security Considerations (for PoC)

- Securely manage API keys and email credentials using `.env` and `python-dotenv`.
- Be mindful of any sensitive data processed from emails, even in a test environment.

## Testing Strategy (for PoC)

- Manual testing of the end-to-end email processing flow.
- (Optional, if time allows) Basic unit tests for critical functions like email parsing or tool execution.

## Deployment Considerations (for PoC)

- Run as a local Python script/daemon.
- Ensure necessary environment variables are set.

## Future Enhancements

(These can be listed as potential next steps beyond the PoC)

1. Advanced analytics dashboard.
2. Machine learning for response improvement.
3. Integration with additional property management systems.
4. More sophisticated workflow engine and toolset.
5. Robust error handling and retry mechanisms.
6. Handling attachments more comprehensively.

## Success Metrics (for PoC)

1. Successfully monitors and parses unread emails asynchronously.
2. AI agent correctly understands basic intents for a few sample emails.
3. AI agent successfully invokes at least one async tool (e.g., generates a draft reply).
4. Async daemon runs continuously and processes new emails as they arrive.
5. Demonstrates non-blocking behavior when handling multiple emails simultaneously.

This revised plan aims for a manageable scope for your test assignment, focusing on demonstrating the core AI-assisted email processing loop.
