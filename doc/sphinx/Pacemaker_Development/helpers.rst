C Development Helpers
---------------------

.. index::
   single: unit testing

Sanitizers
##########

gcc supports a variety of run-time checks called sanitizers.  These can be used to
catch programming errors with memory, race conditions, various undefined behavior
conditions, and more.  Because these are run-time checks, they should only be used
during development and not in compiled packages or production code.

Certain sanitizers cannot be combined with others because their run-time checks
cause interfere.  Instead of trying to figure out which combinations work, it is
simplest to just enable one at a time.

Each supported sanitizer requires an installed libray.  In addition to just
enabling the sanitizer, their use can be configured with environment variables.
For example:

.. code-block:: none

   $ ASAN_OPTIONS=verbosity=1:replace_str=true crm_mon -1R

Pacemaker supports the following subset of gcc's sanitizers:

+--------------------+-------------------------+----------+----------------------+
| Sanitizer          | Configure Option        | Library  | Environment Variable |
+====================+=========================+==========+======================+
| Address            | --with-sanitizers=asan  | libasan  | ASAN_OPTIONS         |
+--------------------+-------------------------+----------+----------------------+
| Threads            | --with-sanitizers=tsan  | libtsan  | TSAN_OPTIONS         |
+--------------------+-------------------------+----------+----------------------+
| Undefined behavior | --with-sanitizers=ubsan | libubsan | UBSAN_OPTIONS        |
+--------------------+-------------------------+----------+----------------------+

The undefined behavior sanitizer further supports suboptions that need to be
given as CFLAGS when configuring pacemaker:

.. code-block:: none

   $ CFLAGS=-fsanitize=integer-divide-by-zero ./configure --with-sanitizers=ubsan

For more information, see the `gcc documentation <https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html>`_
which also provides links to more information on each sanitizer.

Unit Testing
############

Where possible, changes to the C side of Pacemaker should be accompanied by unit
tests.  Much of Pacemaker cannot effectively be unit tested (and there are other
testing systems used for those parts), but the ``lib`` subdirectory is pretty easy
to write tests for.

Pacemaker uses the `cmocka unit testing framework <https://cmocka.org/>`_ which looks
a lot like other unit testing frameworks for C and should be fairly familiar.  In
addition to regular unit tests, cmocka also gives us the ability to use
`mock functions <https://en.wikipedia.org/wiki/Mock_object>`_ for unit testing
functions that would otherwise be difficult to test.

Organization
____________

Pay close attention to the organization and naming of test cases to ensure the
unit tests continue to work as they should.

Tests are spread throughout the source tree, alongside the source code they test.
For instance, all the tests for the source code in ``lib/common/`` are in the
``lib/common/tests`` directory.  If there is no ``tests`` subdirectory, there are no
tests for that library yet.

Under that directory, there is a ``Makefile.am`` and additional subdirectories.  Each
subdirectory contains the tests for a single library source file.  For instance,
all the tests for ``lib/common/strings.c`` are in the ``lib/common/tests/strings``
directory.  Note that the test subdirectory does not have a ``.c`` suffix.  If there
is no test subdirectory, there are no tests for that file yet.

Finally, under that directory, there is a ``Makefile.am`` and then various source
files.  Each of these source files tests the single function that it is named
after.  For instance, ``lib/common/tests/strings/pcmk__btoa_test.c`` tests the
``pcmk__btoa()`` function in ``lib/common/strings.c``.  If there is no test
source file, there are no tests for that function yet.

The ``_test`` suffix on the test source file is important.  All tests have this
suffix, which means all the compiled test cases will also end with this suffix.
That lets us ignore all the compiled tests with a single line in ``.gitignore``:

.. code-block:: none

   /lib/*/tests/*/*_test

Adding a test
_____________

Testing a new function in an already testable source file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow these steps if you want to test a function in a source file where there
are already other tested functions.  For the purposes of this example, we will
add a test for the ``pcmk__scan_port()`` function in ``lib/common/strings.c``.  As
you can see, there are already tests for other functions in this same file in
the ``lib/common/tests/strings`` directory.

* cd into ``lib/common/tests/strings``
* Add the new file to the ``check_PROGRAMS`` variable in ``Makefile.am``, making
  it something like this:

  .. code-block:: none

      check_PROGRAMS = \
             pcmk__add_word_test             \
             pcmk__btoa_test                 \
             pcmk__scan_port_test

* Create a new ``pcmk__scan_port_test.c`` file, copying the copyright and include
  boilerplate from another file in the same directory.
* Continue with the steps in `Writing the test`_.

Testing a function in a source file without tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow these steps if you want to test a function in a source file where there
are not already other tested functions, but there are tests for other files in
the same library.  For the purposes of this example, we will add a test for the
``pcmk_acl_required()`` function in ``lib/common/acls.c``.  At the time of this
documentation being written, no tests existed for that source file, so there
is no ``lib/common/tests/acls`` directory.

* Add to ``AC_CONFIG_FILES`` in the top-level ``configure.ac`` file so the build
  process knows to use directory we're about to create.  That variable would
  now look something like:

  .. code-block:: none

     dnl Other files we output
     AC_CONFIG_FILES(Makefile                                            \
                     ...
                     lib/common/tests/Makefile                           \
                     lib/common/tests/acls/Makefile                      \
                     lib/common/tests/agents/Makefile                    \
                     ...
     )

* cd into ``lib/common/tests``
* Add to the ``SUBDIRS`` variable in ``Makefile.am``, making it something like:

  .. code-block:: none

     SUBDIRS = agents acls cmdline flags operations strings utils xpath results

* Create a new ``acls`` directory, copying the ``Makefile.am`` from some other
  directory.  At this time, each ``Makefile.am`` is largely boilerplate with
  very little that needs to change from directory to directory.
* cd into ``acls``
* Get rid of any existing values for ``check_PROGRAMS`` and set it to
  ``pcmk_acl_required_test`` like so:

  .. code-block:: none

     check_PROGRAMS = pcmk_acl_required_test

* Double check that the following includes are at the top of ``Makefile.am``:

  .. code-block:: none

     include $(top_srcdir)/mk/common.mk
     include $(top_srcdir)/mk/tap.mk
     include $(top_srcdir)/mk/unittest.mk

* If necessary, settings from those includes can be overridden like so:

  .. code-block:: none

     AM_TESTS_ENVIRONMENT += PCMK_CTS_CLI_DIR=$(top_srcdir)/cts/cli
     AM_CPPFLAGS += -I$(top_srcdir)
     LDADD += $(top_builddir)/lib/pengine/libpe_status_test.la

* Follow the steps in `Testing a new function in an already testable source file`_
  to create the new ``pcmk_acl_required_test.c`` file.

Testing a function in a library without tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adding a test case for a function in a library that doesn't have any test cases
to begin with is only slightly more complicated.  In general, the steps are the
same as for the previous section, except with an additional layer of directory
creation.

For the purposes of this example, we will add a test case for the
``lrmd_send_resource_alert()`` function in ``lib/lrmd/lrmd_alerts.c``.  Note that this
may not be a very good function or even library to write actual unit tests for.

* Add to ``AC_CONFIG_FILES`` in the top-level ``configure.ac`` file so the build
  process knows to use directory we're about to create.  That variable would
  now look something like:

  .. code-block:: none

     dnl Other files we output
     AC_CONFIG_FILES(Makefile                                            \
                     ...
                     lib/lrmd/Makefile                                   \
                     lib/lrmd/tests/Makefile                             \
                     lib/services/Makefile                               \
                     ...
     )

* cd into ``lib/lrmd``
* Create a ``SUBDIRS`` variable in ``Makefile.am`` if it doesn't already exist.
  Most libraries should not have this variable already.

  .. code-block:: none

     SUBDIRS = tests

* Create a new ``tests`` directory and add a ``Makefile.am`` with the following
  contents:

  .. code-block:: none

     SUBDIRS = lrmd_alerts

* Follow the steps in `Testing a function in a source file without tests`_ to create
  the rest of the new directory structure.

* Follow the steps in `Testing a new function in an already testable source file`_
  to create the new ``lrmd_send_resource_alert_test.c`` file.

Adding to an existing test case
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If all you need to do is add additional test cases to an existing file, none of
the above work is necessary.  All you need to do is find the test source file
with the name matching your function and add to it and then follow the
instructions in `Writing the test`_.

Writing the test
________________

A test case file contains a fair amount of boilerplate.  For this reason, it's
usually easiest to just copy an existing file and adapt it to your needs.  However,
here's the basic structure:

.. code-block:: c

   /*
    * Copyright 2021 the Pacemaker project contributors
    *
    * The version control history for this file may have further details.
    *
    * This source code is licensed under the GNU Lesser General Public License
    * version 2.1 or later (LGPLv2.1+) WITHOUT ANY WARRANTY.
    */

   #include <crm_internal.h>

   #include <crm/common/unittest_internal.h>

   /* Put your test-specific includes here */

   /* Put your test functions here */

   PCMK__UNIT_TEST(NULL, NULL,
                   /* Register your test functions here */)

Each test-specific function should test one aspect of the library function,
though it can include many assertions if there are many ways of testing that
one aspect.  For instance, there might be multiple ways of testing regular
expression matching:

.. code-block:: c

   static void
   regex(void **state) {
       const char *s1 = "abcd";
       const char *s2 = "ABCD";

       assert_true(pcmk__strcmp(NULL, "a..d", pcmk__str_regex) < 0);
       assert_true(pcmk__strcmp(s1, NULL, pcmk__str_regex) > 0);
       assert_int_equal(pcmk__strcmp(s1, "a..d", pcmk__str_regex), 0);
   }

Each test-specific function must also be registered or it will not be called.
This is done with ``cmocka_unit_test()`` in the ``PCMK__UNIT_TEST`` macro:

.. code-block:: c

   PCMK__UNIT_TEST(NULL, NULL,
                   cmocka_unit_test(regex))

Most unit tests do not require a setup and teardown function to be executed
around the entire group of tests.  On occassion, this may be necessary.  Simply
pass those functions in as the first two parameters to ``PCMK__UNIT_TEST``
instead of using NULL.

Assertions
__________

In addition to the `assertions provided by cmocka
<https://api.cmocka.org/group__cmocka__asserts.html>`_, ``unittest_internal.h``
also provides ``pcmk__assert_asserts``. This macro takes an expression and
verifies that the expression aborts due to a failed call to ``pcmk__assert()``
or some other similar function.  It can be used like so:

.. code-block:: c

   static void
   null_input_variables(void **state)
   {
       long long start, end;

       pcmk__assert_asserts(pcmk__parse_ll_range("1234", NULL, &end));
       pcmk__assert_asserts(pcmk__parse_ll_range("1234", &start, NULL));
   }

Here, ``pcmk__parse_ll_range`` expects non-NULL for its second and third
arguments.  If one of those arguments is NULL, ``pcmk__assert()`` will fail and
the program will abort.  ``pcmk__assert_asserts`` checks that the code would
abort and the test passes.  If the code does not abort, the test fails.


Running
_______

If you had to create any new files or directories, you will first need to run
``./configure`` from the top level of the source directory.  This will regenerate
the Makefiles throughout the tree.  If you skip this step, your changes will be
skipped and you'll be left wondering why the output doesn't match what you
expected.

To run the tests, simply run ``make check`` after previously building the source
with ``make``.  The test cases in each directory will be built and then run.
This should not take long.  If all the tests succeed, you will be back at the
prompt.  Scrolling back through the history, you should see lines like the
following:

.. code-block:: none

    PASS: pcmk__strcmp_test 1 - same_pointer
    PASS: pcmk__strcmp_test 2 - one_is_null
    PASS: pcmk__strcmp_test 3 - case_matters
    PASS: pcmk__strcmp_test 4 - case_insensitive
    PASS: pcmk__strcmp_test 5 - regex
    ============================================================================
    Testsuite summary for pacemaker 2.1.0
    ============================================================================
    # TOTAL: 33
    # PASS:  33
    # SKIP:  0
    # XFAIL: 0
    # FAIL:  0
    # XPASS: 0
    # ERROR: 0
    ============================================================================
    make[7]: Leaving directory '/home/clumens/src/pacemaker/lib/common/tests/strings'

The testing process will quit on the first failed test, and you will see lines
like these:

.. code-block:: none

   PASS: pcmk__scan_double_test 3 - trailing_chars
   FAIL: pcmk__scan_double_test 4 - typical_case
   PASS: pcmk__scan_double_test 5 - double_overflow
   PASS: pcmk__scan_double_test 6 - double_underflow
   ERROR: pcmk__scan_double_test - exited with status 1
   PASS: pcmk__starts_with_test 1 - bad_input
   ============================================================================
   Testsuite summary for pacemaker 2.1.0
   ============================================================================
   # TOTAL: 56
   # PASS:  54
   # SKIP:  0
   # XFAIL: 0
   # FAIL:  1
   # XPASS: 0
   # ERROR: 1
   ============================================================================
   See lib/common/tests/strings/test-suite.log
   Please report to users@clusterlabs.org
   ============================================================================
   make[7]: *** [Makefile:1218: test-suite.log] Error 1
   make[7]: Leaving directory '/home/clumens/src/pacemaker/lib/common/tests/strings'

The failure is in ``lib/common/tests/strings/test-suite.log``:

.. code-block:: none

   ERROR: pcmk__scan_double_test
   =============================

   1..6
   ok 1 - empty_input_string
   PASS: pcmk__scan_double_test 1 - empty_input_string
   ok 2 - bad_input_string
   PASS: pcmk__scan_double_test 2 - bad_input_string
   ok 3 - trailing_chars
   PASS: pcmk__scan_double_test 3 - trailing_chars
   not ok 4 - typical_case
   FAIL: pcmk__scan_double_test 4 - typical_case
   # 0.000000 != 3.000000
   # pcmk__scan_double_test.c:80: error: Failure!
   ok 5 - double_overflow
   PASS: pcmk__scan_double_test 5 - double_overflow
   ok 6 - double_underflow
   PASS: pcmk__scan_double_test 6 - double_underflow
   # not ok - tests
   ERROR: pcmk__scan_double_test - exited with status 1

At this point, you need to determine whether your test case is incorrect or
whether the code being tested is incorrect.  Fix whichever is wrong and continue.


Fuzz Testing
############

Pacemaker is integrated with the
`OSS-Fuzz <https://github.com/google/oss-fuzz>`_ project. OSS-Fuzz calls
selected Pacemaker APIs with random argument values to catch edge cases that
might be missed by other forms of testing.

The OSS-Fuzz project has a contact address for Pacemaker in
projects/pacemaker/project.yaml that will receive bug reports. The address must
have been used to commit to Pacemaker, and should be tied to a Google account.

Open reports that aren't security-related can be seen at `OSS-Fuzz testcases
<https://oss-fuzz.com/testcases?project=pacemaker&open=yes>`_.


Fuzzers
_______

Each fuzz-tested library has a fuzzers subdirectory (for example,
``lib/common/fuzzers``). That directory has a file for each fuzzed source file,
named the same except ending in ``_fuzzer.c`` (for example,
``lib/common/fuzzers/strings_fuzzer.c`` has fuzzing for
``lib/common/strings.c``). Those files are not built or distributed as part of
Pacemaker but are used by OSS-Fuzz (see ``projects/pacemaker/build.sh`` in the
OSS-Fuzz repository).

By default, fuzzing uses `libFuzzer <https://llvm.org/docs/LibFuzzer.html>`_.
Only Pacemaker APIs that accept any input and do not exit can be fuzzed.
Ideally, fuzzed functions will not modify global state or vary code paths by
anything other than the fuzzed input (such as environment variable values,
date/time, etc.).


Local Fuzzing
_____________

You can use OSS-Fuzz locally to run fuzz testing or reproduce issues reported
by OSS-Fuzz.

To prep a test host:

1. If podman is installed, it will conflict with Docker, so remove it first.
   Example for RHEL-like OSes:

   * ``dnf remove runc``

1. Install and start Docker. Example for RHEL-like OSes:

   * ``dnf config-manager --add-repo
     https://download.docker.com/linux/rhel/docker-ce.repo``
   * ``dnf install docker-ce docker-ce-cli containerd.io docker-buildx-plugin
     docker-compose-plugin``
   * ``usermod -a -G docker $USER``

2. Clone the OSS-Fuzz repository:

   * ``cd`` to wherever you want to put it
   * ``git clone https://github.com/google/oss-fuzz.git``
   * ``cd oss-fuzz``

3. Specify the Pacemaker source you want to test:

   * Edit ``projects/pacemaker/Dockerfile`` and replace the last ``git clone``
     with the source that you want to test. For example, if you have a branch
     ``my-fuzzing-branch`` that you've pushed to your GitHub account, you could
     use: ``git clone -b my-fuzzing-branch --single-branch --depth 1
     https://github.com/$USER/pacemaker``.

To fuzz the code:

1. Ensure Docker is running:

   * ``systemctl start docker``

2. Build the necessary Docker containers:

   * ``python3 infra/helper.py build_image pacemaker``

3. Build the fuzzers. Choose a sanitizer (for example, ``SANITIZER=address``).
   There are three possible sanitizers: address, memory, and undefined. The
   memory sanitizer requires special preparation and is generally not used. If
   you are reproducing an OSS-Fuzz-reported issue, the issue will list the
   sanitizer that was used.

   * ``python3 infra/helper.py build_fuzzers --sanitizer $SANITIZER pacemaker``

4. Ensure the build succeeded (use the same sanitizer as the previous step):

   * ``python3 infra/helper.py check_build --sanitizer $SANITIZER pacemaker``

5. If you want to run fuzzing yourself, choose a fuzzer (for example,
   ``FUZZER=iso8601_fuzzer``). Create a temporary directory for the fuzzer's
   outputs, then run the fuzzing command, which will fuzz for 25 seconds then
   time out:

   * ``rm -rf /tmp/corpus >/dev/null 2>&/dev/null``
   * ``mkdir /tmp/corpus``
   * ``python3 infra/helper.py run_fuzzer --corpus-dir=/tmp/corpus pacemaker
     $FUZZER``
   * This can be repeated with different fuzzers. The ``build_fuzzers`` step
     can also be repeated with a different sanitizer, and the fuzzers tested
     again.

6. If you want to reproduce an OSS-Fuzz-reported issue, make a note of the
   fuzzer that was used (``$FUZZER`` in this example) and download the provided
   reproducer test case file (``$TESTCASE`` in this example), then run:

   * ``python3 infra/helper.py reproduce pacemaker $FUZZER $TESTCASE``

For details, see the `OSS-Fuzz documentation
<https://google.github.io/oss-fuzz/getting-started/new-project-guide/#testing-locally>`_.


Code Coverage
#############

Figuring out what needs unit tests written is the purpose of a code coverage tool.
The Pacemaker build process uses ``lcov`` and special make targets to generate
an HTML coverage report that can be inspected with any web browser.

To start, you'll need to install the ``lcov`` package which is included in most
distributions.  Next, reconfigure the source tree:

.. code-block:: none

   $ ./configure --with-coverage

Then run ``make -C devel coverage``.  This will do the same thing as ``make check``,
but will generate a bunch of intermediate files as part of the compiler's output.
Essentially, the coverage tools run all the unit tests and make a note if a given
line if code is executed as a part of some test program.  This will include not
just things run as part of the tests but anything in the setup and teardown
functions as well.

Afterwards, the HTML report will be in ``coverage/index.html``.  You can drill down
into individual source files to see exactly which lines are covered and which are
not, which makes it easy to target new unit tests.  Note that sometimes, it is
impossible to achieve 100% coverage for a source file.  For instance, how do you
test a function with a return type of void that simply returns on some condition?

Note that Pacemaker's overall code coverage numbers are very low at the moment.
One reason for this is the large amount of code in the ``daemons`` directory that
will be very difficult to write unit tests for.  For now, it is best to focus
efforts on increasing the coverage on individual libraries.

Additionally, there is a ``coverage-cts`` target that does the same thing but
instead of testing ``make check``, it tests ``cts/cts-cli``.  The idea behind this
target is to see what parts of our command line tools are covered by our regression
tests.  It is probably best to clean and rebuild the source tree when switching
between these various targets.


Debugging
#########

gdb
___

If you use ``gdb`` for debugging, some helper functions are defined in
``devel/gdbhelpers``, which can be given to ``gdb`` using the ``-x`` option.

From within the debugger, you can then invoke the ``pcmk`` command that
will describe the helper functions available.
