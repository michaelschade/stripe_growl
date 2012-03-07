APP_NAME = 'Stripe Growl'

class StripeNotifier(object):
    NOTIFICATIONS = [
        # App events
        'info',
        'error',
        # Stripe event types
        'charge.succeeded',
    ]

    def __init__(self, api_key, max_events, since_id=None):
        """
        max_events: if None, defaults to 4. This is the maximum number of event
        notifications that Growl will display during a single poll.

        since_id: a POSIX timestamp in UTC that is used to filter Stripe
        events. If None, defaults to the current time (in UTC).
        """
        # Setup Stripe
        import stripe
        self.stripe         = stripe
        self.stripe.api_key = api_key
        self.max_events     = max_events
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
        except self.stripe.StripeError, e:
            msg = e.json_body['error']['message']
            self._notify('error', '%s: Error' % APP_NAME, msg)
            return False
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
    # Setup argument parser
    import argparse
    parser = argparse.ArgumentParser(
        description='Receive Growl notifications of Stripe events',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('key', type=str, help='Your Stripe secret API key.')
    parser.add_argument(
        '--poll-events', type=int, default=4,
        help='Maximum number of events to display at a time.'
    )
    parser.add_argument(
        '--poll-interval', type=int, default=5,
        help='Delay (in minutes) between polls for Stripe events (minimum: 5)'
    )
    args = vars(parser.parse_args())
    # Start notifier
    sn = StripeNotifier(
        api_key     = args['key'],
        max_events  = args['poll_events'],
    )
    from time import sleep
    if args['poll_interval'] < 1:
        import sys
        sys.stderr.write('ERR: You cannot provide a polling interval under'
            ' 1 minute. The preference is that you keep it at or above 5'
            ' minutes.\n')
        sys.exit(1)
    while True:
        sn.poll()
        sleep(args['poll_interval'] * 60)
