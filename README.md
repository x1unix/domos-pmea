# Property Manager Email Assistant - Test Assignment

## How To Run

Please see [this setup guide](docs/SETUP_GUIDE.md).

## Design

### Project Structure

```
src/
└── pmea/
    ├── app/                  # Application bootstrap
    ├── agent/                # AI Agent Messages Processor
    │   └── tools/            # Tools callable by agent
    ├── config/               # Configuration logic & types
    ├── mailer/               # Email consuming and publishing (IMAP/SMTP)
    ├── models/               # Shared data types and classes
    ├── repository/           # Data access layer
    └── main.py               # Main executable
```

#### Stack

* uv - Python and package manager.
* Redis - Chat history and mail processing state storage.
* LangChain - wrapper around different AI model/platform providers.
* Supported AI providers:
  * Google (Gemini)
  * Ollama

### Assumptions

* All tenants live in US and speak only English.
* All apartments located in a single city.
* User won't try to spam, flood or abuse context size of agent.
* Agent speak only with 1 person in each Email thread.

### Inbox Mail Processing

At startup, server checks for missed messages by tracking `uid` and waits for new events using IDLE loop.\
This logic is implemented in `pmea.mailer.mail_listener` package.

> [!NOTE]
> Although missed messages check wasn't in requirements list, I implemented it for debugging convenience as server push delay is about 2-3 minutes.
> Rolling back conversation until a certain point and replaying conversation was much faster process.

> [!NOTE]
> This solution doesn't have a dead letter queue to save time.
> Also message queue is implemented in memory using asyncio queues.

Messages are downloaded in batches and then queued for processing. Batch size is configurable.

Then, messages are routed to `pmea.mailer.thread_listener` which assembles incoming messages into \
a thread - the same way as any mail client does.

This is done by tracking `References`, `In-Reply-To` and `Message-ID` headers.\
Message to thread mapping (and vice-versa) is stored in Redis.

Each thread has an assigned UUIDv4 which is also later used for AI session ID to load conversation context.

### AI Agent Stage

After message was categorized, it's routed to `pmea.agent.consumer` which:

* prepares tool call handlers.
* provides chat history based on mail thread ID.
* sets up and runs chain.

See system prompt [here](src/pmea/agent/prompts.py).

#### Supported Models & Platforms

Agent primerally optimized to run with Google's Gemini but also supports Ollama for testing purposes.

Model reasoning should be **disabled** as I don't filter `<think>` thougts out of output.

See *Implementation Trade-offs* for context.

#### Caching

See *Implementation Trade-offs* for context.

#### Tools Calls

In order to interact with the system, agent has access to a set of tools:

* `find_properties`
  * Provides agent ability to locate tenant's property info, contract information and landlord email.
  * Supports partial non-strict search so agent can try to guess or request extra information if necessary.
* `create_ticket`
  * Create a ticket if necessary, as per requirements.
  * Information from `find_properties` is necessary to fill a ticket.
* `forward_to_stakeholder`
  * If agent is not capable to help, forwards tenant's mail to landlord with additional context (property info).

> [!NOTE]
> I didn't test how system will behave when multiple people are communicating within the same thread.
> Although each prompt contains sender email and name - Agent has one instance of chat memory per thread.

#### Chat Context Memory

For sake of simplicity, Redis is used to store chat context using LangChain's `RedisChatMessageHistory`.\
Chat history TTL is not set.

Redis was chosen as it's already used to track message to thread relation.

#### Error handling

In case of any unexpected exception from AI side (Ollama server died, etc):

* Tenant gets a templated mail that system isn't able to handle his request.
* Tenant's mail is forwarded to property manager (if possible).

## Implementation Trade-offs

Here is a list of trade-offs and things which I could do if I had more time.

* **Database:**
  * Property data is mocked and stored as a JSON file for sake of simplicity.
  * This can be moved into an actual database - sqlite is fine for local instances.
* **LLM:**
  * **LLM - Tools:**
    * `create_ticket`:
      * Use a dedicated response template instead of relying on AI response.
      * Ability to track status of created ticket.
    * `forward_to_stakeholder`:
      * It might make sense to reply back to user with `Reply-To` header with landlord's address.
      * Decouple forwared message formatting from sending.
  * **Optimization:**
    * Introduce stable multi-user support in conversation.
      * Currently agent is already supplied with sender name and address but it doesn't have separate roles.
    * Use embedding models to cache prompts.
    * Support attachments (pdf, jpg)
    * Chat history size management (or at-least a ring buffer).
    * Ability to export conversations into some form of audit log to track quality.
  * **Misc**
    * Tool call arguments validation using schema.
    * Support *reasoning models* and filter out `<think>...</think>` and other artifacts.
      * I tried to circumvent this by asking model to use a special `reply_to_user` tool but couldn't get reliable results.
      * Some models like `qwen3` still made output to chat instead of using the tool.
* **Mail processing:**
  * **IDLE loop server push on GMail occurs with 2-3 minute delay for some reason.**
  * Email clients in threads include reply quotes which need to be removed before processing because:
    * Bloat AI context with unecessary data.
    * Can impact on result and confuse LLM.
    * I tried to solve this myself but even [mail-parser-reply](https://github.com/alfonsrv/mail-parser-reply) doesn't handle Gmail cases well, especially if thread was done between different mail agents.
  * Missing Dead letter queue to process unhandled incoming & outgoing messages.
  * Use queues like *Redis, Kafka, etc* for emails to avoid loosing unprocessed mails.
  * Outgoing messages are sent immediately. Ideally should be moved into a separate queue for background process.
  * Parallel mail downloads are not supported.
* **Chats:**
  * Move email-to-ai handling into separate worker processes which can be scaled on demand.
    * Ideally those processes could be k8s pods/containers which can be autoscaled on demand.
* **Config:**
  * Migrate to pydantic v2. Atm it throws deprecation warnings as `@validator` is deprecated and aliased to v2 method.
  * Use dotenv and env vars for config instead of YAML.
    * Debugging which keys pydantic is actually reading takes a lot of time.
* **General:**
  * Scalability & observability & metrics.
  * E2E & Unit tests.
  * Use connection pool for Redis.
  * Graceful shutdown.

## Appendix - AI Notes

I used both Cursor and mix of Claude & ChatGPT:

* Cursor for code generation and autocompletion.
* ChatGPT o3 model for IMAP protocol and LangChain research where possible.
  * I also tried Gemini Pro reasoning model inside Cursor but it performed poorly.

### Bootstrapping

Gemini Pro in Cursor chat was a good tool to boostrap a project - select stack, explore options.

I used it to make a very brief, approximate action plan (see [docs/PLAN.md](docs/PLAN.md)).\
Referenced plan can be used as a "memory" for further chats.

Although it was useful during bootstapping stage, I had to focus on building stuff and didn't have \
enough time to sync what I did with `PLAN.md`.

Right now, some parts of the document diverges from actual implementation but I still keep it for \
historical records.

### Cursor Wibe-Coding experience

Cursor was used to make this assignment. I tried mixing different models (Claude, Gemma, GPT) but sometimes experience look like [on this video](https://youtu.be/_2C2CNmK7dQ?si=AYklZ_-MXaGsohtM).

* Sometimes Cursor could bork half of a codebase because it decided to refactor and break project config. Blind vibe coding is dangerous.

### General Feelings

#### Upsides

* gpt-4.1 proven to be the safest code-generation model choice (only template code).
* Python autocompletion is very convenient except cases where it misses the point and starts introducing bugs.

#### Downsides

When dealing with a new domain (for me it was IMAP), I found that AI is often halucinating, giving solutions that doesn't work. \
This even happens with o1 reasoning model, but not so often as with regular models.

Couple of cases:

* LangChain is frequently updated, introducing breaking changes, making suggested solutions obsolete.
* Claude, Gemini and GPT struggled with ICMP:

I had to manually debug a program to figure out how to properly implement a logic, using AI only for a concrete questions.

Usually in that cases I just resort to checking examples by searching existing codebases in GitHub (they have a good search engine).

In addition to that, during development I faced some issues which AI can't address or investigate. As example:

* <https://github.com/langchain-ai/langchain-redis/issues/67>
