from __future__ import print_function


def setBitAt(value, index, state):
	"""Sets a bit to one or zero at the given index.
	
	Args:
		value: int, integer to be modified
		index: int, position of bit to set to state
		state: bool, True to set bit to 1, False to set bit to 0
	Returns: int
	"""
	if state:
		value = value | (1<<index)
	else:
		value = value & ~(1<<index)
	return value
	
	
def getBitAt(value, index):
	"""Sets a bit to one or zero at the given index.
	
	Args:
		value: int, integer to be modified
		index: int, position of bit to set to state
		state: bool, True to set bit to 1, False to set bit to 0
	Returns: 1 | 0
	"""
	return value>>index & 1
