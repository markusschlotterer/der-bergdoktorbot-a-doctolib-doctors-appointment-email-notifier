from datetime import date, datetime, timedelta
import json
import os
import urllib.parse
import urllib.request
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

port = 587  # For starttls
smtp_server = ''
sender_email = ''
password = ''
receiver_email = ''

BOOKING_URL = ''
AVAILABILITIES_URL = ''
APPOINTMENT_NAME = None
MOVE_BOOKING_URL = None
UPCOMING_DAYS = 15
MAX_DATETIME_IN_FUTURE = datetime.today() + timedelta(days = UPCOMING_DAYS)
NOTIFY_HOURLY = False

# Read parameters from private file
myData = 'myData.py'
if os.path.exists(myData): 
    exec(compile(source=open(myData).read(), filename=myData, mode='exec'))

if not (
    BOOKING_URL
    and AVAILABILITIES_URL
    ) or UPCOMING_DAYS > 15:
    exit()

urlParts = urllib.parse.urlparse(AVAILABILITIES_URL)
query = dict(urllib.parse.parse_qsl(urlParts.query))
query.update({
    'limit': UPCOMING_DAYS,
    'start_date': date.today(),
})
newAvailabilitiesUrl = (urlParts
                            ._replace(query = urllib.parse.urlencode(query))
                            .geturl())
request = (urllib
                .request
                .Request(newAvailabilitiesUrl))
request.add_header(
    'User-Agent',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
)
response = (urllib.request
                    .urlopen(request)
                    .read()
                    .decode('utf-8'))

availabilities = json.loads(response)

slotsInNearFuture = availabilities['total']
slotInNearFutureExist = slotsInNearFuture > 0
earlierSlotExists = False
if slotInNearFutureExist:
    for day in availabilities['availabilities']:
        if len(day['slots']) == 0:
            continue;
        nextDatetimeIso8601 = day['date']
        nextDatetime = (datetime.fromisoformat(nextDatetimeIso8601)
                                .replace(tzinfo = None))
        if nextDatetime < MAX_DATETIME_IN_FUTURE:
            earlierSlotExists = True
            break;

isOnTheHour = datetime.now().minute == 0
isHourlyNotificationDue = isOnTheHour and NOTIFY_HOURLY

if not (earlierSlotExists or isHourlyNotificationDue):
    exit()

message = ''
if APPOINTMENT_NAME:
    message += f'👨‍⚕️👩‍⚕️ {APPOINTMENT_NAME}'
    message += '\n'

if earlierSlotExists:
    pluralSuffix = 's' if slotsInNearFuture > 1 else ''
    message += f'🔥 {slotsInNearFuture} slot{pluralSuffix} within {UPCOMING_DAYS}d!'
    message += '\n'
    if MOVE_BOOKING_URL:
        message += f'<a href="{MOVE_BOOKING_URL}">🚚 Move existing booking</a>.'
        message += '\n'

if isHourlyNotificationDue:
    nextSlotDatetimeIso8601 = availabilities['next_slot']
    nextSlotDate = (datetime.fromisoformat(nextSlotDatetimeIso8601)
                                .strftime('%d %B %Y'))
    message += f'🐌 slot <i>{nextSlotDate}</i>.'
    message += '\n'

message += f'Book now on <a href="{BOOKING_URL}">doctolib.de</a>.'

html = message

message = MIMEMultipart("alternative")
message["Subject"] = "New slots in " + APPOINTMENT_NAME + " on doctolib.de"
message["From"] = sender_email
message["To"] = receiver_email

# Turn these into plain/html MIMEText objects
#part1 = MIMEText(text, "plain")
part2 = MIMEText(html, "html")

# Add HTML/plain-text parts to MIMEMultipart message
# The email client will try to render the last part first
#message.attach(part1)
message.attach(part2)

# Create a secure SSL context
context = ssl.create_default_context()

# Try to log in to server and send email
try:
    server = smtplib.SMTP(smtp_server,port)
    server.ehlo() # Can be omitted
    server.starttls(context=context) # Secure the connection
    server.ehlo() # Can be omitted
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, message.as_string())
except Exception as e:
    # Print any error messages to stdout
    print(e)
finally:
    server.quit() 
