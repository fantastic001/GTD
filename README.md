- [GTD - Gamify The Day - God That Deadline!!!](#gtd---gamify-the-day---god-that-deadline)
- [Installation](#installation)
- [Configuration](#configuration)
- [Configure to work with Trello](#configure-to-work-with-trello)
- [Creating tasks](#creating-tasks)
  - [Command reference: gtd upload ](#command-reference-gtd-upload-)
  - [Examples](#examples)
    - [1) One task per line](#1-one-task-per-line)
    - [2) Multiline tasks (title + description)](#2-multiline-tasks-title--description)
    - [3) Tasks with checklist items](#3-tasks-with-checklist-items)
    - [4) Multiple named checklists per task](#4-multiple-named-checklists-per-task)
    - [5) Use stdin (no input file)](#5-use-stdin-no-input-file)
    - [6) Trello board/list targeting via context + parent](#6-trello-boardlist-targeting-via-context--parent)
  - [How upload integrates with Trello](#how-upload-integrates-with-trello)
  - [Troubleshooting upload](#troubleshooting-upload)
- [Services](#services)
  - [Command reference: gtd service SERVICENAME](#command-reference-gtd-service-servicename)
  - [Export closed Trello tasks to CSV](#export-closed-trello-tasks-to-csv)
- [Configuration reference](#configuration-reference)
- [Writing extensions for GTD](#writing-extensions-for-gtd)
- [Guides](#guides)
  - [Analyzing your productivity patterns](#analyzing-your-productivity-patterns)



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

## Command reference: gtd upload <OPTIONS>

Use this command to batch-create tasks from stdin or a file:

```shell
gtd upload <OPTIONS>
```

Current options (from CLI help):

```text
-i, --input INPUT
-m, --multiline
-c, --checklists
--importer IMPORTER
-p, --parent PARENT
--multi-checklist
--context CONTEXT
```

Behavior:

- `--input` reads tasks from file. If omitted, `gtd upload` reads from stdin.
- default mode (no `--multiline`, no `--checklists`): each non-empty line is one task title.
- `--multiline`: first line of a block is title, remaining lines are description; tasks are separated by an empty line.
- `--checklists`: similar block parsing, but lines starting with `*` become checklist items.
- `--multi-checklist`: only with `--checklists`; allows named checklists using a line ending with `:` (for example `Acceptance criteria:`), then `* item` lines go into that checklist.
- `--importer`: choose importer explicitly. If omitted, GTD auto-selects importer only when exactly one importer is available.
- `--parent`: target project/list for created tasks. If it does not exist, GTD creates it.
- `--context`: importer-specific context. For Trello this is the board name.

When `--checklists` is enabled, command internally uses checklist mode (you do not need `--multiline` together with it).

Duplicate protection is enabled: if a task already exists, it is skipped instead of creating a duplicate.

## Examples

### 1) One task per line

```text
buy groceries
prepare sprint demo
review notes
```

```shell
gtd upload -i tasks.txt -p "This Week"
```

### 2) Multiline tasks (title + description)

```text
Prepare monthly report
Collect data from analytics and Jira
Draft summary for stakeholders

Refactor importer layer
Split Trello-specific logic from generic import flow
```

```shell
gtd upload -i tasks_multiline.txt --multiline -p "Backlog"
```

### 3) Tasks with checklist items

```text
Release v1.2.0
Publish release notes
* Update changelog
* Tag release
* Announce in Slack

Plan Q3 roadmap
Draft goals
* Gather input from team
* Estimate initiatives
```

```shell
gtd upload -i tasks_checklists.txt --checklists -p "Planning"
```

### 4) Multiple named checklists per task

```text
Launch feature flag
Rollout with safeguards
Acceptance:
* tests pass in CI
* no errors in logs
Communication:
* update docs
* notify support
```

```shell
gtd upload -i tasks_multi_checklist.txt --checklists --multi-checklist -p "Releases"
```

### 5) Use stdin (no input file)

```shell
cat tasks.txt | gtd upload -p "Inbox"
```

### 6) Trello board/list targeting via context + parent

```shell
gtd upload -i tasks.txt --context "Backlog" -p "This Week"
```

This uploads cards to Trello board `Backlog`, list `This Week`.

## How upload integrates with Trello

With Trello plugin enabled (`gtd.trello`):

- `--context` maps to Trello board.
- `--parent` maps to Trello list.
- if list does not exist, GTD creates the list automatically.
- each imported task becomes one Trello card.
- description text is sent as card description.
- checklist data is created as Trello checklists/check items.
- uniqueness check compares open cards by title in the target list (same title in same list is treated as existing).

Trello-specific extra behavior:

- if title contains a date in format `[YYYY-MM-DD]`, importer extracts it and sets card due date.
  Example title: `Finish draft [2026-05-30]`

## Troubleshooting upload

- Problem: `No importer found` or upload fails before creating tasks.
        Fix: enable at least one importer plugin (for Trello: `gtd.trello`) or pass `--importer` explicitly.

- Problem: upload fails because multiple importers are available.
        Fix: select importer with `--importer <name>`.

- Problem: Trello board not found when using `--context`.
        Fix: ensure `--context` exactly matches one of your available Trello boards.

- Problem: wrong list/project receives tasks.
        Fix: pass `-p/--parent` explicitly. If list does not exist, GTD creates it.

- Problem: no `--parent` and upload fails unexpectedly.
        Cause: upload defaults to first available list/project. If the board has no lists, there is no default parent.
        Fix: create at least one list first, or pass `--parent` so GTD can create it.

- Problem: tasks are skipped as duplicates.
        Cause: upload uses unique mode. For Trello, duplicates are checked by open card title in target list.
        Fix: change title, choose another list, or close/archive the existing card.

- Problem: named checklist sections are ignored.
        Fix: use `--multi-checklist` and make section headers end with `:`.

- Problem: checklist lines become description text.
        Fix: checklist items must start with `*`.

- Problem: command appears to hang.
        Cause: without `--input`, upload reads from stdin.
        Fix: pass `--input <file>`, or finish stdin input with Ctrl+D.

- Problem: cannot read input file.
        Fix: verify the `--input` path exists and is readable.

# Services

Use services to fetch structured report data from plugins.

## Command reference: gtd service SERVICENAME

Conceptually, you select a service by name:

```shell
gtd service SERVICENAME
```

CSV output is enabled with `-p` / `--print-csv`:

```shell
gtd service SERVICENAME --print-csv
```

List available services:

```shell
gtd services
```

## Export closed Trello tasks to CSV

This is currently available via Trello service `TrelloClosedCards`.

1. Ensure Trello plugin is enabled in config (`gtd.trello`) and credentials are configured.
2. Verify service exists:

```shell
gtd services
```

3. Export CSV:

```shell
gtd service TrelloClosedCards --print-csv > closed_cards.csv
```

4. Optional quick check:

```shell
head -n 5 closed_cards.csv
```

`TrelloClosedCards` includes fields such as:

- `title`
- `description`
- `due_date`
- `project`
- `url`
- `labels`
- `id`
- `closed_date`
- `closed_from_today`
- `board`
- `created_date`
- `created_from_today`
- `has_primary_label`
- `has_secondary_label`

If Trello config/API fails, service returns an error payload instead of card rows.

# Configuration reference

| param                           | type   | default                                                                                                                                                                                                                                                                      | doc                                                                     |
|:--------------------------------|:-------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------|
| plugin_search_path              | list   | ["'/usr/local/share/' + PROJECT_NAME + '/plugins'", "'/usr/share/' + PROJECT_NAME + '/plugins'", "os.path.join(os.path.expanduser('~'), '.' + PROJECT_NAME, 'plugins')", "os.path.join(os.path.expanduser('~'), '.local', 'share', PROJECT_NAME, 'plugins')", 'os.getcwd()'] | List of plugin search paths                                             |
| disabled_plugins                | list   | []                                                                                                                                                                                                                                                                           | List of plugins to disable                                              |
| plugins                         | list   | []                                                                                                                                                                                                                                                                           | List of plugins to load                                                 |
| scripts                         | list   | []                                                                                                                                                                                                                                                                           | List of scripts to run for report                                       |
| context_search_paths            | list   | ['Administration', '', 'Administration/Research & Development', 'Administration/Training & Education', 'Administration/Social Responsibility']                                                                                                                               | Paths to search for context text files for projects on Google Drive     |
| context_filenames               | list   | ['Context']                                                                                                                                                                                                                                                                  | Filenames to search for context text files for projects on Google Drive |
| trello_boards                   | list   | []                                                                                                                                                                                                                                                                           | Trello board names                                                      |
| maintenance_file                | str    |                                                                                                                                                                                                                                                                              | Path to the maintenance file                                            |
| maintenance_sheet               | str    | maintenance                                                                                                                                                                                                                                                                  | Sheet name in the maintenance file                                      |
| last_maintenance_column         | str    | Last maintenance                                                                                                                                                                                                                                                             | Column name for last maintenance                                        |
| frequency_column                | str    | Frequency (days)                                                                                                                                                                                                                                                             | Column name for frequency                                               |
| item_column                     | str    | Item                                                                                                                                                                                                                                                                         | Column name for item                                                    |
| operation_column                | str    | Operation                                                                                                                                                                                                                                                                    | Column name for operation                                               |
| token_file                      | str    | tokens.json                                                                                                                                                                                                                                                                  | Path to the file with tokens                                            |
| report_template_dir             | str    | templates                                                                                                                                                                                                                                                                    | Directory with report templates                                         |
| import_server_notify_fifo       | str    | /tmp/gtd_import_server_fifo                                                                                                                                                                                                                                                  | FIFO file for import server                                             |
| import_server_pidfile           | str    | /tmp/gtd_import_server.pid                                                                                                                                                                                                                                                   | PID file for import server                                              |
| notes_path                      | str    | /data/Development/notes/                                                                                                                                                                                                                                                     | Path to notes directory                                                 |
| challange_cache_path            | str    |                                                                                                                                                                                                                                                                              | Path to challange cache directory                                       |
| jira_url                        | str    |                                                                                                                                                                                                                                                                              | URL of Jira instance                                                    |
| jira_graphql_url                | str    |                                                                                                                                                                                                                                                                              | URL of Jira GraphQL endpoint                                            |
| jira_username                   | str    |                                                                                                                                                                                                                                                                              | Username of jira user                                                   |
| jira_password                   | str    |                                                                                                                                                                                                                                                                              | Password of jira user                                                   |
| meals                           | str    |                                                                                                                                                                                                                                                                              | Path to meals file                                                      |
| trello_this_week_label          | str    | This week                                                                                                                                                                                                                                                                    | Label Used in tasks in Trello to mark tasks for this week               |
| trello_abandoned_label          | str    | Abandoned                                                                                                                                                                                                                                                                    | Label Used in tasks in Trello to mark tasks that are abandoned          |
| trello_ai_help_label            | str    | Help                                                                                                                                                                                                                                                                         | Label Used in tasks in Trello to mark tasks for AI help                 |
| trello_board                    | str    |                                                                                                                                                                                                                                                                              | Trello board name                                                       |
| trello_apikey                   | str    |                                                                                                                                                                                                                                                                              | Trello API key                                                          |
| trello_token                    | str    |                                                                                                                                                                                                                                                                              | Trello token                                                            |
| show_context_distribution       | bool   | False                                                                                                                                                                                                                                                                        | Show context distribution                                               |
| show_context_distribution_table | bool   | False                                                                                                                                                                                                                                                                        | Show context distribution table                                         |
| report_deliverables             | bool   | True                                                                                                                                                                                                                                                                         | Whether to report deliverables for closed cards this week               |


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

# Guides

## Analyzing your productivity patterns

Get closed tasks first:

        gtd service TrelloClosedCards --print-csv > closed_cards.csv

Then, you can analyze them in Excel or Jupyter notebook to find patterns in your productivity. For instance, you can find out on which days of week you are most productive, how many tasks you close on average per day, etc.

There is command to give you some insights about your productivity:

        gtd analyze --path closed_cards.csv