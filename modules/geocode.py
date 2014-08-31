from geopy.geocoders import Nominatim
from werkzeug.utils import escape
from jeev.message import Attachment
from jeev.module import Module
from utils.importing import import_dotted_path

module = Module()

@module.loaded
def loaded(module):
    module.geocoder = import_dotted_path(module.opts['using'])()

@module.respond('geocode (.*)$')
@module.async()
def geocode(message, location):
    g = module.geocoder.geocode(location)
    if g:
        a = Attachment(g.address)
        a.field("Latitude", g.latitude, True)
        a.field("Longitude", g.longitude, True)
        message.reply_with_attachment(a)
    else:
        message.reply_to_user("Couldn't geocode that...")