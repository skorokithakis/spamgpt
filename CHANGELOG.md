Changelog
=========


(unreleased)
------------

Fix
~~~
- Only use the last five messages as context. [Stavros Korokithakis]
- More fix GPT issue where the user and assistant were swapped. [Stavros
  Korokithakis]
- Fix GPT issue where the user and assistant were swapped. [Stavros
  Korokithakis]
- Improve quote removal. [Stavros Korokithakis]
- Improve quote removal. [Stavros Korokithakis]
- Improve quote removal. [Stavros Korokithakis]
- Change Docker shell. [Stavros Korokithakis]
- Remove duplicate variables from Compose file. [Stavros Korokithakis]
- Add more variable checking. [Stavros Korokithakis]
- More robust reference handling. [Stavros Korokithakis]
- Clean up emails a bit better. [Stavros Korokithakis]
- Parse the bodies of emails better, because email is a fucking mess.
  [Stavros Korokithakis]
- Clean up HTML messages before replying. [Stavros Korokithakis]
- Change "Me" to "ChatGPT" [Stavros Korokithakis]
- Hide email addresses from exported threads. [Stavros Korokithakis]
- Add the subject to the chat context. [Stavros Korokithakis]
- Make configuration more robust. [Stavros Korokithakis]

Other
~~~~~
- Feat: Tell GPT the current date and time. [Stavros Korokithakis]
- Merge pull request #3 from skorokithakis/sweep/fix-incompatible-
  arguments. [Stavros Korokithakis]

  Make arguments -d and --export-json incompatible
- Update spamgpt/cli.py. [sweep-ai[bot]]
- Add --debug flag. [Stavros Korokithakis]
- Feat: Add another quoting method. [Stavros Korokithakis]
- Feat: Echo sleep interval in the Docker container. [Stavros
  Korokithakis]
- Doc: Add deployment instructions. [Stavros Korokithakis]
- Chore: Remove the data dir from Compose. [Stavros Korokithakis]
- Feat: Add the `MY_NAME` variable. [Stavros Korokithakis]
- Feat: Add Docker image with crond. [Stavros Korokithakis]
- Ci: Forbid pudb in pre-commit. [Stavros Korokithakis]
- Chore: Change Python version. [Stavros Korokithakis]
- Feat: Add JSON exporting. [Stavros Korokithakis]
- Feat: Add date to the email message. [Stavros Korokithakis]
- Feat: Add prompt customization. [Stavros Korokithakis]
- Initial commit. [Stavros Korokithakis]


