#!/usr/bin/python

"""
This application demonstrates doing something at a regular interval.
"""

import sys

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser

from bacpypes.core import run
from bacpypes.task import RecurringTask

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   PrairieDog
#

@bacpypes_debugging
class PrairieDog(RecurringTask):

    def __init__(self, dog_number, interval):
        if _debug: PrairieDog._debug("__init__ %r %r", dog_number, interval)

        # save the identity
        self.dog_number = dog_number

        # this is a recurring task
        RecurringTask.__init__(self, interval)

        # install it
        self.install_task()

    def process_task(self):
        if _debug: PrairieDog._debug("process_task")

        sys.stdout.write("%d woof!\n" % (self.dog_number,))

#
#   __main__
#

try:
    # parse the command line arguments
    parser = ConfigArgumentParser(description=__doc__)

    # add an argument for seconds per dog
    parser.add_argument('seconds', metavar='N', type=int, nargs='+',
          help='number of seconds for each dog',
          )

    # now parse the arguments
    args = parser.parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # make some dogs
    for i, sec in enumerate(args.seconds):
        dog = PrairieDog(i, sec * 1000)
        if _debug: _log.debug("    - dog: %r", dog)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
