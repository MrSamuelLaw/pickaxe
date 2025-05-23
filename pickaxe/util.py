from __future__ import print_function
import sys
import traceback
from StringIO import StringIO
from datetime import timedelta
from java.lang import Exception as JavaException
from com.inductiveautomation.ignition.common.model import ApplicationScope



def getGatewayName():
	"""Reads the current gateway name using the system tags.
	Returns: 
		str, name of the gateway
	"""
	return system.tag.readBlocking(['[System]Gateway/SystemName'])[0].value
	
	
def getScope():
	"""Returns the string name of the current scope.
	Returns:
		'designer' | 'client' | 'perspective' | 'gateway'
	"""
	scope = ApplicationScope.getGlobalScope()
	if ApplicationScope.isClient(scope):
		return 'client'
	elif ApplicationScope.isDesigner(scope):
		return 'designer'
	elif ApplicationScope.isGateway(scope):
		try:
			system.perspective.print('msg')
			return 'perspective'
		except:
			return 'gateway'


def timeBetween(seconds):
	"""Converts a time delta of seconds into
	years, months, days... formatted as a string
	Args:
		seconds: int | float
	"""
	dt = timedelta(seconds=seconds)
	return str(dt)


def getRootCause(javaException, maxDepth=5):
	"""Method to get the root cause for a java exception"""
	i = 0
	possibleException = javaException.getCause()
	while i < maxDepth and possibleException:
		i = i + 1
		javaException = possibleException
		possibleException = javaException.getCause()
	return javaException
	
	
def logException(logMethod, exception, tagPath=None, javaRootCause=True, includeStackTrace=False):
	"""Logs an exception using the log method and then 
	write the log message to a tag if tagPath is not None.
	
	Args:
		logMethod: Callable, method to log the exception.
		exception: Exception | JavaException, object to log.
		tagPath: str, optional argument that will also log the exception to a tag.
		
	Example:
		from java.lang import Exception as JavaException
		...
		try:
			<code that causes an exception>
		except (Exception, JavaException) as e:
			logger = system.util.getLogger('mylogger')
			logException(logger.warn, e, tagPath='path/to/memory/tag')
	"""
	# get root cuase if its a java exception
	if javaRootCause and isinstance(exception, JavaException):
		exception = getRootCause(exception)
	
	# start the message
	msg = str(exception)
	
	# get the stack trace if necessary
	if includeStackTrace: 
		if isinstance(exception, JavaException):
			traceBacks = exception.getStackTrace()
			stackTrace = '\n'.join([str(tb) for tb in traceBacks])
		else:
			excName, excValue, traceBack = sys.exc_info()
			stream = StringIO()
			traceback.print_tb(traceBack, file=stream)
			stackTrace = stream.getvalue()
			stream.close()
		msg = msg + '\n' + str(stackTrace)
	
	# log the method
	logMethod(msg)
	
	# log the msg to a tag if requested
	if tagPath is not None:
		system.tag.writeBlocking([tagPath], [msg])
		
	
	