# General config
APP_NAME      = 'Stripe Growl'
MAX_EVENTS    = 4
POLL_INTERVAL = 5 # Minutes

# Environment variables
ENV_API  = 'SGROWL_API_KEY'
ENV_ME   = 'SGROWL_MAX_EVENTS'
ENV_POLL = 'SGROWL_POLL_INTERVAL'

class StripeNotifier(object):
    NOTIFICATIONS = [
        # App events
        'info',
        'error',
        # Stripe event types
        'charge.succeeded',
    ]

    def __init__(self, api_key, since_id=None, max_events=None):
        """
        since_id: a POSIX timestamp in UTC that is used to filter Stripe
        events. If None, defaults to the current time (in UTC).

        Max events: if None, defaults to 4. This is the maximum number of event
        notifications that Growl will display during a single poll.
        """
        # Setup Stripe
        import stripe
        self.stripe         = stripe
        self.stripe.api_key = api_key
        self.max_events     = max_events or MAX_EVENTS
        # Specified 'latest known' event (or right now)
        from time import time
        self.since_id = since_id or int(time())
        # Setup Growl notifier
        import gntp.notifier
        self.notifier = gntp.notifier.GrowlNotifier(
                            applicationName      = APP_NAME,
                            notifications        = self.NOTIFICATIONS,
                            defaultNotifications = self.NOTIFICATIONS,
                      )
        try:
            self.notifier.register()
        except:
            from sys import exit, stderr
            stderr.write("ERR: Unable to register %s with Growl.\n" % APP_NAME)
            exit(1)

    def _notify(self, noteType, title, message):
        """
        Use the Growl notifier to send an event, where note type is in
        StripeNotifier.NOTIFICATIONS.
        """
        self.notifier.notify(
            noteType    = noteType,
            title       = title,
            description = message,
        )

    def _handle_event(self, event):
        """
        Displays a notification regarding the event based on the event type.

        Currently, only 'charge.succeeded' is supported.
        """
        if event.type == 'charge.succeeded':
            from datetime import datetime
            dformat = '%b. %d, %I:%M %p'
            charge  = event.data.object.to_dict()
            created = datetime.fromtimestamp(charge['created'])
            title   = 'New Charge! (%s)' % created.strftime(dformat)
            message = "$%(amount).2f - %(description)s" % {
                'amount':       charge['amount'] / 100.,
                'description':  charge.get('description', '(no description)'),
            }
            self._notify(event.type, title, message)
        else: # Only handle charge.succeeded right now
            pass

    def poll(self):
        """
        Return a boolean indicating success (True) or failure (False). Updates
        StripeNotifier's state to only retrieve new events.
        """
        # Retrieve events
        try:
            rsp = self.stripe.Event.all(
                created = { 'gt': self.since_id },
                type    = 'charge.succeeded',
                count   = self.max_events,
            )
        except:
            self._notify(
                'error', '%s: Error' % APP_NAME, 'Unable to retrieve Events.'
            )
            return False
        else:
            count  = rsp.count
            events = rsp.data
            if not len(events): # No new events (still a success)
                return True
            # No errors; handle events
            self.since_id = events[0].created
            for event in events:
                self._handle_event(event)
            # Notify of any hidden events
            rem = count - self.max_events
            if rem > 0:
                self._notify('info', APP_NAME, '%d events not shown.' % rem)
            return True

if __name__ == '__main__':
    # Check / Retrieve Stripe.com API key
    import sys
    import os
    if not os.environ.has_key(ENV_API):
        sys.stderr.write('ERR: You must provide your Stripe API key using the'
            ' %s environment variable.\n' % ENV_API)
        sys.exit(1)
    # Start notifier
    sn = StripeNotifier(
        api_key     = os.environ[ENV_API],
        max_events  = int(os.environ.get(ENV_ME, MAX_EVENTS)),
    )
    from time import sleep
    poll = int(os.environ.get(ENV_POLL, POLL_INTERVAL))
    if poll < 1:
        sys.stderr.write('ERR: You cannot provide a polling interval under'
            ' 1 minute. The preference is that you keep it at or above 5'
            ' minutes.\n')
        sys.exit(1)
    while True:
        sn.poll()
        sleep(poll * 60)
