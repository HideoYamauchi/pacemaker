#
# Copyright 2024 the Pacemaker project contributors
#
# The version control history for this file may have further details.
#
# This source code is licensed under the GNU General Public License version 2
# or later (GPLv2+) WITHOUT ANY WARRANTY.
#

include $(top_srcdir)/mk/common.mk
include $(top_srcdir)/mk/tap.mk
include $(top_srcdir)/mk/unittest.mk

# Add "_test" to the end of all test program names to simplify .gitignore.
check_PROGRAMS = pcmk__set_scheduler_defaults_test	\
		 pcmk__update_recheck_time_test		\
		 pcmk_get_dc_test			\
		 pcmk_get_no_quorum_policy_test		\
		 pcmk_has_quorum_test			\
		 pcmk_new_scheduler_test		\
		 pcmk_set_scheduler_cib_test

TESTS = $(check_PROGRAMS)
