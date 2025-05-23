from __future__ import print_function
import sys
import unittest


def runTests(*testClasses, **kwargs):
	"""Test runner that prints the output
	Args:
		testSuite: testCaseClass
		**kwargs: arguments for a TextTestRunner
		
	Example:
		
	"""
	# create the test suite
	suites = [unittest.TestLoader().loadTestsFromTestCase(s) for s in testClasses]
	suite = unittest.TestSuite(suites)
	
	# inject sensible defaults to the test runner
	params = {'stream': sys.stdout, 'verbosity': 2}
	params.update(kwargs)
	
	# print the test output
	output = unittest.TextTestRunner(**params).run(suite)
	print(output)
	sys.stdout.flush()
	
	

		
	
	