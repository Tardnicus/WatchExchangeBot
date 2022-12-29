# /r/Watchexchange Bot

Monitors `/r/Watchexchange` for certain criteria and posts to a Discord webhook when found.

# Running

The program is designed to run "indefinitely". At a certain point, PRAW's "stream" function may encounter an error and the program will crash. No crash recovery is built-in, so [using Docker Compose](#docker-compose) is recommended.

## Bare Metal

### Install Requirements

ℹ️A virtual environment is recommended for running on bare metal.

```shell
cd /wemb/src
python -m pip install -r requirements.txt
```

### Running

```shell
python main.py
```

The program will run indefinitely (or until an error happens, see above). To quit prematurely, press Ctrl+C.

## Docker Compose

A valid [docker-compose.yaml file has been provided](./docker-compose.yaml):

```yaml
version: '3.9'
services:
  wemb-core:
    build: './wemb'
    restart: unless-stopped
    environment:
      - praw_client_id=${PRAW_CLIENT_ID}
      - praw_client_secret=${PRAW_CLIENT_SECRET}
      - praw_user_agent=${PRAW_USER_AGENT}
      - WEMB_LOGLEVEL=DEBUG
    volumes:
      - './wemb/src/config.yaml:/app/config.yaml:ro'
```

Note: This compose file uses an .env file to get the client id, secret, and user agent.

See the below sections on configuration for how to properly provide authentication, etc.

# Configuration

There are two major configuration files / info that are required for this application to run.

## PRAW Authentication

PRAW authentication can be provided in two ways: a praw.ini file, and through environment variables.

### Prerequisites

Firstly, you need to provide some authentication for the Reddit API to function. This can be done by going to <https://www.reddit.com/prefs/apps> and creating an app. ([more information here](https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#read-only-reddit-instances))

Since we only need read-only access to the API, we don't need much. Pick "script", give it a description and name. We need to copy two things:

1. The client ID found under the bolded subheader of "personal use script" near the top of the box.
2. The client secret, titled as "secret".

Both of these, along with a user agent, will be used to authenticate with the Reddit API.

### Environment Variables

PRAW also takes configuration via environment variables. [As described by PRAW's docs](https://praw.readthedocs.io/en/stable/getting_started/configuration/environment_variables.html), the necessary/relevant environment variables are:

- `praw_client_id`
- `praw_client_secret`
- `praw_user_agent`

You amy set these manually yourself, or use the method below.

#### Docker Compose `.env` File

If you run the program using Docker Compose (recommended), copy [`.env-example`](./.env-example) as `.env`, and fill in the client ID and secret. Don't forget to replace your username in the user-agent string:

```diff
 # Authentication used for PRAW
-PRAW_CLIENT_ID=
-PRAW_CLIENT_SECRET=
-PRAW_USER_AGENT=linux:com.example.watchexchangemonitorbot:0.1.0 (by /u/username)
+PRAW_CLIENT_ID=bjarElX6axdaiVnApRAaLP
+PRAW_CLIENT_SECRET=ZvxYlKpMd1z80SxZmTxZp2rkILRC3B
+PRAW_USER_AGENT=linux:com.example.watchexchangemonitorbot:0.1.0 (by /u/youruserhere)
```

⚠️Make sure to run `docker compose` from the same location as the `.env` file.

### `praw.ini`

If you choose to use a praw.ini file, copy [`praw.ini.example`](./wemb/src/praw.ini.example) as `praw.ini`, and fill in the client ID and secret. Don't forget to replace your username in the user-agent string:

```diff
 [DEFAULT]
-client_id=
-client_secret=
-user_agent=linux:com.example.watchexchangemonitorbot:0.1.0 (by /u/username)
+client_id=bjarElX6axdaiVnApRAaLP
+client_secret=ZvxYlKpMd1z80SxZmTxZp2rkILRC3B
+user_agent=linux:com.example.watchexchangemonitorbot:0.1.0 (by /u/youruserhere)
```

⚠️Make sure `praw.ini` is in the same directory as the script.

## Application Configuration YAML

This program uses a [`config.yaml`](./wemb/src/config.yaml) to control some application configuration. Each of the major sections are summarized below:

🚨 This will likely be removed in the future!

### Note About Docker

When running in Docker Compose, a valid configuration must be mounted to the container, as one is not available as default. There is an example provided in the [`docker-compose.yaml`](docker-compose.yaml) file 

### Criteria

A top-level list of criteria that the bot will use to evaluate posts against. This is the only way to provide criteria to the bot.

Each element in the list needs four pieces of information:

1. `submissionType` - Either `"WTS"` or `"WTB"`. Filters the submission by those tags.
2. `minTransactions` - The minimum number of transactions the posting user needs to have for this to be considered. Default 5.
3. `keywords` - A LIST of keywords that need to show up in the submission for it to be considered. The behaviour of this is affected by the option below.
4. `allRequired` - If true, ALL keywords in the previous option must be present for the post to be considered. If false, only one of them needs to be.

### Webhook Information

The rest of the configuration file deals with webhook configuration. The following two pieces of information are required:

1. `webhookUrl` - The URL for the webhook to post the message to. This can be copied directly from the webhook creation screen on a channel.
2. `mentionString` - A mention string. This allows the bot to mention a specific person, or role. You MUST use IDs. Enable Developer mode in Discord settings to get the "Copy ID" button.
    - Example: `<@&320244003583033356>` is a role mention; and
    - `<@575252669443211264>` is a user mention.

## Other Environment Variables

The application also takes other environment variables as configuration. They are listed below:

| Environment Variable | Possible Values                                                                    | Description                                                                               |
|----------------------|------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `WEMB_LOGLEVEL`      | [Described in docs](https://docs.python.org/3/library/logging.html#logging-levels) | Controls the logging level. Turn up or down if you want more/less logs. Default: `DEBUG`. |
