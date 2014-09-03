# Environment Variables

Jeev can be configured with a python file, or directly from environment variables. This document lists all of the 
configuration options that can be set to configure Jeev.

## Jeev Core

* `JEEV_ADAPTER`: The adapter to use to connect to the chat server. 
    * Builtin options: `slack`, `console`.  
    * Default: `console`
    
* `JEEV_STORAGE`: The storage backend to use to serialize module data via `module.data`.
    * Builtin options: `shelve`, `redis`
    * Default: `shelve`
    
* `JEEV_MODULES`: A comma seperated list of modules to load.
    * Default: ``
    * Example: `facts,eightball`

## Jeev Web-Server

* `JEEV_WEB`: Should Jeev run it's built in web-server, that will allow modules to define web endpoints?
    * Default: `FALSE`
    * Possible Values: `FALSE`, `TRUE`
    
* `JEEV_WEB_LISTEN_HOST`: The host that the built in web-server will bind to.
    * **REQUIRED** if `JEEV_WEB == TRUE`.
    * Example: `0.0.0.0` (to listen on all interfaces), `127.0.0.1` (to only listen on localhost)
    
* `JEEV_WEB_LISTEN_PORT`: The port taht the built in web-server will bind to.
    * **REQUIRED** if `JEEV_WEB == TRUE`
    * Example: `8000` (note that if you are using the Slack adapter, it will default bind to port 8080).


## Adapter Options

### `jeev.adapter.console`

* `JEEV_ADAPTER_CONSOLE_CHANNEL`: The default channel that the adapter will pretend you are in.
    * Default: `console`
    
* `JEEV_ADAPTER_CONSOLE_USER`: The default user that the adapter will pretend you are.
    * Default: `user`
    
### `jeev.adapter.slack`

* `JEEV_ADAPTER_SLACK_LISTEN_HOST`: The address to bind the web-server for slack's web hook.
    * Default: `0.0.0.0` (listens on all hosts)
    
* `JEEV_ADAPTER_SLACK_LISTEN_PORT`: The port to bind the web-server for slack's web hook.
    * Default: `8080`
    
* `JEEV_ADAPTER_SLACK_TEAM_NAME`: The team-name of your slack service.
    * **REQUIRED**
    
* `JEEV_ADAPTER_SLACK_TOKEN`: The integration token for Jeev.
    * **REQUIRED**
    
* `JEEV_ADAPTER_SLACK_LINK_NAMES`: Not sure what this does yet...
    * Default: `FALSE`
    * Possible Values: `FALSE`, `TRUE`
    
## Storage Options

### `jeev.storage.shelve`

* `JEEV_STORAGE_SHELVE_DATA_PATH`: Where shelve stores it's database files. 
    * **REQUIRED**
    * Example: `./shelve`
    
### `jeev.storage.redis`

* `JEEV_STORAGE_REDIS_KEY_PREFIX`: What to prefix all the redis keys with in the database
    * Default: `` (empty string, keys won't be prefixed)

* `JEEV_STORAGE_REDIS_URL`: The redis URL to connect to
    * Default: `redis://127.0.0.1:6379/0`

If you don't want to use a URL, you can set the connection kwargs for the `StrictRedis` connection by using 
`JEEV_STORAGE_REDIS_{KEY}`, where `{KEY}` is one of: `HOST`, `PORT`, `DB`, `PASSWORD`, `SOCKET_TIMEOUT`, 
`SOCKET_CONNECT_TIMEOUT`, `SOCKET_KEEPALIVE`, `SOCKET_KEEPALIVE_OPTIONS`, `CONNECTION_POOL`, `UNIX_SOCKET_PATH`, 
`ENCODING`, `ENCODING_ERRORS`, `ERRORS`, `DECODE_RESPONSES`, `RETRY_ON_TIMEOUT`, `SSL`, `SSL_KEYFILE`, `SSL_CERTFILE`, 
`SSL_CERT_REQS`, `SSL_CA_CERTS`. See https://github.com/andymccurdy/redis-py for more details.