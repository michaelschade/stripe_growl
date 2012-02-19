from setuptools import setup

setup(
    name            = 'stripe_growl',
    version         = '0.1.0',
    author          = 'Michael Schade',
    author_email    = 'michael@mschade.me',
    url             = 'https://github.com/michaelschade/stripe_growl/',
    description     = 'Polls Stripe.com and displays new events with Growl.',
    setup_requires  = ['gntp', 'stripe'],
)
