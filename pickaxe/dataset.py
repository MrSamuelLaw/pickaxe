import csv
from math import floor
from operator import setitem
from com.inductiveautomation.ignition.common import BasicDataset



def _partition(data, low, high, key):
	"""partion algorithm that partitions 
	data with all the rows greater than the index
	on the right and all the rows less than the index
	on the left.
	"""
	
	# utility functions for getting and setting rows
	getRow = lambda rowIdx: [data[i][rowIdx] for i in range(len(data))]
	setRow = lambda rowIdx, row: [setitem(data[i], rowIdx, x) for i, x in enumerate(row)]
	
	# pivot will be the middle value, then moved to the end
	pivotIdx = low + int(floor((high-low)/2))
	pivot = getRow(pivotIdx)
	setRow(pivotIdx, getRow(high))
	setRow(high, pivot)
	
	# traverse from the outside in swapping idx 
	lowIdx = low - 1
	for highIdx in range(low, high):
		highItem = getRow(highIdx)
		if key(highItem) < key(pivot):
			lowIdx = lowIdx + 1
			temp = getRow(lowIdx)
			setRow(lowIdx, getRow(highIdx))
			setRow(highIdx, temp)
	
	# put the pivot back into it's spot
	temp = getRow(lowIdx + 1)
	setRow(lowIdx + 1, pivot)
	setRow(high, temp)
	
	# return the new pivot index
	return lowIdx + 1
	

def quickSort(data, low, high, key):
	"""Implements a quicksort algorithm on a data structure
	that has data by column.
	
	Args:
		data: List[List], each nested listed is a column.
		low: int, low index to sort from.
		high: int, high index to sort from.
		key: callable, function that takes a row and returns a tuple. 
	"""
	
	if low < high:
		# Find pivot element such that
		# element smaller than pivot are on the left
		# element greater than pivot are on the right
		pi = _partition(data, low, high, key)
		
		# Recursive call on the left of pivot
		quickSort(data, low, pi - 1, key)
		
		# Recursive call on the right of pivot
		quickSort(data, pi + 1, high, key)


def sort(ds, key, method='quickSort', reverse=False):
	"""Sorts a dataset in place using a key.
	Args:
		ds: BasicDataset
		key: int | callable, int | function that takes a row and returns a tuple.
		reverse: bool, optional, defaults to False, reverses the order of the returned dataset
	"""
	ds = system.dataset.filterColumns(ds, range(ds.getColumnCount()))
	isort(ds, key=key, method=method, reverse=reverse)
	return ds
	

def isort(ds, key, method='quickSort', reverse=False):
	"""Sorts a dataset in place using a key.
	Args:
		ds: BasicDataset
		key: int | callable, int | function that takes a row and returns a tuple. 
	"""
	
	# adapt a column index
	if type(key) is int:
		f = lambda row: (row[key],)
	else:
		f = key
		
	# use the sort method of choice
	if method == 'quickSort':
		quickSort(ds.getData(), 0, ds.getRowCount() - 1, f)
	
	# reverse if needed
	if reverse:
		data = ds.getData()
		for i in range(ds.getColumnCount()):
			data[i][:] = data[i][::-1]


def groupBy(dataset, bucket_by, column_index):
	"""Function that takes a dataset and groups
	rows using the bucket_by function and the column index
	Args:
		dataset: system.dataset
		bucket_by: function(val) -> hashible type
		column_index: column where each row will have bucket_by called on it
	returns: 
		a dictionary where the keys are the unique values from the 
		transformed column and the values are lists of indexes where the key matched in the dataset
	"""
	# grab the unique values
	vector = dataset.getColumnAsList(column_index)
	vector = [bucket_by(val) for val in vector]
	unique_vector = set(vector)
	
	# sort into bins
	results = {}
	for uv in unique_vector:
		results[uv] = [i for i, v in enumerate(vector) if v == uv]
	return results
	

def csvToDataSet(lines, types, delimiter=',', headers=None, dialect=None):
	"""Parses lines of text into a dataset
	args:
		lines: List[str]: Lines of text to be split into a csv.
		types: List[types]: Types for each column in csv. 
							Must be a able to convert a string to the type for example int(s) -> int and
							must be one of the types allowed for datasets in ignition to avoid serialization errors
		sep: [optional] str:  Seperator for each value in the csv, defaults to ","
		headers: [optional] List[str]: Headers for the dataset, defaults to row zero of the csv
	returns:
		Returns a dataset 
	"""
	data = list(csv.reader(lines, delimiter, dialect=dialect))
	headers = headers if headers is not None else data.pop(0)
	
	# transpose for column operations
	data = list(zip(*data))
	for i, t in enumerate(types):
		def default_func(s):
			return t(s) if s else None
		def number_func(s):
			s = s.replace(',','')
			return t(s) if s else None
		f = number_func if isinstance(t, tuple(type(t) for t in (float, int))) else default_func
		data[i] = [f(v) for v in data[i]]
		
	# transpose for row operations again
	data = list(zip(*data))
		
	# explicitly set the columnTypes
	ds = system.dataset.toDataSet(headers, data)
	ds.setColumnTypes(types)
	return ds
	
	
def distinct(ds):
	"""Returns a subset of the dataset containing
	only the unique rows in the dataset
	args:
		ds: dataset
	returns:
		dataset
	"""
	data = list({r for r in zip(*ds.getData().tolist())})
	ds = system.dataset.toDataSet(list(ds.getColumnNames()), data)
	return ds


def filterRows(dataset, filter_func):
	"""Returns a new filtered dataset
	Args: 
		dataset: dataset.
		filter_func: callable -> bool: Function used to filter the dataset
	Returns:
		dataset
    Example:
        animalDS = system.dataset.toDataSet(['Animal'], [['cat'], ['dog'], ['snake']])
		searchString = 'a'
		def like(r):
            return searchString in r[0]
		filterRows(animalDS, like)
		
		result : Dataset [2R x 1C]		
	"""
	data = dataset.getData()
	idx = [i for i, r in enumerate(list(zip(*data))) if not filter_func(r)]
	dataset = system.dataset.deleteRows(dataset, idx)
	return dataset


def ifilterRows(dataset, filter_func):
	"""filters a dataset by row in place, meaning it effects the dataset directly
	Args: 
		ds: dataset.
		filter_func: callable -> bool: Function used to filter the dataset
	Returns:
		dataset
	"""
	data = dataset.getData()
	idx = [i for i, r in enumerate(list(zip(*data))) if not filter_func(r)]
	def pop(i, j):
		for k in range(len(data)):
			data[k] = data[k][:i-j] + data[k][i-j + 1:]
	[pop(i, j) for j, i in enumerate(idx)]
	dataset.setDataDirectly(data)
	return dataset
	

def join(left, right, how='full', on=lambda leftRow, rightRow: True, leftSuffix='_left', rightSuffix='_right'):
	"""Joins two datasets into one dataset using a method that defaults to a full join.
	Args:
		left: BasicDataset, left dataset.
		right: BasicDataset, right dataset.
		how: one of 'full' | 'left' | 'right'.
		on: Callable, used to compute the row to return, should return true if the rows should be joined else false.
		leftSuffix: str, suffix to append to avoid column name collisions, defaults to _left.
		rightSuffix: str, suffix to append to avoid column name collisions, default to _right.
	Returns: BasicDataset
	
	Example:
		...
		# joins matching on all columns
		dsFullJoin = join(left, right)
		dsInnerJoin = join(left, right, on=lambda leftRow, rightRow: leftRow == rightRow)
		dsLeftJoin = join(left, right, how='left', on=lambda leftRow, rightRow: leftRow == rightRow)
		dsRightJoin = join(left, right, how='right', on=lambda leftRow, rightRow: leftRow == rightRow)
		
		# join on primary keys
		leftPkIdx
		rightPkIdx
		dsInnerJoin = join(left, right, on=lambda leftRow, rightRow: leftRow[leftPkIdx] == rightRow['rightPkIdx'])
	"""
	
	# validte the how
	if how not in ('full', 'left', 'right'):
		msg = 'how must be one of "full" | "right" | "right", not {}'.format(how)
		raise ValueError(msg)
	
	# parse the headers
	leftHeaders = left.getColumnNames()
	rightHeaders = right.getColumnNames()
	cleanedLeftHeaders = [h + leftSuffix if h in rightHeaders else h for h in leftHeaders]
	cleanedRightHeaders = [h + rightSuffix if h in leftHeaders else h for h in rightHeaders]
	headers = cleanedLeftHeaders + cleanedRightHeaders
	
	# perform the join
	data = []
	
	# short circuit evaluation for a null resultent
	if (left.getRowCount() != 0) and (right.getRowCount() != 0):
		leftData = left.getData()
		leftColumnCount = len(leftData)
		rightData = right.getData()
		rightColumnCount = len(rightData)
		for i in range(len(leftData[0])):
			rows = []
			for j in range(len(rightData[0])):
				leftRow = [leftData[c][i] for c in range(leftColumnCount)]
				rightRow = [rightData[c][j] for c in range(rightColumnCount)]
				if on(leftRow, rightRow):
					row = leftRow + rightRow
					rows.append(row)
			
			# implement the left or right join
			if not rows:
				if how == 'left':
					row = leftRow + [None]*len(rightRow)
					rows.append(row)
				elif how == 'right':
					row = [None]*len(leftRow) + rightRow
					rows.append(row)
			
			# append rows to the dataset
			data.extend(rows)
	
	# return the joined dataset
	types = list(left.getColumnTypes()) + list(right.getColumnTypes())
	data = list(zip(*data))
	ds = BasicDataset(headers, types, data)
	return ds


def diff(left, right, mode='distinct'):
	"""Returns all of the elements in the left dataset that are not in the
	right dataset. If mode is set to 'distinct' than the difference is computed
	using the unique rows between the left and right datasets. if the mode
	is set to 'all', the difference is computed using the count and well as the value
	of the row.
	The function is based on mysql's "except" set operation
	
	Args:
		left: BasicDataset, left side of the difference
		right: BasicDataset, right side of the difference
		mode: 'distinct' | 'all', optional, defaults to 'distinct', see mysql docs for inspiration
	
	Returns:
		Basic Dataset
	
	Examples:
		# when using 'distinct', the duplicate (3, 4) in a don't matter
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
		for row in zip(*diff(b, a, mode='distinct').getData()):
			print(row)
		>>>
			(5, 6)
		
		# when using 'all' the duplicate 3, 4 does matter
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
		for row in zip(*diff(b, a, mode='all').getData()):
			print(row)
		>>>
			(3, 4)
			(5, 6)
	"""
	leftRows = list(zip(*left.getData()))
	rightRows = list(zip(*right.getData()))
	diff = []
	for lrow in leftRows:
		if lrow not in rightRows:
			diff.append(lrow)
		elif mode == 'all':
			rightRows.remove(lrow)
	return system.dataset.toDataSet(list(left.getColumnNames()), diff)


def _fill(dataset, getIdx, columns=None):
	
	# create a copy of the data
	ds = system.dataset.filterColumns(dataset, range(dataset.getColumnCount()))
	
	# cast strings to column index or create a list of all column indices.
	if columns is not None:
		idxs = [ds.getColumnIndex(v) if isinstance(v, str) else v for v in columns]
	else:
		idxs = [i for i in range(ds.getColumnCount())]
	
	# apply the fill
	data = ds.getData()
	for col in data:
		previousValue = None
		for i in range(len(col)):
			idx = getIdx(i)
			val = col[idx]
			if val is not None:
				previousValue = val
			else:
				col[idx] = previousValue
	
	# return the dataset
	return ds


def ffill(dataset, columns=None):
	"""Method that fills a dataset from top to bottom using the previous
	non None to fill in None values. The dataset returned is a copy of the
	dataset passed in with the fill applied.
	
	Args:
		dataset: BasicDataset,
		columns: list[str, int] | None, optional, columns to fill, if omitted fills all columns.
				 strings are interpreted as column names, and ints as column index's
	
	Returns: 
		BasicDataset
	"""
	return _fill(
		dataset, 
		lambda i: i,
		columns
	)


def bfill(dataset, columns=None):
	"""Method tha fills a dataset from bottom to top using the previous
	non None value to fill in nones.
	
	Args:
		dataset: BasicDataset,
		columns: list[str, int] | None, optional, columns to fill, if omitted fills all columns.
				 strings are interpreted as column names, and ints as column index's
	
	Returns: 
		BasicDataset
	"""
	maxIdx = dataset.getRowCount() - 1
	return _fill(
		dataset, 
		lambda i: maxIdx - i,
		columns
	)
