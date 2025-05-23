from __future__ import print_function
import unittest
from pickaxe import db


class Testdb(unittest.TestCase):

	def removeWhiteSpace(self, query):
		query = query.splitlines()
		query = '\r\n'.join([s.strip() for s in query])
		return query
	
	def test_canSanitizeQuery(self):
		# basic case
		query = """
			select *
			from shingle_instantiation_log
			where instantiatedTimestamp between :start and :end
			limit 1
		"""
		query = self.removeWhiteSpace(query)
		sanitized, keys = db.makePrepQuery(query)
		self.assertEqual(keys, ['start', 'end'])
		
		expected = """
			select *
			from shingle_instantiation_log
			where instantiatedTimestamp between ? and ?
			limit 1
		"""
		expected = self.removeWhiteSpace(expected)
		self.assertEqual(sanitized, expected)
		
		# case with underscores
		query = """
			select *
			from shingle_instantiation_log
			where instantiatedTimestamp between :start_ and :end_
			limit 1
		"""
		query = self.removeWhiteSpace(query)
		sanitized, keys = db.makePrepQuery(query)
		self.assertEqual(keys, ['start_', 'end_'])
		self.assertEqual(sanitized, expected)
		
		# case with numbers
		query = """
			select *
			from shingle_instantiation_log
			where instantiatedTimestamp between :start1 and :end1
			limit 1
		"""
		query = self.removeWhiteSpace(query)
		sanitized, keys = db.makePrepQuery(query)
		self.assertEqual(keys, ['start1', 'end1'])
		self.assertEqual(sanitized, expected)
		
		# case with all 3
		query = """
			select *
			from shingle_instantiation_log
			where instantiatedTimestamp between :start_1_ and :end_1_
			limit 1
		"""
		query = self.removeWhiteSpace(query)
		sanitized, keys = db.makePrepQuery(query)
		self.assertEqual(keys, ['start_1_', 'end_1_'])
		self.assertEqual(sanitized, expected)
		
	def test_doesNotFailWithDatetimeLiterals(self):
		# case with all 3
		query = """
			select
				date_format(from_unixtime(sil.instantiatedTimestamp / 1E+6), '%Y-%m-%d %H:00:00') as `datetime`,
				srel.eExitLocation
			from 
				shingle_instantiation_log sil 
				left join shingle_rdi_entry_log srel on srel.serialCode = sil.serialCode
			where 
				sil.instantiatedTimestamp between unix_timestamp(:startTime)*1E+6 and unix_timestamp(:endTime)*1E+6
		"""
		query = self.removeWhiteSpace(query)
		
		expected = """
			select
				date_format(from_unixtime(sil.instantiatedTimestamp / 1E+6), '%Y-%m-%d %H:00:00') as `datetime`,
				srel.eExitLocation
			from 
				shingle_instantiation_log sil 
				left join shingle_rdi_entry_log srel on srel.serialCode = sil.serialCode
			where 
				sil.instantiatedTimestamp between unix_timestamp(?)*1E+6 and unix_timestamp(?)*1E+6
		"""
		expected = self.removeWhiteSpace(expected)
		
		sanitized, keys = db.makePrepQuery(query)
		self.assertEqual(keys, ['startTime', 'endTime'])
		self.assertEqual(sanitized, expected)
		
	def formatLines(self, s):
		s = '\n'.join((l.strip() for l in s.splitlines()))
		return s
		
	def test_canBuildBatchedQueryWithSingleInjection(self):
		query = """
			select foo
			from bar
			where baz in ({})
		"""
		injection = ':value'
		items = [{'value': i} for i in range(5)]
		query , params = db.buildBatchedQuery(query, injection, items)
		expected = """
			select foo
			from bar
			where baz in (:value0, :value1, :value2, :value3, :value4)
		"""
		actual, expected = self.formatLines(query), self.formatLines(expected)
		self.assertEqual(actual, expected)
		
	def test_canBuildBatchedQueryWithMultiInjection(self):
		query = """
			select foo
			from bar
			where 
				baz in ({})
				and fiz not in ({})
		"""
		injections = [':value', ':qty']
		items = [{'value': i, 'qty': i} for i in range(5)]
		query , params = db.buildBatchedQuery(query, injections, items)
		expected = """
			select foo
			from bar
			where 
				baz in (:value0, :value1, :value2, :value3, :value4)
				and fiz not in (:qty0, :qty1, :qty2, :qty3, :qty4)
		"""
		actual, expected = self.formatLines(query), self.formatLines(expected)
		self.assertEqual(actual, expected)
		
	def test_canBuildBatchedQueryWithSingleIndexedInjection(self):
		query = """
			select foo
			from bar
			where 
				baz in ({0})
				and fiz not in ({0})
		"""
		injection = ':value'
		items = [{'value': i} for i in range(5)]
		query , params = db.buildBatchedQuery(query, injection, items)
		expected = """
			select foo
			from bar
			where 
				baz in (:value0, :value1, :value2, :value3, :value4)
				and fiz not in (:value0, :value1, :value2, :value3, :value4)
		"""
		actual, expected = self.formatLines(query), self.formatLines(expected)
		self.assertEqual(actual, expected)
		
	def test_canBuildBatchedQueryWithMultiIndexedInjection(self):
		query = """
			select foo
			from bar
			where 
				baz in ({0})
				and fiz not in ({1})
		"""
		injections = [':value', ':qty']
		items = [{'value': i, 'qty': i} for i in range(5)]
		query , params = db.buildBatchedQuery(query, injections, items)
		expected = """
			select foo
			from bar
			where 
				baz in (:value0, :value1, :value2, :value3, :value4)
				and fiz not in (:qty0, :qty1, :qty2, :qty3, :qty4)
		"""
		actual, expected = self.formatLines(query), self.formatLines(expected)
		self.assertEqual(actual, expected)
		
	def test_canBuildBatchedQueryWithSingleKeyedInjection(self):
		query = """
			select foo
			from bar
			where 
				baz in ({x1})
		"""
		injections = {'x1': ':value'}
		items = [{'value': i} for i in range(5)]
		query , params = db.buildBatchedQuery(query, injections, items)
		expected = """
			select foo
			from bar
			where 
				baz in (:value0, :value1, :value2, :value3, :value4)
		"""
		actual, expected = self.formatLines(query), self.formatLines(expected)
		self.assertEqual(actual, expected)
		
	def test_canBuildBatchedQueryWithDuplicateKeyedInjection(self):
		query = """
			select foo
			from bar
			where 
				baz in ({x1})
				and fiz not in ({x1})
		"""
		injections = {'x1': ':value'}
		items = [{'value': i} for i in range(5)]
		query , params = db.buildBatchedQuery(query, injections, items)
		expected = """
			select foo
			from bar
			where 
				baz in (:value0, :value1, :value2, :value3, :value4)
				and fiz not in (:value0, :value1, :value2, :value3, :value4)
		"""
		actual, expected = self.formatLines(query), self.formatLines(expected)
		self.assertEqual(actual, expected)
		
	def test_canBuildBatchedQueryWithMulitKeyedInjection(self):
		query = """
			select foo
			from bar
			where 
				baz in ({x1})
				and fiz not in ({x2})
		"""
		injections = {'x1': ':value', 'x2': ':qty'}
		items = [{'value': i, 'qty': i} for i in range(5)]
		query , params = db.buildBatchedQuery(query, injections, items)
		expected = """
			select foo
			from bar
			where 
				baz in (:value0, :value1, :value2, :value3, :value4)
				and fiz not in (:qty0, :qty1, :qty2, :qty3, :qty4)
		"""
		actual, expected = self.formatLines(query), self.formatLines(expected)
		self.assertEqual(actual, expected)
		
		
		
		
		
def runTests():
	pickaxe.testing.utils.runTests(Testdb)
	