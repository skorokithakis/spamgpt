SpamGPT
=======

SpamGPT uses the power of ChatGPT to reply to spammers with realistic-sounding emails,
wasting their damn time like they wasted mine.

There isn't much documentation yet, but I'll add some. Also, the email protocols are so
old and brittle, that I'd be very surprised if this thing doesn't break all the time.
Still, it kind of works for me, and maybe it will work for you too.


# Installation

You don't need to install it, clone the repo and run it from there.


# Configuration

You need to give it some configuration environment variables, if it's ever going to run:

| *Name* | *Why* |
|---|---|
| **`SMTP_URL`** | The URL of your SMTP server. Usually, `smtp://email@host.com:password@smtp.youremail.com`. |
| **`IMAP_URL`** | The URL of your IMAP server. Usually, `imap://email@host.com:password@imap.youremail.com`. |
| **`OPENAI_API_KEY`** | Your OpenAI API key, for talking to GPT. |
| **`MY_NAME`** | Your name, for GPT to know, e.g. `Stavros`. |
| **`MY_ADDRESSES`** | A comma-separated list of your email addresses, so SpamGPT knows where you are the recipient. E.g. `foo@bar.com,baz@bar.com`. Note that, if you have catch-all domains, this can also be just the domain, e.g. `@foo.bar,john@example.com,@baz.com`. |
| **`MESSAGE_ID_HOST`** | Your email provider's host for the `Message-ID` email header that they send (I know, good luck). You can find this by opening an email *that you sent*, clicking "view raw message" (or similar), and looking for `Message-ID`. It will be something like `someletters@mail.host.com`. You need the `mail.host.com` part for this. If you get this wrong, I've noticed that some providers (Gmail, for example) will consider the message ID invalid if it doesn't come from your particular host, and generate its own message ID. This breaks SpamGPT's threading, and it gets confused and doesn't know when to reply and to whom. |
| **`PERSONAL_DETAILS`** | Some details about you, to help ChatGPT imitate you. For example, `I am Stavros, a software developer from Greece.` |


# Deployment

You can easily deploy SpamGPT on
a [Harbormaster](https://harbormaster.readthedocs.io/en/latest/) server.

Just add this stanza to your Harbormaster config file:

```yaml
apps:
  spamgpt:
    url: https://github.com/skorokithakis/spamgpt.git
    environment_file: "secrets/spamgpt.txt"
```

Add your environment variables to `secrets/spamgpt.txt` (or however you do environment
variables), and Harbormaster will deploy and run SpamGPT, launching it at a random
minute every hour to reply to your spam.
