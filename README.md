# Viggo
Unofficial Home Assistant client for Viggo (https://viggo.dk/viggo/)

## Disclaimer
This a very early version...

## Configuration
The required parameters is:
+ url
+ username
+ password

```yaml
viggo:
  # REQUIRED
  url: https://raagelund.viggo.dk    # The URL to the "Viggo" of the school
  username: john@my_domain.com       # Your username
  password: SECRET                   # Your password

  # OPTIONAL, with these the default values is used
  update_interval: 15   # Bypass the standard of 60 minutes interval
    
  show:                 # These are the default values used if nothing is stated
    userinfo: True      # Show the users info
    unread: True        # Make sensors with unread messages and bulletins
    amount: 5           # Amount of messages or bulletins to show, 0 for excluding
    details:            # The level og details in showing messages
      - sender_name     # The name of the sender
      - date            # Date of the message
      - subject         # Subject
      - preview         # We can only show a preview, and not the entire message
      - sender_image    # The profile picture of the sender
    relations: True     # Shall we show our relations (children)
    schedule: True      # Shal we show the schedule for the current week
```
