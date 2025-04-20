
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


# Configure to work with Trello


Here is example to configure GTD to work with Trello:

In your `~/.config/gtd.json` add this:

```json
{
        "trello_apikey": "your trello api key",
        "trello_token": "your trello token",
        "plugins": [
                "gtd.trello"
        ],
        "trello_board": "Backlog"
}

```

GTD can extract tasks you planned to do this week, so you just need to attach label on them in Trello. Default label name is `This week` but you can change it using `trello_this_week_label` configuration parameter:

```json
{
        "trello_apikey": "your trello api key",
        "trello_token": "your trello token",
        "plugins": [
                "gtd.trello"
        ],
        "trello_board": "Backlog",
        "trello_this_week_label": "Planned this week"
}

```

You can test generation by trying to list your projects:

    gtd projects 

It should show you lists in your board. We treat every list as a project and cards inside the list are tasks (tickets). 

Every task can have subtasks in terms of check items or acceptance criteria. These are simple checklists in trello per task.

# Configuration reference

| param                           | type   | default                                                                                                                                                                                                                                                                      | doc                                                       |
|:--------------------------------|:-------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------|
| maintenance_file                | str    |                                                                                                                                                                                                                                                                              | Path to the maintenance file                              |
| maintenance_sheet               | str    | maintenance                                                                                                                                                                                                                                                                  | Sheet name in the maintenance file                        |
| last_maintenance_column         | str    | Last maintenance                                                                                                                                                                                                                                                             | Column name for last maintenance                          |
| frequency_column                | str    | Frequency (days)                                                                                                                                                                                                                                                             | Column name for frequency                                 |
| item_column                     | str    | Item                                                                                                                                                                                                                                                                         | Column name for item                                      |
| operation_column                | str    | Operation                                                                                                                                                                                                                                                                    | Column name for operation                                 |
| meals                           | str    |                                                                                                                                                                                                                                                                              | Path to meals file                                        |
| jira_url                        | str    |                                                                                                                                                                                                                                                                              | URL of Jira instance                                      |
| jira_graphql_url                | str    |                                                                                                                                                                                                                                                                              | URL of Jira GraphQL endpoint                              |
| jira_username                   | str    |                                                                                                                                                                                                                                                                              | Username of jira user                                     |
| jira_password                   | str    |                                                                                                                                                                                                                                                                              | Password of jira user                                     |
| notes_path                      | str    | /data/Development/notes/                                                                                                                                                                                                                                                     | Path to notes directory                                   |
| trello_this_week_label          | str    | This week                                                                                                                                                                                                                                                                    | Label Used in tasks in Trello to mark tasks for this week |
| trello_board                    | str    |                                                                                                                                                                                                                                                                              | Trello board name                                         |
| trello_apikey                   | str    |                                                                                                                                                                                                                                                                              | Trello API key                                            |
| trello_token                    | str    |                                                                                                                                                                                                                                                                              | Trello token                                              |
| show_context_distribution       | bool   | False                                                                                                                                                                                                                                                                        | Show context distribution                                 |
| show_context_distribution_table | bool   | False                                                                                                                                                                                                                                                                        | Show context distribution table                           |
| scripts                         | list   | []                                                                                                                                                                                                                                                                           | List of scripts to run for report                         |
| plugin_search_path              | list   | ["'/usr/local/share/' + PROJECT_NAME + '/plugins'", "'/usr/share/' + PROJECT_NAME + '/plugins'", "os.path.join(os.path.expanduser('~'), '.' + PROJECT_NAME, 'plugins')", "os.path.join(os.path.expanduser('~'), '.local', 'share', PROJECT_NAME, 'plugins')", 'os.getcwd()'] | List of plugin search paths                               |
| disabled_plugins                | list   | []                                                                                                                                                                                                                                                                           | List of plugins to disable                                |
| plugins                         | list   | []                                                                                                                                                                                                                                                                           | List of plugins to load                                   |
