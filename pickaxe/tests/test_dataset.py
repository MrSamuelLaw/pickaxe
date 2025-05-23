from __future__ import print_function
import unittest
from pickaxe import dataset


class TestDataset(unittest.TestCase):
	
	def test_csvToDataSet(self):
		lines = [
			'value,name,id',
			'1,foo,A1', 
			',,']
		types = [int, unicode, unicode]
		ds = dataset.csvToDataSet(lines, types)
		pds = system.dataset.toPyDataSet(ds) 
		# test headers
		expected = ['value', 'name', 'id']
		result = system.dataset.getColumnHeaders(pds)
		self.assertEqual(expected, result)
		# test row 0 types
		expected = types
		result1 = [type(v) for v in pds[0]]
		self.assertEqual(expected, result1)
		# test row 1 types
		expected = [type(None)]*3
		result = [type(v) for v in pds[1]]
		self.assertEqual(expected, result)
		
	def test_join(self):
		# left join
		left = system.dataset.toDataSet(['a', 'b'], [[1, 2], [3, 4]])
		right = system.dataset.toDataSet(['a', 'd'], [[1, 2], [3, 4]])
		joined = dataset.join(left, right)
		self.assertEqual(joined.getRowCount(), 4)
		self.assertEqual(joined.getColumnNames(), ['a_left', 'b', 'a_right', 'd'])
		
		# inner join
		left = system.dataset.toDataSet(['a', 'b'], [[1, 2], [3, 4]])
		right = system.dataset.toDataSet(['a', 'd'], [[1, 2], [3, 4]])
		joined = dataset.join(left, right, on=lambda leftRow, rightRow: leftRow == rightRow)
		self.assertEqual(joined.getRowCount(), 2)
		
		# left join
		left = system.dataset.toDataSet(['a', 'b'], [[1, 2], [3, 4]])
		right = system.dataset.toDataSet(['a', 'd'], [[1, 2], [0, 0]])
		joined = dataset.join(left, right, how='left', on=lambda leftRow, rightRow: leftRow == rightRow)
		self.assertEqual(joined.getRowCount(), 2)
		self.assertTrue(all([joined.getValueAt(*t) is None for t in [(1, 2), (1, 3)]]))
		
		# right join
		left = system.dataset.toDataSet(['a', 'b'], [[1, 2], [3, 4]])
		right = system.dataset.toDataSet(['a', 'd'], [[1, 2], [0, 0]])
		joined = dataset.join(left, right, how='right', on=lambda leftRow, rightRow: leftRow == rightRow)
		self.assertEqual(joined.getRowCount(), 2)
		self.assertTrue(all([joined.getValueAt(*t) is None for t in [(1, 0), (1, 1)]]))
	
	def test_diff(self):
		a = system.dataset.toDataSet(('a', 'b'), [
			[1, 2],
			[3, 4]
		])
		
		b = system.dataset.toDataSet(('c', 'd'), [
			[1, 2],
			[3, 4],
			[3, 4],
			[5, 6]
		])
		# test distinct
		rows = list(zip(*pickaxe.dataset.diff(b, a).getData()))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0], (5, 6))
		# test all
		rows = list(zip(*pickaxe.dataset.diff(b, a, mode='all').getData()))
		self.assertEqual(len(rows), 2)
		self.assertEqual(rows, [(3, 4), (5, 6)])
	
	def test_fill(self):
		# test ffill
		a = system.dataset.toDataSet(('a', 'b'), [
			[1, 2],
			[None, None],
			[3, 4],
			[None, None]
		])
		a = pickaxe.dataset.ffill(a)
		self.assertEqual(a.getValueAt(1, 0), 1)
		self.assertEqual(a.getValueAt(1, 1), 2)
		self.assertEqual(a.getValueAt(2, 0), 3)
		self.assertEqual(a.getValueAt(3, 1), 4)
		
		# test bfill
		a = system.dataset.toDataSet(('a', 'b'), [
			[None, None],
			[1, 2],
			[None, None],
			[3, 4]
		])
		a = pickaxe.dataset.bfill(a)
		self.assertEqual(a.getValueAt(1, 0), 1)
		self.assertEqual(a.getValueAt(1, 1), 2)
		self.assertEqual(a.getValueAt(2, 0), 3)
		self.assertEqual(a.getValueAt(3, 1), 4)
		
		# test an all null dataset
		a = system.dataset.toDataSet(('a', 'b'), [
			[None, None],
			[None, None],
			[None, None],
			[None, None]
		])
		a = pickaxe.dataset.bfill(a)
		self.assertEqual(a.getColumnAsList(0), [None]*4)
		self.assertEqual(a.getColumnAsList(1), [None]*4)


def runTests():
	pickaxe.testing.utils.runTests(TestDataset)
	
