
import sys

from threading import Event
from time import time as _time
from heapq import heapify, heappush, heappop

try:
    import CSThread as Thread
except:
    import Thread
if ("--debugThread" in sys.argv):
    print "Task imported", Thread

# some debugging
_debug = ('--debugTask' in sys.argv)

# there can be only one task manager
taskManager = None

# if a task is installed before the task manager is created it 
# will be put in this temporary list and installed when the 
# manager is finally created.
_unscheduledTasks = []

#
#   _Task
#

class _Task:

    def __init__(self):
        self.taskTime = None
        self.isScheduled = False

    def InstallTask(self, when=None):
        global taskManager

        # fallback to the inited value
        if when is None:
            when = self.taskTime
        if when is None:
            raise RuntimeError, "schedule missing, use zero for 'now'"
        self.taskTime = when
        
        # pass along to the task manager
        if not taskManager:
            _unscheduledTasks.append(self)
        else:
            taskManager.InstallTask(self)

    def ProcessTask(self):
        raise RuntimeError, "ProcessTask must be overridden"

    def SuspendTask(self):
        global taskManager

        taskManager.SuspendTask(self)

    def ResumeTask(self):
        global taskManager

        taskManager.ResumeTask(self)

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

def OneShotFunction(fn):
    class OneShotFunctionTask(OneShotDeleteTask):
        def ProcessTask(self):
            fn()
        def __call__(self, *args, **kwargs):
            fn(*args, **kwargs)
    task = OneShotFunctionTask(_time())
    task.InstallTask()
    
    return task
    
#
#   RecurringTask
#

class RecurringTask(_Task):

    def __init__(self, interval):
        _Task.__init__(self)
        self.taskInterval = interval
        self.taskTime = _time() + (self.taskInterval / 1000)

    def InstallTask(self):
        global taskManager, _unscheduledTasks

        # get ready for the next interval
        self.taskTime = _time() + (self.taskInterval / 1000)
        
        # pass along to the task manager
        if not taskManager:
            _unscheduledTasks.append(self)
        else:
            taskManager.InstallTask(self)
        
#
#   RecurringFunction
#

def RecurringFunction(interval):
    def RecurringFunctionDecorator(fn):
        class RecurringFunctionTask(RecurringTask):
            def ProcessTask(self):
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

class TaskManager:

    def __init__(self):
        global taskManager, _unscheduledTasks

        assert not taskManager, "task manager already created"
        taskManager = self

        self.mutex = Thread.Lock(self)
        self.tasks = []

        # there may be tasks created that couldn't be scheduled
        # because a task manager wasn't created yet.
        if _unscheduledTasks:
            for task in _unscheduledTasks:
                self.InstallTask(task)
        
    def InstallTask(self, task):
        if _debug:
            print "TaskManager.InstallTask", task
            
        # lock down the task list
        self.mutex.acquire()

        # save this in the task list
        heappush( self.tasks, (task.taskTime, task) )
        task.isScheduled = True

        # release the mutex
        self.mutex.release()

    def SuspendTask(self, task):
        if _debug:
            print "TaskManager.SuspendTask", task
            
        # lock down the task list
        self.mutex.acquire()

        # remove this guy
        for i in range(len(self.tasks)):
            when, curtask = self.tasks[i]
            if task is curtask:
                del self.tasks[i]
                task.isScheduled = False
                heapify(self.tasks)
                break
                
        # release the mutex
        self.mutex.release()

    def ResumeTask(self, task):
        if _debug:
            print "TaskManager.ResumeTask", task
            
        # just re-install it
        self.InstallTask(task)

    def GetNextTask(self):
        """Get the next task if there's one that should be processed, 
        and return how long it will be until the next one should be 
        processed."""
        if _debug:
            print "TaskManager.GetNextTask"

        # lock down the task list
        self.mutex.acquire()

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
                    delta = when - now
            else:
                delta = when - now
            
        # release the mutex
        self.mutex.release()

        # return the task to run and how long to wait for the next one
        return (task, delta)

    def ProcessTask(self, task):
        if _debug:
            print "TaskManager.ProcessTask", task
            
        # process the task
        task.ProcessTask()

        # see if it should be rescheduled
        if isinstance(task, OneShotDeleteTask):
            del task
        elif isinstance(task, RecurringTask):
            task.InstallTask()

#
#   TaskManagerThread
#

class TaskManagerThread(TaskManager, Thread.Thread):

    def __init__(self):
        # create an event so if there are unscheduled events 
        # they can be installed.
        self.event = Event()
        
        TaskManager.__init__(self)
        Thread.Thread.__init__(self, "TaskManager")
        
        self.maxWaitTime = 60

        self.go = 0
        self.setDaemon(1)

    def run(self):
        """Get the next task and run it."""
        self.go = 1
        while self.go:
            task, delta = self.GetNextTask()

            if task:
                self.ProcessTask(task)

            if delta is None:
                self.event.wait(self.maxWaitTime)
            elif (delta > 0):
                self.event.wait(min(self.maxWaitTime,delta))
            self.event.clear()

    def halt(self):
        """Stop the thread."""
        self.go = 0
        self.event.set()

    def InstallTask(self, task):
        """Wake up the thread after installing a task."""
        if _debug:
            print "TaskManagerThread.InstallTask", task
            
        TaskManager.InstallTask(self, task)
        self.event.set()

    def SuspendTask(self, task):
        """Wake up the thread after suspending a task."""
        if _debug:
            print "TaskManagerThread.SuspendTask", task
            
        TaskManager.SuspendTask(self, task)
        self.event.set()

TaskManagerThread()
