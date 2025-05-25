# Property Manager Email Assistant - Test Assignment

## Design

### IMAP

Initially I planned to make mail downloads also parallel and just queue mails to download (UIDs).
Unfortunately doing this with a single IMAP connection which is also used for IDLE loop causes SSL connection errors and breaks a whole process.

I had to pick between 2 options:

1. Make downloads parallel but each client supplied with a separate IMAP connection or implement connection pool.
2. Sequential messages download. Process messages separately.

I picked the second option due to simplicity and I believe download process isn't the biggest bottleneck. \
Downloaded messages are still handled in separate workers.

## AI Notes

### Downsides

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

- **LLM:**
    - Use embedding models to cache prompts.
    - Support attachments (pdf, jpg)
- **Mail processing:**
    - Current design has a fatal flaw: it just stores last successfully processed msg UID.
    - Instead: it should also have a dead-letter queue of unprocessed UIDs.
- **Chats:**
    - Maintain a whole conversation per topic. Possible solutions:
        - Persist in DB (Redis or other) + TTL.
        - Just follow quoted replies in a mail itself.
    - Identify each topic by adding conversation ID. Possible solitions:
        - Custom header isn't an option as it will be lost when client replies to agent.
        - Plus tag in reply email is easiest solution. E.g `agent+[chat_id]@gmail.com`
    - Move email handling into separate worker processes which can be scaled on demand.
        - Ideally those processes could be k8s pods/containers which can be autoscaled on demand.
    - Use queues for emails to avoid loosing unprocessed mails.
- **Misc:**
    - Tests!
    - Graceful shutdown.
    - Use dotenv and env vars for config instead of YAML.
        - Debugging which keys pydantic is actually reading takes a lot of time.

