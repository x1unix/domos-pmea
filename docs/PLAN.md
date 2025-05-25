# Property Manager Email Assistant - Implementation Plan

This document is partially created both by AI and me.

## Project Overview

The Property Manager Email Assistant is a Python-based **daemon service** that automates email communication for property management systems. The service monitors an email inbox, processes incoming messages using an AI agent, generates appropriate responses, and triggers relevant actions based on the email content and agent decisions. This plan focuses on a simplified version suitable for a rapid prototype.

## High-level approach

### RAG

RAG receives a message from client via email.

RAG can request additional information for context using tool calls and/or ask additional information from user.

If user requests some action (call me, etc.) - RAG should create and forward mail to property manager.

### Mail Thread History

Per research, the most standard way to track mail thread is to rely on following headers:

| Header          | What it contains                                                | How to use it                                                                  |
| --------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Message-ID**  | A globally-unique identifier for *this* message.                | Always store it; it is the primary key.                                        |
| **In-Reply-To** | The single Message-ID this note is replying to.                 | First place to look when you want to connect the dots.                         |
| **References**  | An ordered list of *all* ancestor Message-IDs, oldest → newest. | If *In-Reply-To* is absent or you want the root of the thread, scan this list. |

Redis is used to store message IDs and map them to a thread ID:

```redis
SET   msg:{Message-ID}   {thread_id}      # forward map (1 key per message)
SADD  thread:{thread_id} {Message-ID}     # reverse map (1 set per thread)
```

Same thread ID is used for LLM conversations.

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

### `async def find_properties_by_criteria(address: Optional[str] = None, tenant_name: Optional[str] = None, tenant_email: Optional[str] = None) -> List[dict]`

- **Description**: Searches for and retrieves detailed information about properties and their tenants from a data source (e.g., `data/properties_db.json`) based on criteria like address, tenant name, or tenant email. This tool is essential for Requirement #3a ("Load relevant information") when specific identifiers like a property ID are not initially known. It allows the AI to look up properties based on details often found in emails (e.g., tenant mentioning their street or name). This context is vital for personalizing responses and routing issues. It supports handling example emails like "rent", "Lease terms".
- **Parameters**:

    | Name           | Type  | Optional | Default | Description                                  |
    |----------------|-------|----------|---------|----------------------------------------------|
    | `address`      | `str` | Yes      | `None`  | Full or partial address of the property.     |
    | `tenant_name`  | `str` | Yes      | `None`  | Name of the tenant.                          |
    | `tenant_email` | `str` | Yes      | `None`  | Email address of the tenant.                 |

    *Note: At least one parameter (`address`, `tenant_name`, or `tenant_email`) should be provided for lookup.*
- **Returns**:
  - **Type**: `List[dict]`
  - **Description**: A list of dictionaries. Returns an empty list (`[]`) if no matching properties are found. Each dictionary in the list will have the following structure, mirroring `data/properties_db.json`:
    - `property_id`: `int`
    - `building_number`: `str`
    - `street_name`: `str`
    - `city`: `str`
    - `unit`: `str`
    - `tenant`: `dict` (object with `name: str`, `email: str`, `phone: str`)
    - `stakeholder_email`: `str`
    - `monthly_rent_usd_cents`: `int`

### `async def get_property_by_id(property_id: int) -> Optional[dict]`

- **Description**: Retrieves detailed information for a specific property using its unique `property_id`. Provides a direct and efficient way to fetch property details when the unique identifier is already known (e.g., from a previous search or if a user explicitly provides it). This avoids redundant searching and ensures precise data retrieval for subsequent actions.
- **Parameters**:

    | Name          | Type  | Optional | Default | Description                          |
    |---------------|-------|----------|---------|--------------------------------------|
    | `property_id` | `int` | No       | N/A     | The unique identifier for the property. |

- **Returns**:
  - **Type**: `Optional[dict]`
  - **Description**: A single dictionary closely matching the structure in `data/properties_db.json` if found (see structure under `find_properties_by_criteria` returns), otherwise `None`.

### `async def draft_ai_reply(original_email_body: str, original_email_subject: str, sender_email: str, identified_intent: str, context_data: Optional[dict] = None, proposed_actions: Optional[list[str]] = None, tone: str = "professional and helpful") -> dict`

- **Description**: Generates a context-aware, ready-to-send plain-text email reply using an LLM. This tool directly addresses Requirement #3b ("Generate a Draft Reply"), allowing the AI agent to use the original email's content, its identified intent, and fetched contextual data (from `find_properties_by_criteria` or `get_property_by_id`) to generate a relevant reply.
- **Parameters**:

    | Name                     | Type                  | Optional | Default                        | Description                                                                                                                                                              |
    |--------------------------|-----------------------|----------|--------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | `original_email_body`    | `str`                 | No       | N/A                            | The content of the incoming email.                                                                                                                                       |
    | `original_email_subject` | `str`                 | No       | N/A                            | The subject of the incoming email.                                                                                                                                       |
    | `sender_email`           | `str`                 | No       | N/A                            | The email address of the original sender.                                                                                                                                |
    | `identified_intent`      | `str`                 | No       | N/A                            | The main purpose of the email as understood by the agent (e.g., "maintenance_request", "rent_inquiry", "access_issue").                                               |
    | `context_data`           | `dict`                | Yes      | `None`                         | Contextual information. Expected structure: `{"property_details": Union[List[dict], dict, None], "chat_id": str}`. `property_details` comes from property lookup tools. |
    | `proposed_actions`       | `Optional[List[str]]` | Yes      | `None`                         | List of actions the AI has decided to take/has taken (e.g., "Maintenance ticket created.").                                                                           |
    | `tone`                   | `str`                 | Yes      | `"professional and helpful"` | Desired tone of the reply (e.g., "empathetic", "formal").                                                                                                             |

- **Returns**:
  - **Type**: `dict`
  - **Description**: A dictionary with `subject: str` and `body: str` for the reply email.

### `async def create_maintenance_ticket(property_id: int, tenant_email: str, issue_description: str, urgency: str = "medium") -> dict`

- **Description**: Creates a structured maintenance ticket for issues reported by tenants (e.g., "fix the toilet"). This fulfills part of Requirement #3c ("Create Action Items"), translating email requests into structured action items for logging or passing to maintenance personnel.
- **Parameters**:

    | Name                | Type  | Optional | Default    | Description                                                                 |
    |---------------------|-------|----------|------------|-----------------------------------------------------------------------------|
    | `property_id`       | `int` | No       | N/A        | The ID of the property where the issue is located.                          |
    | `tenant_email`      | `str` | No       | N/A        | The email of the tenant reporting the issue (for identification/contact). |
    | `issue_description` | `str` | No       | N/A        | A clear description of the maintenance problem.                             |
    | `urgency`           | `str` | Yes      | `"medium"` | The urgency level (e.g., "low", "medium", "high").                          |

- **Returns**:
  - **Type**: `dict`
  - **Description**: A dictionary confirming ticket creation, e.g., `{"ticket_id": "some_uuid", "status": "open", "details": {...}}`.

### `async def schedule_manager_task(task_type: str, description: str, tenant_email: Optional[str] = None, property_id: Optional[int] = None, due_date_time_iso: Optional[str] = None, manager_email: Optional[str] = None) -> dict`

- **Description**: Creates a task for a human property manager (e.g., callback, review, forward email). Addresses Requirement #3c ("Create Action Items") for issues requiring human intervention (e.g., "locked out", "call me back"), ensuring requests are actioned.
- **Parameters**:

    | Name                | Type            | Optional | Default | Description                                                                                                |
    |---------------------|-----------------|----------|---------|------------------------------------------------------------------------------------------------------------|
    | `task_type`         | `str`           | No       | N/A     | Type of task (e.g., "callback_request", "information_forward", "urgent_review").                         |
    | `description`       | `str`           | No       | N/A     | Detailed description of the task.                                                                          |
    | `tenant_email`      | `Optional[str]` | Yes      | `None`  | Email of the tenant related to the task.                                                                   |
    | `property_id`       | `Optional[int]` | Yes      | `None`  | Property ID related to the task.                                                                           |
    | `due_date_time_iso` | `Optional[str]` | Yes      | `None`  | Suggested due date/time in ISO format (e.g., "2024-07-28T16:00:00Z").                                      |
    | `manager_email`     | `Optional[str]` | Yes      | `None`  | Specific manager to assign; if None, could default to `stakeholder_email` from property data.          |

- **Returns**:
  - **Type**: `dict`
  - **Description**: A dictionary confirming task creation, e.g., `{"task_id": "some_uuid", "status": "pending"}`.

### `async def send_email(to_address: str, subject:str, body: str, cc_addresses: Optional[list[str]] = None, bcc_addresses: Optional[list[str]] = None) -> dict`

- **Description**: Sends an email using the configured SMTP service. This tool is necessary to satisfy Requirement #3d ("Send Email") after a reply is drafted or if the AI needs to send a notification.
- **Parameters**:

    | Name            | Type                  | Optional | Default | Description                               |
    |-----------------|-----------------------|----------|---------|-------------------------------------------|
    | `to_address`    | `str`                 | No       | N/A     | Primary recipient's email address.        |
    | `subject`       | `str`                 | No       | N/A     | Subject line of the email.                |
    | `body`          | `str`                 | No       | N/A     | Plain-text body of the email.             |
    | `cc_addresses`  | `Optional[List[str]]` | Yes      | `None`  | List of CC recipients.                    |
    | `bcc_addresses` | `Optional[List[str]]` | Yes      | `None`  | List of BCC recipients.                   |

- **Returns**:
  - **Type**: `dict`
  - **Description**: A dictionary with `status: str` ("sent" or "failed") and `message_id: Optional[str]` if successful.

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
