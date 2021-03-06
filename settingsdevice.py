import dbus
import logging

# Local imports
from vedbus import VeDbusItemImport

## Indexes for the setting dictonary.
PATH = 0
VALUE = 1
MINIMUM = 2
MAXIMUM = 3

## The Settings Device class.
# Used by python programs, such as the vrm-logger, to read and write settings they
# need to store on disk. And since these settings might be changed from a different
# source, such as the GUI, the program can pass an eventCallback that will be called
# as soon as some setting is changed.
#
# The settings are stored in flash via the com.victronenergy.settings service on dbus.
# See https://github.com/victronenergy/localsettings for more info.
#
# If there are settings in de supportSettings list which are not yet on the dbus, 
# and therefore not yet in the xml file, they will be added through the dbus-addSetting
# interface of com.victronenergy.settings.
class SettingsDevice(object):
	## The constructor processes the tree of dbus-items.
	# @param bus the system-dbus object
	# @param name the dbus-service-name of the settings dbus service, 'com.victronenergy.settings'
	# @param supportedSettings dictionary with all setting-names, and their defaultvalue, min and max.
	# @param eventCallback function that will be called on changes on any of these settings
	def __init__(self, bus, supportedSettings, eventCallback, name='com.victronenergy.settings'):
		logging.debug("===== Settings device init starting... =====")
		self._bus = bus
		self._dbus_name = name
		self._eventCallback = eventCallback
		self._supportedSettings = supportedSettings
		self._values = {} # stored the values, used to pass the old value along on a setting change
		self._settings = {}

		if 'com.victronenergy.settings' not in self._bus.list_names():
			raise Exception("The settings service com.victronenergy.settings does not exist!")

		# Add the items.
		for setting, options in self._supportedSettings.items():
			busitem = VeDbusItemImport(self._bus, self._dbus_name, options[PATH], self.handleChangedSetting)
			if busitem.exists:
				logging.debug("Setting %s found" % options[PATH])
			else:
				logging.info("Setting %s does not exist yet, adding it" % options[PATH])

				# Prepare to add the setting.
				path = options[PATH].replace('/Settings/', '', 1)
				value = options[VALUE]
				if type(value) == int or type(value) == dbus.Int16 or type(value) == dbus.Int32 or type(value) == dbus.Int64:
					itemType = 'i'
				elif type(value) == float or type(value) == dbus.Double:
					itemType = 'f'
				else:
					itemType = 's'
				
				# Add the setting
				# TODO, make an object that inherits VeDbusItemImport, and complete the D-Bus settingsitem interface
				VeDbusItemImport(self._bus, self._dbus_name, '/Settings', createsignal=False)._proxy.AddSetting('', path, value, itemType, options[MINIMUM], options[MAXIMUM])

				busitem = VeDbusItemImport(self._bus, self._dbus_name, options[PATH], self.handleChangedSetting)
			
			self._settings[setting] = busitem
			self._values[setting] = busitem.get_value()

		logging.debug("===== Settings device init finished =====")

	def handleChangedSetting(self, servicename, path, changes):
		# TODO: yes yes, below loop is a bit stupid. But as it won't happen often, why would we
		# TODO: keep a second dictionary just for this?
		setting = None
		for s, options in self._supportedSettings.items():
			if options[PATH] == path:
				setting = s
				break

		assert setting is not None

		oldvalue = self._values[setting]
		self._values[setting] = changes['Value']

		if self._eventCallback is None:
			return

		self._eventCallback(setting, oldvalue, changes['Value'])

	def __getitem__(self, setting):
		return self._settings[setting].get_value()

	def __setitem__(self, setting, newvalue):
		result = self._settings[setting].set_value(newvalue)
		if result != 0:
			# Trying to make some false change to our own settings? How dumb!
			assert False
