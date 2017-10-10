
Start/Stop/Kill the Development Server
================================================================================
Start the default server.

```
dev_appserver.py app.yaml
dev_appserver.py --clear_datastore=yes app.yaml
```

Sometimes you need to kill some processes on a given port:
```
lsof -P | grep '8080' | awk '{print $2}' | xargs kill -9
```

API
================================================================================

### Get a json list of most recent submitted pictures ###
```
http://--.appspot.com/user/<USERNAME>/json/?id_token=XXXX
```
Example
```
curl -X GET https://mpcs51033-2017-autumn-photos.appspot.com/user/default/json/?id_token=XXXX
```

### See a list of the most recent on a web page (useful for debugging) ####
```
http://--.appspot.com/user/<USERNAME>/web/?id_token=XXXX
```
Example
```
 curl -X GET https://mpcs51033-2017-autumn-photos.appspot.com/user/andrew/web/?id_token=XXXX
```

### Endpoint for posting images to server. There is an optional "caption" parameter that you can use. ###
```
http://--.appspot.com/user/<USERNAME>/post/?id_token=XXXX
```
Example
```
curl -X POST -H "Content-Type: multipart/form-data" -F caption='curl' -F "image=@IMG_0255.jpg" https://mpcs51033-2017-autumn-photos.appspot.com/post/lolakitty/?id_token=XXXX
```

### Delete a certain photo. ###
```
http://--.appspot.com//image/<IMAGE-KEY>/delete//?id_token=XXXX
```
Example
```

```

~~~
 curl -X POST http://localhost:8080/email_task/
~~~

Deploy to App Engine
================================================================================
The following updates a server that is using a single default service defined in
app.yaml file.  Note the `--project` option for you own project id and the `--version`.  If you don't specify a version, App Engine will assign one for you.

```
gcloud app deploy app.yaml index.yaml --project mpcs51033-2017-autumn-photos -V some_version
```

See it in action in a browser.
```
gcloud app browse --project  mpcs51033-2017-autumn-photos
```

Deploy Task Queues and Cron Tasks
================================================================================
Deploy the cron jobs.
```
gcloud app deploy cron.yaml
```

Deploy the task queues that will do the work.
```
gcloud app deploy queue.yaml
```
