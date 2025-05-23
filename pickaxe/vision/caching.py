from __future__ import print_function
from functools import wraps
from threading import Lock
from collections import OrderedDict


def _getJComponentKey(jComponent, func):
	"""Function used to generate the key that is used to get/set
	the cacheParams object on the jComponent.
	
	Args:
		jComponent: instance of a JComponent
		func: a function to be cached.
	"""
	return '.'.join((jComponent.name, func.__name__, '__cache'))


def lruCache(event, maxLength=10, maxAge=10000):
	"""Decorator that builds/updates the cache and then
	reads the cache before calling the function each time
	the function is called.
	
	Args:
		event: Event that is used to restrict the cache to the component
		on which the event occurs.
		maxLength: long, optional, defaults to 10, max number of entries allowed in the cache.
		maxAge: long, optional, default to 10,000, max age of an entry in milliseconds before it is invalidated.
	"""
	def buildCache(func):
		"""This function sets up the cacheParams object that 
		contains cache parameters and the actual cache itself which
		is just an OrderedDict from the collections module.
		"""
		jComponent = event.source
		key = _getJComponentKey(jComponent, func)
		cacheParams = jComponent.getClientProperty(key)
		if cacheParams is None:
			cacheParams = {
				'hitCount': 0,
				'missCount': 0,
				'orderedDict': OrderedDict(),
				'lock': Lock()
			}
			jComponent.putClientProperty(key, cacheParams)
		cacheParams.update({
			'maxLength': maxLength,
			'maxAge': maxAge,
		})
		
		@wraps(func)
		def useCache(*args, **kwargs):
			"""This function wraps the target function and will look for the 
			result in the cache before calling the function to retrieve a fresh
			result. This function is thread safe which enables the use of caching
			with asyncPropertyChangeHandler
			"""
			key = '.'.join((jComponent.name, func.__name__, '__cache'))
			cacheParams = jComponent.getClientProperty(key)
			with cacheParams['lock']:
				od = cacheParams['orderedDict']
				key = ((func.__name__, )
					   + ('args:', )
					   + args 
					   + ('kwargs:', )
					   + tuple([(k, kwargs[k]) for k in sorted(kwargs.keys())]))
				now = system.date.now()
				try:
					result, then = od.pop(key)
					if system.date.millisBetween(then, now) > cacheParams['maxAge']:
						raise KeyError
					cacheParams['hitCount'] += 1
					od[key] = (result, then)
				except KeyError:
					cacheParams['missCount'] += 1
					result = func(*args, **kwargs)
					od[key] = (result, now)
				if len(od) > cacheParams['maxLength']:
					oldestKey, oldestResult = od.popitem(last=False)
				return result
		return useCache
	return buildCache


def resetCache(event, func):
	"""Clears all cache entries and resets
	the cacheParams statistics.
	
	Args:
		event: Event that is used to restrict the cache to the component
		func: Function that has been cached prior to the call
	"""
	jComponent = event.source
	key = _getJComponentKey(jComponent, func)
	cacheParams = jComponent.getClientProperty(key)
	if (cacheParams is not None):
		with cacheParams['lock']:
			cacheParams['orderedDict'].clear()
			cacheParams['hitCount'] = 0
			cacheParams['missCount'] = 0
	else:
		msg = 'Could not find cacheParams for component with name {} and function with name {}'
		msg = msg.format(jComponent.name, func.__name__)
		raise ValueError(msg)


def invalidateCache(event, func, filterFunc=lambda args, kwargs: True):
	"""Invalidates specific cache entries so that the system will 
	refresh the cache on the next call. Returns the number of entries that
	were invalidated.
	
	Args:
		event: Event that is used to restrict the cache to the component
		func: Function that has been cached prior to the call
		filterFunc: Function, optional, defaults to invalidating every entry.
		Used to filter entries by args & kwargs in orderto invalidate them.
		
	Returns:
		long
	"""
	jComponent = event.source
	key = _getJComponentKey(jComponent, func)
	cacheParams = jComponent.getClientProperty(key)
	if (cacheParams is not None):
		with cacheParams['lock']:
			count = 0
			od = cacheParams['orderedDict']
			for key in od.keys():
				argsIdx = key.index('args:')
				kwargsIdx = key.index('kwargs:')
				args = key[argsIdx+1:kwargsIdx]
				kwargs = {k: v for (k, v) in key[kwargsIdx:+1]}
				if filterFunc(args, kwargs):
					del od[key]
					count += 1
		return count
	else:
		msg = 'Could not find cacheParams for component with name {} and function with name {}'
		msg = msg.format(jComponent.name, func.__name__)
		raise ValueError(msg)		


def getCacheStats(event, func):
	"""Returns a dictionary with statistics about the cache.
	
	Args:
		event: Event that is used to restrict the cache to the component
		func: Function that has been cached prior to the call
	"""
	jComponent=event.source
	key = _getJComponentKey(jComponent, func)
	cacheParams = jComponent.getClientProperty(key)
	if (cacheParams is not None):
		with cacheParams['lock']:
			hitCount = cacheParams['hitCount']
			missCount = cacheParams['missCount']
		total = hitCount + missCount
		percentage = 100 * hitCount / total if total != 0 else 0
		return {
			'hitCount': hitCount,
			'missCount': missCount,
			'total': total,
			'percentage': percentage
		}
	else:
		msg = 'Could not find cacheParams for component with name {} and function with name {}'
		msg = msg.format(jComponent.name, func.__name__)
		raise ValueError(msg)
