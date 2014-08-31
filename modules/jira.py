from jeev.message import Attachment
import requests
import module


color_to_hex = {
    'green': '#14892c',
    'yellow': '#ffd351',
    'brown': '#815b3a',
    'warm-red': '#d04437',
    'blue-gray': '#4a6785',
    'medium-gray': '#cccccc',
}


@module.match('(?P<issue_key>[A-Z]+\-\d+)')
@module.async(module.STOP)
def jira_issue(message, issue_key):
    r = requests.get('%s/issue/%s?full' % (module.opts['cache'], issue_key))
    if r.status_code == requests.codes.ok:
        json = r.json()
        fields = json['fields']
        link = '%s/browse/%s' % (module.opts['jira'], json['key'])
        a = Attachment(link) \
            .icon(fields['issuetype']['iconUrl']) \
            .color(color_to_hex.get(fields['status']['statusCategory']['colorName'], 'good')) \
            .name("jira") \
            .field("Summary", fields['summary']) \
            .field("Status", fields['status']['name'], True) \
            .field("Assignee", fields['assignee']['displayName'], True) \

        message.reply_with_attachment(a)