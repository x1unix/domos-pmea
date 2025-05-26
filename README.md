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
* As a good point - autocomplete works perfectly and this is a real time saver.

### Downsides

When dealing with a new domain (for me it was IMAP), I found that AI is often halucinating, giving a code that doesn't work.
I had to manually debug a program to figure out how to properly implement a logic, using AI only for a concrete questions.
Usually in that cases I just resort to checking examples by searching existing codebases in GitHub (they have a good search engine).

## Implementation Trade-offs

Here is a list of things which I could do if I had more time:

* **LLM:**
  * Use embedding models to cache prompts.
  * Support attachments (pdf, jpg)
* **Mail processing:**
  * Dead letter queue to process unhandled messages is not implemented.
  * Parallel mail downloads are not supported.
  * IDLE loop server push occurs after 1 minute for some reason.
* **Chats:**
  * Move email-to-ai handling into separate worker processes which can be scaled on demand.
    * Ideally those processes could be k8s pods/containers which can be autoscaled on demand.
  * Use queues for emails to avoid loosing unprocessed mails.
* **Misc:**
  * Tests!
  * Graceful shutdown.
  * Use dotenv and env vars for config instead of YAML.
    * Debugging which keys pydantic is actually reading takes a lot of time.
