
# GTD 

GTD tool which uses JIRA as a backend and allows you to manage your tasks in a GTD way

# Installation 

To install gtd utility run: 

```shell
python setup.py install 
```

# Configuration 


In order to get configuration parameters you can modify, execute:

    python scripts/detect_function_calls.py  gtd/ get_config_ --exclude get_config_location

Every configuration parameter can be changed in configuration file and overwritten by using environment variable. 

For instance, `url` can be specified in configuration file and can be modified using `GTD_URL` environment variable. 

Configuration file is specified using `GTD_CONFIG` and default location is at `~/.config/gtd.json`
