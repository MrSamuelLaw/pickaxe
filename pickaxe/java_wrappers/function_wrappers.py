from java.lang import Runnable
from java.util.function import Function, Supplier



class RunnableWrapper(Runnable):
	"""Python wraper for java.lang.Runnable
	Example:
		...
		def fetch():
			... 
			long running task
			result = foo
			...
			def updateGui():
				...
				table.data = result
				...
				
			system.util.invokeLater(updateGui)	
	
		r1 = RunnableWrapper(fetch)
	""" 
	
	def __init__(self, func):
		self._func = func
		
	def run(self):
		return self._func()
		
		
class SupplierWrapper(Supplier):
	
	def __init__(self, func):
		self._func = func
		
	def get(self):
		return self._func()


class FunctionWrapper(Function):
	"""Python wrapper for java.util.function.Function
	Example:
		f1 = FunctionWrapper(lambda v: v+1)
		f2 = FunctionWrapper(lambda v: v*2)
		
		f3 = f1.andThen(f2)
		f4 = f1.compose(f2)
		f3(1)
		f4(1)
		>>> 4
			3
	"""

	def __init__(self, func):
		"""Python function, that takes a single parameter, to be wrapped
		Args:
			func: callable
		"""
		self._func = func
		
	def __call__(self, value):
		"""Implements the functor pattern so instances can be used like functions
		Args: 
			value: any
		"""
		return self.apply(value)
	
	def apply(self, value):
		"""Calls the wrapped python function with the parameter of value
		Args:
			value: any
		"""
		return self._func(value)
			
	def compose(self, before):
		"""Returns a new composed function, see example for details
		Args:
			before: FunctionWrapper
		"""
		return FunctionWrapper(lambda result: self.apply(before.apply(result)))
	
	def andThen(self, after):
		"""Returns a new composed function, see example for details
		Args:
			after: FunctionWrapper
		"""
		return FunctionWrapper(lambda result: after.apply(self.apply(result)))

	def identity(self, value):
		"""Echos the value
		Args:
			value: any
		"""
		return value