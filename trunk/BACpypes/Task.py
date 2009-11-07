#/usr/bin/python

"""
Task
"""

import sys
import logging

from time import time as _time
from heapq import heapify, heappush, heappop

from Singleton import SingletonLogging
from Debugging import DebugContents, Logging, FunctionLogging
from CommandLogging import ConsoleLogHandler

# some debugging
_log = logging.getLogger(__name__)
if ("--debugTask" in sys.argv):
    ConsoleLogHandler(_log)

# globals
_taskManager = None
_unscheduledTasks = []

# only defined for linux platforms
if 'linux' in sys.platform:
    from Event import WaitableEvent
    #
    #   _Trigger
    #
    #   An instance of this class is used in the task manager to break 
    #   the asyncore.loop() call.  In this case, handle_read will 
    #   immediately "clear" the event.
    #

    class _Trigger(WaitableEvent, Logging):

        def handle_read(self):
            _Trigger._debug("handle_read")
            data = self.recv(1)

#
#   _Task
#

class _Task(DebugContents, Logging):

    _debugContents = ('taskTime', 'isScheduled')
    
    def __init__(self):
        self.taskTime = None
        self.isScheduled = False

    def InstallTask(self, when=None):
        global _taskManager, _unscheduledTasks

        # fallback to the inited value
        if when is None:
            when = self.taskTime
        if when is None:
            raise RuntimeError, "schedule missing, use zero for 'now'"
        self.taskTime = when
        
        # pass along to the task manager
        if not _taskManager:
            _unscheduledTasks.append(self)
        else:
            _taskManager.InstallTask(self)

    def ProcessTask(self):
        raise RuntimeError, "ProcessTask must be overridden"

    def SuspendTask(self):
        global _taskManager

        _taskManager.SuspendTask(self)

    def ResumeTask(self):
        global _taskManager

        _taskManager.ResumeTask(self)

#
#   OneShotTask
#

class OneShotTask(_Task):

    def __init__(self, when=None):
        _Task.__init__(self)
        self.taskTime = when

#
#   OneShotDeleteTask
#

class OneShotDeleteTask(_Task):

    def __init__(self, when=None):
        _Task.__init__(self)
        self.taskTime = when

#
#   OneShotFunction
#

@FunctionLogging
def OneShotFunction(fn, *args, **kwargs):
    class OneShotFunctionTask(OneShotDeleteTask):
        def ProcessTask(self):
            OneShotFunction._debug("ProcessTask %r %s %s", fn, repr(args), repr(kwargs))
            fn(*args, **kwargs)
    task = OneShotFunctionTask(_time())
    task.InstallTask()
    
    return task
    
#
#   FunctionTask
#

def FunctionTask(fn, *args, **kwargs):
    _log.debug("FunctionTask %r %r %r", fn, args, kwargs)
    
    class _FunctionTask(OneShotDeleteTask):
        def ProcessTask(self):
            _log.debug("ProcessTask (%r %r %r)", fn, args, kwargs)
            fn(*args, **kwargs)
    task = _FunctionTask()
    _log.debug("    - task: %r", task)
    
    return task
    
#
#   RecurringTask
#

class RecurringTask(_Task):

    _debugContents = ('taskInterval',)
    
    def __init__(self, interval=None):
        _Task.__init__(self)
        self.taskInterval = interval
        if interval is None:
            self.taskTime = None
        else:
            self.taskTime = _time() + (self.taskInterval / 1000)

    def InstallTask(self, interval=None):
        global _taskManager, _unscheduledTasks
        
        # set the interval if it hasn't already been set
        if interval is not None:
            self.taskInterval = interval
        if not self.taskInterval:
            raise RuntimeError, "interval unset, use ctor or InstallTask parameter"
            
        # get ready for the next interval (aligned)
        now = _time()
        interval = self.taskInterval / 1000.0
        self.taskTime = now + interval - (now % interval)
        
        # pass along to the task manager
        if not _taskManager:
            _unscheduledTasks.append(self)
        else:
            _taskManager.InstallTask(self)
        
#
#   RecurringFunctionTask
#

@FunctionLogging
def RecurringFunctionTask(interval, fn, *args, **kwargs):
    RecurringFunctionTask._debug("RecurringFunctionTask %r %r %r", fn, args, kwargs)
    
    class _RecurringFunctionTask(RecurringTask):
        def __init__(self, interval):
            RecurringTask.__init__(self, interval)
            
        def ProcessTask(self):
            RecurringFunctionTask._debug("ProcessTask %r %r %r", fn, args, kwargs)
            fn(*args, **kwargs)
            
    task = _RecurringFunctionTask(interval)
    RecurringFunctionTask._debug("    - task: %r", task)
    
    return task
    
#
#   RecurringFunction
#

@FunctionLogging
def RecurringFunction(interval):
    def RecurringFunctionDecorator(fn):
        class RecurringFunctionTask(RecurringTask):
            def ProcessTask(self):
                RecurringFunction._debug("ProcessTask %r", fn)
                fn()
            def __call__(self, *args, **kwargs):
                fn(*args, **kwargs)
        task = RecurringFunctionTask(interval)
        task.InstallTask()
        
        return task
    
    return RecurringFunctionDecorator

#
#   TaskManager
#

class TaskManager(SingletonLogging):

    def __init__(self):
        TaskManager._debug("__init__")
        global _taskManager, _unscheduledTasks

        # initialize
        self.tasks = []
        if 'linux' in sys.platform:
            self.trigger = _Trigger()
        else:
            self.trigger = None
            
        # task manager is this instance
        _taskManager = self

        # there may be tasks created that couldn't be scheduled
        # because a task manager wasn't created yet.
        if _unscheduledTasks:
            for task in _unscheduledTasks:
                self.InstallTask(task)
        
    def InstallTask(self, task):
        TaskManager._debug("InstallTask %r %r", task, task.taskTime)
            
        # if this is already installed, suspend it
        if task.isScheduled:
            self.SuspendTask(task)
        
        # save this in the task list
        heappush( self.tasks, (task.taskTime, task) )
        self._debug("    - tasks: %r", self.tasks)
        
        task.isScheduled = True

        # trigger the event
        if self.trigger:
            self.trigger.set()
        
    def SuspendTask(self, task):
        TaskManager._debug("SuspendTask %r", task)
        
        # remove this guy
        for i, (when, curtask) in enumerate(self.tasks):
            if task is curtask:
                TaskManager._debug("    - task found")
                del self.tasks[i]
                
                task.isScheduled = False
                heapify(self.tasks)
                break
        else:
            TaskManager._debug("    - task not found")
                
        # trigger the event
        if self.trigger:
            self.trigger.set()
        
    def ResumeTask(self, task):
        TaskManager._debug("ResumeTask %r", task)
            
        # just re-install it
        self.InstallTask(task)

    def GetNextTask(self):
        """Get the next task if there's one that should be processed, 
        and return how long it will be until the next one should be 
        processed."""
        TaskManager._debug("GetNextTask")

        # get the time
        now = _time()

        task = None
        delta = None

        if self.tasks:
            # look at the first task
            when, nxttask = self.tasks[0]
            if when <= now:
                # pull it off the list and mark that it's no longer scheduled
                heappop(self.tasks)
                task = nxttask
                task.isScheduled = False
                
                if self.tasks:
                    when, nxttask = self.tasks[0]
                    # peek at the next task, return how long to wait
                    delta = max(when - now, 0.0)
            else:
                delta = when - now
            
        # return the task to run and how long to wait for the next one
        return (task, delta)

    def ProcessTask(self, task):
        TaskManager._debug("ProcessTask %r", task)
        
        # process the task
        task.ProcessTask()

        # see if it should be rescheduled
        if isinstance(task, RecurringTask):
            task.InstallTask()
        elif isinstance(task, OneShotDeleteTask):
            del task

