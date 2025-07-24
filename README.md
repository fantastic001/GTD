- [GTD - Gamify The Day - God That Deadline!!!](#gtd---gamify-the-day---god-that-deadline)
- [Installation](#installation)
- [Configuration](#configuration)
- [Configure to work with Trello](#configure-to-work-with-trello)
- [Creating tasks](#creating-tasks)
  - [Creating tasks with only title](#creating-tasks-with-only-title)
  - [Adding tasks with description and checklists](#adding-tasks-with-description-and-checklists)
- [Configuration reference](#configuration-reference)
- [Writing extensions for GTD](#writing-extensions-for-gtd)



# GTD - Gamify The Day - God That Deadline!!!

Okay, lets face it: your life is miserable and you are miserable. Some capitalists told you that YOU HAVE TO BE PRODUCTIVE IN ORDER TO EAT AND FUCK REGULARLY. 

Still, you are miserable and hence you have problems with eating and fucking. You can fight capitalism or you can make game out of it. NUMBERS! Baby! 

Yeah, that's right! Numbers and charts make us work more. Ok, ok, money also makes us work more but I cannot give you money because I am living off my savings right now. 

So, back to numbers. Numbers are great and we (ab)use them every day. You probably saw some politicians using numbers to influence something. You also love numbers. Whenever you go to gym, you pay attention how fat you became and how dumb your eating habits are. 

But, there is one important thing: it does not matter if we measure something for the right reason or not. What matters is process! Right? 

So, by measuring your productivity, it will make you more productive and then you can have money and eat food and fuck regularly. 

And this is the purpose of this tool. to measure your productivity and guide you in your journey to better fucking life. In the end, when you die, you would be glad that people will know how many tickets in Jira (or whatever bullshit tool) you closed.

So, here it is! Tool to measure your productivity, make task management easy, automate certain stuff with fucking AI or whatever. 

I strongly believe in fucking UNIX philosophy. If you do not know what UNIX philosophy means, that is okay. If you know what UNIX philosophy is, then you don't fuck regularly probably. 

Anyway, this tool is simple and built with KISS principle in mind. That being said, please do not come to me with some fancy requests like "I want this tool to jerk off instead of me". That won't make sense. But, what you can do is write a plugin and suggest feature in Issues page.

Right now, I wrote several plugins for myself. Keep in mind that I do not have many users to get feedback from, so be patient. 

Main idea behind this tool is to be able to generate HTML report. Report of what? Well, primarily from your tasks in Trello or Jira. There are other things you can put into report, like some script execution output or some other fancy stuff. I use it also to have my meals planned because I am too lazy to think what I want to eat for the whole week. By having that meal plan for whole week, I can get groceries on time and not to wait last minute. 

Another thing is having reminders to review your notes. This enables me to review what I have learned by giving me exercises to practice on daily basis. Somebody told you probably that repetition is key to success. Well, here you go. 

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

# Creating tasks 

## Creating tasks with only title

Just put them line-by-line into fucking file, you motherfucker

        vim my_fucking_tasks.txt 

```
fuck wife
fuck boss
fuck his wife
```

Ok, we have 3 tasks, lets add them into project `Regular fucking`

        gtd upload -i my_fucking_tasks.txt -p "Regular fucking"

That's it! Easy, huh?

## Adding tasks with description and checklists

Maybe you want to describe your tasks better and add some checklist to ensure you actually do something in proper manner. Separate tasks with empty line and add `-c` parameter:

```
task 1 
description
* checkitem 1
* checkitem 2
* checkitem 3

task 2
description
* checkitem 1
* checkitem 2
* checkitem 3
```

and now add to trello or whateveer bullshit you use:

        gtd upload -i mytasks -c -p "My project"

And you will see your fucking tasks in your fucking board. 

# Configuration reference

| param                           | type   | default                                                                                                                                                                                                                                                                      | doc                                                            |
|:--------------------------------|:-------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------|
| plugin_search_path              | list   | ["'/usr/local/share/' + PROJECT_NAME + '/plugins'", "'/usr/share/' + PROJECT_NAME + '/plugins'", "os.path.join(os.path.expanduser('~'), '.' + PROJECT_NAME, 'plugins')", "os.path.join(os.path.expanduser('~'), '.local', 'share', PROJECT_NAME, 'plugins')", 'os.getcwd()'] | List of plugin search paths                                    |
| disabled_plugins                | list   | []                                                                                                                                                                                                                                                                           | List of plugins to disable                                     |
| plugins                         | list   | []                                                                                                                                                                                                                                                                           | List of plugins to load                                        |
| scripts                         | list   | []                                                                                                                                                                                                                                                                           | List of scripts to run for report                              |
| maintenance_file                | str    |                                                                                                                                                                                                                                                                              | Path to the maintenance file                                   |
| maintenance_sheet               | str    | maintenance                                                                                                                                                                                                                                                                  | Sheet name in the maintenance file                             |
| last_maintenance_column         | str    | Last maintenance                                                                                                                                                                                                                                                             | Column name for last maintenance                               |
| frequency_column                | str    | Frequency (days)                                                                                                                                                                                                                                                             | Column name for frequency                                      |
| item_column                     | str    | Item                                                                                                                                                                                                                                                                         | Column name for item                                           |
| operation_column                | str    | Operation                                                                                                                                                                                                                                                                    | Column name for operation                                      |
| token_file                      | str    | tokens.json                                                                                                                                                                                                                                                                  | Path to the file with tokens                                   |
| import_server_notify_fifo       | str    | /tmp/gtd_import_server_fifo                                                                                                                                                                                                                                                  | FIFO file for import server                                    |
| import_server_pidfile           | str    | /tmp/gtd_import_server.pid                                                                                                                                                                                                                                                   | PID file for import server                                     |
| notes_path                      | str    | /data/Development/notes/                                                                                                                                                                                                                                                     | Path to notes directory                                        |
| jira_url                        | str    |                                                                                                                                                                                                                                                                              | URL of Jira instance                                           |
| jira_graphql_url                | str    |                                                                                                                                                                                                                                                                              | URL of Jira GraphQL endpoint                                   |
| jira_username                   | str    |                                                                                                                                                                                                                                                                              | Username of jira user                                          |
| jira_password                   | str    |                                                                                                                                                                                                                                                                              | Password of jira user                                          |
| meals                           | str    |                                                                                                                                                                                                                                                                              | Path to meals file                                             |
| trello_this_week_label          | str    | This week                                                                                                                                                                                                                                                                    | Label Used in tasks in Trello to mark tasks for this week      |
| trello_abandoned_label          | str    | Abandoned                                                                                                                                                                                                                                                                    | Label Used in tasks in Trello to mark tasks that are abandoned |
| trello_ai_help_label            | str    | Help                                                                                                                                                                                                                                                                         | Label Used in tasks in Trello to mark tasks for AI help        |
| trello_board                    | str    |                                                                                                                                                                                                                                                                              | Trello board name                                              |
| trello_apikey                   | str    |                                                                                                                                                                                                                                                                              | Trello API key                                                 |
| trello_token                    | str    |                                                                                                                                                                                                                                                                              | Trello token                                                   |
| show_context_distribution       | bool   | False                                                                                                                                                                                                                                                                        | Show context distribution                                      |
| show_context_distribution_table | bool   | False                                                                                                                                                                                                                                                                        | Show context distribution table                                |


# Writing extensions for GTD

You can write extensions for GTD which will be added to final report. 

You can need to create plugin for GTD.

Create Python file or module inside `~/.gtd/plugins/`, for instance:

```bash 

vim ~/.gtd/plugins/myplugin.py

```

and add the following:

```python

from gtd.extensions import Report
from gtd.config import get_config_str, get_config_bool
from gtd.drive import Spreadsheet
import datetime
from gtd.style import section, table

def add_extensions(report: Report):
    """
    This is my extension
    """
    report.add(section("My extension"))
    report.add(paragraph("Hello GTD"))
        


```

That's it! Now you will see new content generated from your extension in your report.