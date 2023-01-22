# Viggo
Unofficial Home Assistant client for Viggo (https://viggo.dk/viggo/)

## Disclaimer
This a very early version...

## Configuration
It this version, it is all or nothing. In the final it will be possible to adjust settings.

```yaml
viggo:
  # REQUIRED
  url: https://raagelund.viggo.dk    # The URL to the "Viggo" of the school
  username: john@my_domain.com       # Your username
  password: SECRET                   # Your password

  # OPTIONAL, with these the default values is used
  show:
    userinfo: True      # Show the users info
    unread: True        # Make sensors with unread messages and bulletins
    amount: 5           # Amount of messages or bulletins to show, 0 for excluding
    details:            # The level og details in showing messages
      - sender_name     # The name of the sender
      - date            # Date of the message
      - subject         # Subject
      - preview         # We can only show a preview, and not the entire message
      - sender_image    # The profile picture of the sender
```

## Known bugs
- The messages in the dragt folder has a different format and breaks the integration... (1st priority)
