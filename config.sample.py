adapter = 'console'
adapter_opts = {
    'consoleChannel': 'test',
    'consoleUser': 'user',
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
    'listenHost': 'localhost',
    'listenPort': 8080
}

module_data_path = './shelve'