from setuptools import setup
from sys        import version_info

requires = ['gntp', 'stripe']

if version_info < (2, 7):
    required.append('argparse')

setup(
    name            = 'stripe_growl',
    version         = '0.1.0',
    author          = 'Michael Schade',
    author_email    = 'michael@mschade.me',
    url             = 'https://github.com/michaelschade/stripe_growl/',
    description     = 'Polls Stripe.com and displays new events with Growl.',
    setup_requires  = requires,
)
