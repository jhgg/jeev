adapter = 'console'
adapter_opts = {
    'console_channel': 'test',
    'console_user': 'user',
}

modules = {
    'ping': {},
    'kittens': {},
    'dealwithit': {},
    'coin': {},
    'decide': {},
    'sudo': {}
}

web = True
web_opts = {
    'listen_host': 'localhost',
    'listen_port': 8080
}

storage = 'shelve'
storage_opts = {
    'shelve_data_path': './shelve'
}
