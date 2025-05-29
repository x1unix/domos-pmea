# Property Manager Email Assistant - Install Guide

## Prerequisites

* Docker + docker-compose
* [uv](https://docs.astral.sh/uv/)
* Google AI Studio [API Key](https://aistudio.google.com/apikey)
* Gmail App Password for IMAP + SMTP
  * Enable 2FA to enable App Password feature.
  * Create an app password [here](https://myaccount.google.com/apppasswords)

## Setup

### Configuring Python & venv

Install project-supported version of Python and initialize virtualenv:

```shell
uv python install
uv venv
uv pip install -e .
```

### docker-compose

Project ships a `compose.yml` file with Redis which is required to run a service:

```shell
docker-compose up -d
docker-compose start
```

### Configuration Files

Copy `config.example.yml` into `config.yml` and edit it.

Recommended AI model is `gemini-2.0-flash`.
Recommended mail service is GMail.

**Note:** To avoid Cursor stealing your API keys, it's recommended to use `GEMINI_API_KEY` environment variable instead of hardcoding Gemini API key in a config.

> [!NOTE]
> Use `--help` flag to see options for each command.

### Update Mocks

If necessary, update tenant and stakeholder contact information in [data/properties_db.json](data/properties_db.json) file.

>[!NOTE]
>For all stakeholders with email suffix `@example.com`, forwarded mails are stored as text files in `data/forwarded_mails` directory (configurable).

## Running Application

Project provides 2 modes:

* Server agent mode - listens and responds to incoming emails.
* Console chat mode - inline chat for debugging without a real email account.
  * Used to debug AI responses without delays caused by slow email delivery.

### Server Agent

```shell
uv run domos-pmea serve --config config.yml
```

### Console Chat Mode

```shell
uv run domos-pmea chat --config config.yml --email <user's email> --name <user's name> --subject <mail subject> 
```

> [!NOTE]
> Email, name and subject can also be supplied with environment variables.
> See `--help` to see supported environment variables.

