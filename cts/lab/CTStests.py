""" Test-specific classes for Pacemaker's Cluster Test Suite (CTS)
"""

__copyright__ = "Copyright 2000-2023 the Pacemaker project contributors"
__license__ = "GNU General Public License version 2 or later (GPLv2+) WITHOUT ANY WARRANTY"

#
#        SPECIAL NOTE:
#
#        Tests may NOT implement any cluster-manager-specific code in them.
#        EXTEND the ClusterManager object to provide the base capabilities
#        the test needs if you need to do something that the current CM classes
#        do not.  Otherwise you screw up the whole point of the object structure
#        in CTS.
#
#                Thank you.
#

import re
import time

from stat import *

from pacemaker import BuildOptions
from pacemaker._cts.CTS import NodeStatus
from pacemaker._cts.audits import AuditResource
from pacemaker._cts.tests import *
from pacemaker._cts.timer import Timer

AllTestClasses = [ ]
AllTestClasses.append(FlipTest)
AllTestClasses.append(RestartTest)
AllTestClasses.append(StonithdTest)
AllTestClasses.append(StartOnebyOne)
AllTestClasses.append(SimulStart)
AllTestClasses.append(SimulStop)
AllTestClasses.append(StopOnebyOne)
AllTestClasses.append(RestartOnebyOne)
AllTestClasses.append(PartialStart)
AllTestClasses.append(StandbyTest)
AllTestClasses.append(MaintenanceMode)
AllTestClasses.append(ResourceRecover)
AllTestClasses.append(ComponentFail)
AllTestClasses.append(SplitBrainTest)
AllTestClasses.append(Reattach)


class SpecialTest1(CTSTest):
    '''Set up a custom test to cause quorum failure issues for Andrew'''
    def __init__(self, cm):
        CTSTest.__init__(self,cm)
        self.name = "SpecialTest1"
        self._startall = SimulStartLite(cm)
        self.restart1 = RestartTest(cm)
        self.stopall = SimulStopLite(cm)

    def __call__(self, node):
        '''Perform the 'SpecialTest1' test for Andrew. '''
        self.incr("calls")

        #        Shut down all the nodes...
        ret = self.stopall(None)
        if not ret:
            return self.failure("Could not stop all nodes")

        # Test config recovery when the other nodes come up
        self._rsh(node, "rm -f " + BuildOptions.CIB_DIR + "/cib*")

        #        Start the selected node
        ret = self.restart1(node)
        if not ret:
            return self.failure("Could not start "+node)

        #        Start all remaining nodes
        ret = self._startall(None)
        if not ret:
            return self.failure("Could not start the remaining nodes")

        return self.success()

    @property
    def errors_to_ignore(self):
        """ Return list of errors which should be ignored """

        # Errors that occur as a result of the CIB being wiped
        return [ r"error.*: v1 patchset error, patch failed to apply: Application of an update diff failed",
                 r"error.*: Resource start-up disabled since no STONITH resources have been defined",
                 r"error.*: Either configure some or disable STONITH with the stonith-enabled option",
                 r"error.*: NOTE: Clusters with shared data need STONITH to ensure data integrity" ]

AllTestClasses.append(SpecialTest1)


class NearQuorumPointTest(CTSTest):
    '''
    This test brings larger clusters near the quorum point (50%).
    In addition, it will test doing starts and stops at the same time.

    Here is how I think it should work:
    - loop over the nodes and decide randomly which will be up and which
      will be down  Use a 50% probability for each of up/down.
    - figure out what to do to get into that state from the current state
    - in parallel, bring up those going up  and bring those going down.
    '''

    def __init__(self, cm):
        CTSTest.__init__(self,cm)
        self.name = "NearQuorumPoint"

    def __call__(self, dummy):
        '''Perform the 'NearQuorumPoint' test. '''
        self.incr("calls")
        startset = []
        stopset = []

        stonith = self._cm.prepare_fencing_watcher("NearQuorumPoint")
        #decide what to do with each node
        for node in self._env["nodes"]:
            action = self._env.random_gen.choice(["start","stop"])
            #action = self._env.random_gen.choice(["start","stop","no change"])
            if action == "start" :
                startset.append(node)
            elif action == "stop" :
                stopset.append(node)

        self.debug("start nodes:" + repr(startset))
        self.debug("stop nodes:" + repr(stopset))

        #add search patterns
        watchpats = [ ]
        for node in stopset:
            if self._cm.ShouldBeStatus[node] == "up":
                watchpats.append(self.templates["Pat:We_stopped"] % node)

        for node in startset:
            if self._cm.ShouldBeStatus[node] == "down":
                #watchpats.append(self.templates["Pat:NonDC_started"] % node)
                watchpats.append(self.templates["Pat:Local_started"] % node)
            else:
                for stopping in stopset:
                    if self._cm.ShouldBeStatus[stopping] == "up":
                        watchpats.append(self.templates["Pat:They_stopped"] % (node, self._cm.key_for_node(stopping)))

        if len(watchpats) == 0:
            return self.skipped()

        if len(startset) != 0:
            watchpats.append(self.templates["Pat:DC_IDLE"])

        watch = self.create_watch(watchpats, self._env["DeadTime"]+10)

        watch.set_watch()

        #begin actions
        for node in stopset:
            if self._cm.ShouldBeStatus[node] == "up":
                self._cm.StopaCMnoBlock(node)

        for node in startset:
            if self._cm.ShouldBeStatus[node] == "down":
                self._cm.StartaCMnoBlock(node)

        #get the result
        if watch.look_for_all():
            self._cm.cluster_stable()
            self._cm.fencing_cleanup("NearQuorumPoint", stonith)
            return self.success()

        self._logger.log("Warn: Patterns not found: " + repr(watch.unmatched))

        #get the "bad" nodes
        upnodes = []
        for node in stopset:
            if self._cm.StataCM(node) == 1:
                upnodes.append(node)

        downnodes = []
        for node in startset:
            if self._cm.StataCM(node) == 0:
                downnodes.append(node)

        self._cm.fencing_cleanup("NearQuorumPoint", stonith)
        if upnodes == [] and downnodes == []:
            self._cm.cluster_stable()

            # Make sure they're completely down with no residule
            for node in stopset:
                self._rsh(node, self.templates["StopCmd"])

            return self.success()

        if len(upnodes) > 0:
            self._logger.log("Warn: Unstoppable nodes: " + repr(upnodes))

        if len(downnodes) > 0:
            self._logger.log("Warn: Unstartable nodes: " + repr(downnodes))

        return self.failure()

    def is_applicable(self):
        return True

AllTestClasses.append(NearQuorumPointTest)


def TestList(cm, audits):
    result = []
    for testclass in AllTestClasses:
        bound_test = testclass(cm)
        if bound_test.is_applicable():
            bound_test.audits = audits
            result.append(bound_test)
    return result


class RemoteLXC(CTSTest):
    def __init__(self, cm):
        CTSTest.__init__(self,cm)
        self.name = "RemoteLXC"
        self._start = StartTest(cm)
        self._startall = SimulStartLite(cm)
        self.num_containers = 2
        self.is_container = True
        self.fail_string = ""

    def start_lxc_simple(self, node):

        # restore any artifacts laying around from a previous test.
        self._rsh(node, "/usr/share/pacemaker/tests/cts/lxc_autogen.sh -s -R &>/dev/null")

        # generate the containers, put them in the config, add some resources to them
        pats = [ ]
        watch = self.create_watch(pats, 120)
        watch.set_watch()
        pats.append(self.templates["Pat:RscOpOK"] % ("start", "lxc1"))
        pats.append(self.templates["Pat:RscOpOK"] % ("start", "lxc2"))
        pats.append(self.templates["Pat:RscOpOK"] % ("start", "lxc-ms"))
        pats.append(self.templates["Pat:RscOpOK"] % ("promote", "lxc-ms"))

        self._rsh(node, "/usr/share/pacemaker/tests/cts/lxc_autogen.sh -g -a -m -s -c %d &>/dev/null" % self.num_containers)

        with Timer(self._logger, self.name, "remoteSimpleInit"):
            watch.look_for_all()

        if watch.unmatched:
            self.fail_string = "Unmatched patterns: %s" % (repr(watch.unmatched))
            self.failed = True

    def cleanup_lxc_simple(self, node):

        pats = [ ]
        # if the test failed, attempt to clean up the cib and libvirt environment
        # as best as possible 
        if self.failed:
            # restore libvirt and cib
            self._rsh(node, "/usr/share/pacemaker/tests/cts/lxc_autogen.sh -s -R &>/dev/null")
            return

        watch = self.create_watch(pats, 120)
        watch.set_watch()

        pats.append(self.templates["Pat:RscOpOK"] % ("stop", "container1"))
        pats.append(self.templates["Pat:RscOpOK"] % ("stop", "container2"))

        self._rsh(node, "/usr/share/pacemaker/tests/cts/lxc_autogen.sh -p &>/dev/null")

        with Timer(self._logger, self.name, "remoteSimpleCleanup"):
            watch.look_for_all()

        if watch.unmatched:
            self.fail_string = "Unmatched patterns: %s" % (repr(watch.unmatched))
            self.failed = True

        # cleanup libvirt
        self._rsh(node, "/usr/share/pacemaker/tests/cts/lxc_autogen.sh -s -R &>/dev/null")

    def __call__(self, node):
        '''Perform the 'RemoteLXC' test. '''
        self.incr("calls")

        ret = self._startall(None)
        if not ret:
            return self.failure("Setup failed, start all nodes failed.")

        (rc, _) = self._rsh(node, "/usr/share/pacemaker/tests/cts/lxc_autogen.sh -v &>/dev/null")
        if rc == 1:
            self.log("Environment test for lxc support failed.")
            return self.skipped()

        self.start_lxc_simple(node)
        self.cleanup_lxc_simple(node)

        self.debug("Waiting for the cluster to recover")
        self._cm.cluster_stable()

        if self.failed:
            return self.failure(self.fail_string)

        return self.success()

    @property
    def errors_to_ignore(self):
        """ Return list of errors which should be ignored """

        return [ r"Updating failcount for ping",
                 r"schedulerd.*: Recover\s+(ping|lxc-ms|container)\s+\(.*\)",
                 # The orphaned lxc-ms resource causes an expected transition error
                 # that is a result of the scheduler not having knowledge that the
                 # promotable resource used to be a clone. As a result, it looks like that
                 # resource is running in multiple locations when it shouldn't... But in
                 # this instance we know why this error is occurring and that it is expected.
                 r"Calculated [Tt]ransition .*pe-error",
                 r"Resource lxc-ms .* is active on 2 nodes attempting recovery",
                 r"Unknown operation: fail",
                 r"VirtualDomain.*ERROR: Unable to determine emulator" ]

AllTestClasses.append(RemoteLXC)


class RemoteBasic(RemoteDriver):
    def __init__(self, cm):
        RemoteDriver.__init__(self, cm)
        self.name = "RemoteBasic"

    def __call__(self, node):
        '''Perform the 'RemoteBaremetal' test. '''

        if not self.start_new_test(node):
            return self.failure(self.fail_string)

        self.test_attributes(node)
        self.cleanup_metal(node)

        self.debug("Waiting for the cluster to recover")
        self._cm.cluster_stable()
        if self.failed:
            return self.failure(self.fail_string)

        return self.success()

AllTestClasses.append(RemoteBasic)

class RemoteStonithd(RemoteDriver):
    def __init__(self, cm):
        RemoteDriver.__init__(self, cm)
        self.name = "RemoteStonithd"

    def __call__(self, node):
        '''Perform the 'RemoteStonithd' test. '''

        if not self.start_new_test(node):
            return self.failure(self.fail_string)

        self.fail_connection(node)
        self.cleanup_metal(node)

        self.debug("Waiting for the cluster to recover")
        self._cm.cluster_stable()
        if self.failed:
            return self.failure(self.fail_string)

        return self.success()

    def is_applicable(self):
        if not RemoteDriver.is_applicable(self):
            return False

        if "DoFencing" in self._env:
            return self._env["DoFencing"]

        return True

    @property
    def errors_to_ignore(self):
        """ Return list of errors which should be ignored """

        return [ r"Lost connection to Pacemaker Remote node",
                 r"Software caused connection abort",
                 r"pacemaker-controld.*:\s+error.*: Operation remote-.*_monitor",
                 r"pacemaker-controld.*:\s+error.*: Result of monitor operation for remote-.*",
                 r"schedulerd.*:\s+Recover\s+remote-.*\s+\(.*\)",
                 r"error: Result of monitor operation for .* on remote-.*: Internal communication failure" ] + super().errors_to_ignore

AllTestClasses.append(RemoteStonithd)


class RemoteMigrate(RemoteDriver):
    def __init__(self, cm):
        RemoteDriver.__init__(self, cm)
        self.name = "RemoteMigrate"

    def __call__(self, node):
        '''Perform the 'RemoteMigrate' test. '''

        if not self.start_new_test(node):
            return self.failure(self.fail_string)

        self.migrate_connection(node)
        self.cleanup_metal(node)

        self.debug("Waiting for the cluster to recover")
        self._cm.cluster_stable()
        if self.failed:
            return self.failure(self.fail_string)

        return self.success()

    def is_applicable(self):
        if not RemoteDriver.is_applicable(self):
            return 0
        # This test requires at least three nodes: one to convert to a
        # remote node, one to host the connection originally, and one
        # to migrate the connection to.
        if len(self._env["nodes"]) < 3:
            return 0
        return 1

AllTestClasses.append(RemoteMigrate)


class RemoteRscFailure(RemoteDriver):
    def __init__(self, cm):
        RemoteDriver.__init__(self, cm)
        self.name = "RemoteRscFailure"

    def __call__(self, node):
        '''Perform the 'RemoteRscFailure' test. '''

        if not self.start_new_test(node):
            return self.failure(self.fail_string)

        # This is an important step. We are migrating the connection
        # before failing the resource. This verifies that the migration
        # has properly maintained control over the remote-node.
        self.migrate_connection(node)

        self.fail_rsc(node)
        self.cleanup_metal(node)

        self.debug("Waiting for the cluster to recover")
        self._cm.cluster_stable()
        if self.failed:
            return self.failure(self.fail_string)

        return self.success()

    @property
    def errors_to_ignore(self):
        """ Return list of errors which should be ignored """

        return [ r"schedulerd.*: Recover\s+remote-rsc\s+\(.*\)",
                 r"Dummy.*: No process state file found" ] + super().errors_to_ignore

    def is_applicable(self):
        if not RemoteDriver.is_applicable(self):
            return 0
        # This test requires at least three nodes: one to convert to a
        # remote node, one to host the connection originally, and one
        # to migrate the connection to.
        if len(self._env["nodes"]) < 3:
            return 0
        return 1

AllTestClasses.append(RemoteRscFailure)

# vim:ts=4:sw=4:et:
