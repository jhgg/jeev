from jeev.message import Attachment
from jeev.utils.importing import import_dotted_path
import module


@module.loaded
def loaded():
    module.g.geocoder = import_dotted_path(module.opts.get('using', 'geopy.geocoders.Nominatim'))()


@module.respond('geocode (.*)$')
@module.async()
def geocode(message, location):
    g = module.g.geocoder.geocode(location)
    if g:
        a = Attachment(g.address)
        a.field("Latitude", g.latitude, True)
        a.field("Longitude", g.longitude, True)
        message.reply_with_attachment(a)
    else:
        message.reply_to_user("Couldn't geocode that...")