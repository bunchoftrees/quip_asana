import json
import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Asana Configuration
ASANA_ACCESS_TOKEN = os.getenv('ASANA_ACCESS_TOKEN')
ASANA_PROJECT_IDS = os.getenv('ASANA_PROJECT_IDS').split(',')
ASANA_HEADERS = {
    'Authorization': f'Bearer {ASANA_ACCESS_TOKEN}'
}

# Quip Configuration
QUIP_ACCESS_TOKEN = os.getenv('QUIP_ACCESS_TOKEN')
QUIP_HEADERS = {
    'Authorization': f'Bearer {QUIP_ACCESS_TOKEN}'
}


def get_asana_tasks(project_id, start_date, end_date):
    url = f'https://app.asana.com/api/1.0/projects/{project_id}/tasks'
    params = {
        'opt_fields': 'name,completed,due_on,custom_fields',
        'completed_since': start_date,
        'due_on': end_date
    }
    response = requests.get(url, headers=ASANA_HEADERS, params=params)
    return response.json()['data']


def format_tasks_for_quip(tasks):
    last_week = []
    next_week = []
    blockers = []
    today = datetime.now().date()
    for task in tasks:
        due_date = task['due_on']
        if due_date:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            task_entry = f"- {task['name']} (Due on: {due_date})"
            if today - timedelta(days=7) <= due_date < today:
                last_week.append(task_entry)
            elif today < due_date <= today + timedelta(days=7):
                next_week.append(task_entry)

            # Check for blockers
            for field in task['custom_fields']:
                if field['name'] == 'Blockers' and field['text_value']:
                    blockers.append(
                        f"- {task['name']} (Blocker: {field['text_value']})")
    return last_week, next_week, blockers


def create_quip_document(last_week, next_week, blockers):
    title = f"Weekly Projects ({datetime.now().strftime('%Y-%m-%d')})"
    content = f"""
    # Weekly Projects ({datetime.now().strftime('%Y-%m-%d')})

    ## Last Week
    {'\n'.join(last_week)}

    ## Next Week
    {'\n'.join(next_week)}

    ## Blockers
    {'\n'.join(blockers)}
    """
    url = 'https://platform.quip.com/1/threads/new-document'
    data = {
        'content': content,
        'title': title
    }
    response = requests.post(url, headers=QUIP_HEADERS, json=data)
    return response.json()


def lambda_handler(event, context):
    start_date_last_week = (
        datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    end_date_next_week = (
        datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

    all_last_week_tasks = []
    all_next_week_tasks = []
    all_blockers = []

    for project_id in ASANA_PROJECT_IDS:
        tasks = get_asana_tasks(
            project_id, start_date_last_week, end_date_next_week)
        last_week_tasks, next_week_tasks, blockers = format_tasks_for_quip(
            tasks)
        all_last_week_tasks.extend(last_week_tasks)
        all_next_week_tasks.extend(next_week_tasks)
        all_blockers.extend(blockers)

    create_quip_document(all_last_week_tasks,
                         all_next_week_tasks, all_blockers)

    return {
        'statusCode': 200,
        'body': json.dumps('Quip document created successfully!')
    }
