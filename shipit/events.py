"""
shipit.events
~~~~~~~~~~~~~

Poor mans pub-sub mechanism.
"""

EVENTS = [
 'show_open_issues',
 'hide_open_issues',

 'show_closed_issues',
 'hide_closed_issues',

 'show_open_pull_requests',
 'hide_open_pull_requests',
]


SUBSCRIBED = dict([(event,[]) for event in EVENTS])

def trigger(event, *args, **kwargs):
    if event in EVENTS:
        for callback in SUBSCRIBED[event]:
            callback(*args, **kwargs)
    else:
        raise ValueError("%s is not a valid event." % event)

def on(event, callback):
    if event in EVENTS:
        SUBSCRIBED[event].append(callback)
    else:
        raise ValueError("%s is not a valid event." % event)


