from __future__ import print_function
import sys
import unittest



def runTests(stream=sys.stdout):
	"""Runs the tests from each module
	
	To override the tests returned by the automatic search
	the module can define the load_tests function per the documentation.
	https://docs.python.org/2.7/library/unittest.html
	"""
	
	modules = [
		pickaxe.tests.test_tag,
		pickaxe.jydantic.tests.test_types,
		pickaxe.jydantic.tests.test_core,
		pickaxe.tests.test_dataset,
		pickaxe.tests.test_util
	]
	
	suites = [unittest.TestLoader().loadTestsFromModule(m) for m in modules]
	suite = unittest.TestSuite(suites)
	output = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
	print(output)
	stream.flush()


