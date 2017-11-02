# Web panel simplifying clicktracker creation in DCM. AppEngine Standard compatible.

This is a Python web application that allows a quick and simple creation of
click tracking ads in DCM. It exposes a simple webpage with a backend meant to
be hosted on Google AppEngine Standard environment.

## Setup instructions:

1.  Create a GCP project with AppEngine enabled
    (<https://cloud.google.com/appengine/docs/standard/python/quickstart>)
2.  Set your local env to use the newly created project in CLI
3.  Change to the directory with the source code
4.  Install google-api-python-client to lib directory `pip install -t lib/
    google-api-python-client` (or on Linux `pip install --system
    --install-option="--prefix=" -t lib/ google-api-python-client`)
5.  Enable DCM API
    (<https://developers.google.com/doubleclick-advertisers/getting_started>)
    and download credentials for API Client
    (<https://developers.google.com/api-client-library/python/guide/aaa_oauth>)
6.  Try running the app locally: `dev_appserver.py .` and check that it works as
    intended
7.  Deploy the app to AppEngine `gcloud app deploy` and press yes
8.  Verify the deployed app works: `gcloud app browse`

### This is not an official Google product.
