from __future__ import print_function
import time
import unittest
from pickaxe import tag
from pickaxe.util import getScope


@unittest.skipIf(getScope() != 'designer', 'test_tag can only be run in designer scope')
class TestTag(unittest.TestCase):

	path = '[default]Dev/Testing/Unit_Testing/Tag/new_tag'

	def setUp(self):
		# creates a fresh tag for testing purposes
		system.tag.deleteTags([self.path])
		tag.createMemoryTag(self.path, 
			tag.TagObjectType.AtomicTag, 
			tag.DataType.Boolean, 
			tag.CollisionPolicy.Overwrite)
		
	def tearDown(self):
		system.tag.deleteTags([self.path])

	def test_canCreateMemoryTag(self):
		# verifies that the new tag created in the setUp call exists and is writable
		system.tag.writeBlocking([self.path], [1])
		self.assertEqual(system.tag.readBlocking([self.path])[0].value, 1)
		
	def test_canReadOpc(self):
		pass  # need to implement
		
	def test_canWriteOpc(self):
		pass  # need to implement
		
	def test_canGetProvider(self):
		provider = tag.getProvider('[default]path/to/tag')
		self.assertEqual(provider, 'default')
		with self.assertRaises(Exception) as ct:
			provider = tag.getProvider('path/to/tag')
		
	
def runTests():
	pickaxe.testing.utils.runTests(TestTag)
