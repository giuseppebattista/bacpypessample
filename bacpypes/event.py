#/usr/bin/python

"""
Event
"""

import asyncore
import os
import select
import logging

from debugging import Logging

# some debugging
_log = logging.getLogger(__name__)

#
#   WaitableEvent
#
#   An instance of this class can be used like a Threading.Event, but will 
#   break the asyncore.loop().
#

class WaitableEvent(asyncore.file_dispatcher, Logging):

    def __init__(self):
        WaitableEvent._debug("__init__")
        
        # make a pipe
        self._read_fd, self._write_fd = os.pipe()
        
        # continue with init
        asyncore.file_dispatcher.__init__(self, self._read_fd)

    def readable(self):
        # we are always happy to read
        return True

    def writable(self):
        # we never have anything to write
        return False

    def handle_read(self):
        WaitableEvent._debug("handle_read")

    def handle_write(self):
        WaitableEvent._debug("handle_write")

    def handle_close(self):
        WaitableEvent._debug("handle_close")
        self.close()
    
    def wait(self, timeout=None):
        rfds, wfds, efds = select.select([self._read_fd], [], [], timeout)
        return self._read_fd in rfds
        
    def isSet(self):
        return self.wait(0)
    
    def set(self):
        WaitableEvent._debug("set")
        if not self.isSet():
            os.write(self._write_fd, '1')
        
    def clear(self):
        WaitableEvent._debug("clear")
        if self.isSet():
            os.read(self._read_fd, 1)
        
    def __del__(self):
        WaitableEvent._debug("__del__")
        os.close(self._read_fd)
        os.close(self._write_fd)

