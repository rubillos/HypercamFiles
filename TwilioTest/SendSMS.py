from twilio.rest import Client

# Your Account SID from twilio.com/console
account_sid = "***REMOVED***"
# Your Auth Token from twilio.com/console
auth_token  = "***REMOVED***"

client = Client(account_sid, auth_token)

message = client.messages.create(from_='***REMOVED***', to='***REMOVED***', body='Test message from Hypercam!')
#print(message.sid)
