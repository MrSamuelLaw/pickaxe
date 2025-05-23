from __future__ import print_function
from inspect import getargspec
from traceback import format_exc
from java.awt import Toolkit
from java.awt.datatransfer import StringSelection, DataFlavor
from java.lang import Exception as JavaException
from java.util.concurrent import CompletableFuture
from pickaxe.java_wrappers.function_wrappers import RunnableWrapper



def copyToClipboard(string_data):
	"""Copies string data to the clipboard
	Args;
		string_data: str
	"""
	clipboard = Toolkit.getDefaultToolkit().getSystemClipboard()
	clipboard.setContents(StringSelection(string_data), None)


def pasteFromClipboard():
	"""Returns string data from the clipboard
	"""
	return Toolkit.getDefaultToolkit().getSystemClipboard().getData(DataFlavor.stringFlavor)


def onMainThread(func):
	"""decorator used to invoke a function immediatly on the main thread.
	
	Example:
		this = event.source
		...
		def functionThatIsAsync(...):
			data = fetchData()
			
			@onMainThread
			def updateGui():
				this.data = data
	"""
	system.util.invokeLater(func)


def propertyChangeHandler(event, millis=50):
	"""Decorator that makes managing property changes significantly easier
	providing built in debouncing and enhanced readability.
	
	Args:
		event: Event | Any, event with attribute propertyName.
		millis: long, minimum duration between function calls in milliseconds.
		
	Example:
		@propertyChangeHandler(event, millis=100)
		def updateTable(serialCode, trackingNumber, bundleTrackingNumber):
			query = ...
			result = pickaxe.db.runPrepUpdate(query, {'serialCode': serialCode}, 'mydb')
			this = event.source
			this.data = result
			...
	"""
	def outer(func, jComponent=event.source, millis=millis):
		# create a key for persisting data
		key = '.'.join((jComponent.name, func.__name__, '__pch'))
		# check if the function needs to be invoked or not
		now = system.date.toMillis(system.date.now())
		delta = now - long(jComponent.getClientProperty(key) or 0)
		propNames = getargspec(func).args
		if (delta > millis) and (event.propertyName in propNames):
			logger = system.util.getLogger('pickaxe.vision.util.propertyChangeHandler')
			if logger.isDebugEnabled():
				msg = 'propertyChangeHandler called for component = {}, and function = {}'
				msg = msg.format(jComponent.name, func.__name__)
				logger.debug(msg)
			# if it does need to be run, update the last run time
			jComponent.putClientProperty(key, now)
			# run the function in <x> milliseconds to allow any other events to process
			def inner():
				kwargs = {name: getattr(jComponent, name, None) for name in propNames}
				func(**kwargs)
			system.util.invokeLater(inner, millis)
		return func
	return outer


def asyncPropertyChangeHandler(event, millis=50):
	"""Decorator that makes managing property changes that require fetching data asyncronosly 
	significantly easier while providing built in debouncing and enhanced readability.
	Note that even if the asyncPropertyChangeHandler fires again but the previous iteration
	has not completed, the function will still not run, this is to prevent overloading external
	resources with requests in the event of rapid property changes.
	
	Args:
		event: Event | Any, event with attribute propertyName.
		millis: long, minimum duration between function calls in milliseconds.
		
	Example:
		@asyncPropertyChangeHandler(event, millis=100)
		def updateTable(tagPath):
			data = ... # code that takes a long time and queries data using the tagPath
			
			@onMainThread
			def updateData():
				this.data = data
			
			otherData = ... # more code that takes a long time here
			
			@onMainThread
			def updateOtherData():
				this.otherData = otherData
	"""
	def outer(func, jComponent=event.source, millis=millis):
		# create a key for persisting data
		key = key = '.'.join((jComponent.name, func.__name__, '__apch'))
		cfKey = key + '.__cf'
		# check if the function needs to be invoked or not
		now = system.date.toMillis(system.date.now())
		delta = now - long(jComponent.getClientProperty(key) or 0)
		cf = jComponent.getClientProperty(cfKey)
		propNames = getargspec(func).args
		if ((delta > millis) and (event.propertyName in propNames)
			and ((cf is None) or cf.isDone())):
			# if it does need to be run, update the last run time
			jComponent.putClientProperty(key, now)
			logger = system.util.getLogger('pickaxe.vision.util.asyncPropertyChangeHandler')
			if logger.isDebugEnabled():
				msg = 'propertyChangeHandler called for component = {}, and function = {}'
				msg = msg.format(jComponent.name, func.__name__)
				logger.debug(msg)
			# run the function in <x> milliseconds to allow any other events to process
			def inner():
				kwargs = {name: getattr(jComponent, name, None) for name in propNames}
				
				# create a wrapper to handle passing exception info between threads
				def wrapper(**kwargs):
					try:
						func(**kwargs)
					except (Exception, JavaException) as e:
						stackTrace = format_exc() 
						@onMainThread
						def raiseException():
							msg = 'exception caught in asyncPropertyChangeHandler\nmsg={}\nstackTrace={}'
							msg = msg.format(e, stackTrace)
							raise Exception(msg)
				
				cf = CompletableFuture.runAsync(RunnableWrapper(lambda: wrapper(**kwargs)))
				jComponent.putClientProperty(cfKey, cf)
			system.util.invokeLater(inner, millis)
		return func
	return outer

