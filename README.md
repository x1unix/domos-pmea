# Property Manager Email Assistant - Test Assignment

## Design

### IMAP

At startup, server checks for missed messages and waits for new one using IDLE loop.

Messages are downloaded in batches and then queued for processing. Batch size is configurable.

Also application is capable of mapping emails into threads using `References` and `Message-ID` headers. This is used to map AI chats to mail threads.

For simplicity: dead letter queue is not implemented.

## AI Notes

Cursor was used to make this assignment. I tried mixing different models (Claude, Gemma, GPT) but sometimes experience look like [on this video](https://youtu.be/_2C2CNmK7dQ?si=AYklZ_-MXaGsohtM).

* Sometimes Cursor could bork half of a codebase because it decided to refactor and break project config. Blind vibe coding is dangerous.

### Upsides

* gpt-4.1 proven to be the most safe model to use.
* Autocompletion is very convenient except cases where it misses the point.

### Downsides

When dealing with a new domain (for me it was IMAP), I found that AI is often halucinating, giving a code that doesn't work.
I had to manually debug a program to figure out how to properly implement a logic, using AI only for a concrete questions.
Usually in that cases I just resort to checking examples by searching existing codebases in GitHub (they have a good search engine).

In addition to that, during development I faced some issues which AI can't address or investigate. As example:

* https://github.com/langchain-ai/langchain-redis/issues/67

## Implementation Trade-offs

Here is a list of things which I could do if I had more time:

* **LLM:**
  * Reroute message to stakeholder on error during message processing by AI.
  * Use embedding models to cache prompts.
  * Support attachments (pdf, jpg)
  * Stuff like `ConversationBufferMemory` are deprecated. Migrate to LangGraph.
* **Mail processing:**
  * Dead letter queue to process unhandled incoming & outgoing messages is not implemented.
  * Outgoing messages are sent immediately. Ideally should be moved into a separate queue.
  * Parallel mail downloads are not supported.
  * IDLE loop server push on GMail occurs with 1-2 minute delay for some reason.
* **Chats:**
  * Move email-to-ai handling into separate worker processes which can be scaled on demand.
    * Ideally those processes could be k8s pods/containers which can be autoscaled on demand.
  * Use queues for emails to avoid loosing unprocessed mails.
* **Config:**
  * Migrate to pydantic v2. Atm it throws deprecation warnings as `@validator` is deprecated and aliased to v2 method.
  * Use dotenv and env vars for config instead of YAML.
    * Debugging which keys pydantic is actually reading takes a lot of time.
* **General:**
  * E2E & Unit tests.
  * Use connection pool for Redis.
  * Graceful shutdown.
