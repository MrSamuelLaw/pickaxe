from __future__ import print_function
import time
import datetime



class TimerBase(object):
	"""Base class for TON and TOF timers.
	Uses the AB syntax but with the class based design pattern
	found in Twincat. 
	
	Note, PRE is in whichever units timingFunc is in, which
	defaults to seconds. 
	"""
	
	def __init__(self, PRE, timingFunc=time.time):
		self._now = None
		self._start = None
		self._timingFunc = timingFunc
		self.EN = False
		self.DN = False
		self.TT = False
		self.PRE = PRE
		self.ACC = 0
		
	def reset(self):
		self.DN = False
		self.TT = False
		self.ACC = 0
		self._start = None
		return self
		
		
class TON(TimerBase):
		
	def __call__(self, EN):
		self.EN = EN
		# check if timer is enabled
		if self.EN and (not self.DN):
			self._now = self._timingFunc()
			if not self.TT:
				# set start = now on rising edge
				self._start = self._now
				# compute the time accumulated so far
			self.ACC = self._now - self._start
			self.DN = self.ACC >= self.PRE
		# reset the timer on a falling edge of enabled
		elif (not self.EN) and (self.ACC or self.DN):
			self.reset()
		# update TT state
		self.TT = self.EN and (not self.DN)
		return self
		
		
class TOF(TimerBase):
		
	def __call__(self, EN):
		self.EN = EN
		self.DN = self.DN or self.EN
		# check if timer is enabled
		if (not self.EN) and self.DN:
			self._now = self._timingFunc()
			if not self.TT:
				# set start = now on rising edge
				self._start = self._now
			# compute the time accumulated so far
			self.ACC = self._now - self._start
			self.DN = self.ACC <= self.PRE
		# reset the timer on a falling edge of enabled
		elif self.EN and (self.ACC or self.DN):
			self.reset()
		# update TT state
		self.TT = (not self.EN) and self.DN
		return self
		
		
def javaDateToDatetime(javaDate):
	"""Returns a datetime.datetime object given a java Date object."""
	millis = system.date.toMillis(javaDate)
	datetimeDate = datetime.datetime.fromtimestamp(float(millis*0.001))
	return datetimeDate
	

def datetimeToJavaDate(datetimeObj):
	"""Returns a java.util.Date object"""
	
	# convert to datetime object if date
	if type(datetimeObj) == datetime.date:
		datetimeObj = datetime.datetime.combine(datetimeObj, datetime.datetime.min.time())
	# compute the timezone offset
	isDST = time.daylight and time.localtime().tm_isdst > 0
	utcOffset = (time.altzone if isDST else time.timezone)
	e = datetime.datetime(1970, 1, 1) - datetime.timedelta(seconds=utcOffset)
	# convert to millis
	millis = int((datetimeObj - e).total_seconds()*1000)
	# load into java
	javaDate = system.date.fromMillis(millis)
	return javaDate
	