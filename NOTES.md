Use this as a starting reference for Assignement 2.

Name: Yi Wang

NOTE:
please authenticate a user (to get id_token) firstly.


curl for local server:

to authenticate
```
curl -X GET http://localhost:8080/user/authenticate/?username=<USERNAME>&password=<PASSWORD>
```

for a list of the most recent
```
curl -X GET http://localhost:8080/user/<USERNAME>/web/?id_token=XXXX
curl -X GET http://localhost:8080/user/<USERNAME>/json/?id_token=XXXX
```

to get a certain photo
```
curl -X GET http://localhost:8080/image/<IMAGE-KEY>/?id_token=XXXX
```

to post a photo
```
curl -X POST -H "Content-Type: multipart/form-data" -F caption='curl' -F "image=<IMAGE-NAME>" https://localhost:8080/post/<USERNAME>/?id_token=XXXX
```

to delete
```
curl -X POST http://localhost:8080/image/<IMAGE-KEY>/delete/?id_token=XXXX
```


url: https://phototimeline-182520.appspot.com

curl:

to authenticate
```
curl -X GET http://phototimeline-182520.appspot.com/user/authenticate/?username=<USERNAME>&password=<PASSWORD>
```

for a list of the most recent
```
curl -X GET http://phototimeline-182520.appspot.com/user/<USERNAME>/web/?id_token=XXXX
curl -X GET http://phototimeline-182520.appspot.com/user/<USERNAME>/json/?id_token=XXXX
```

to get a certain photo
```
curl -X GET http://phototimeline-182520.appspot.com/image/<IMAGE-KEY>/?id_token=XXXX
```

to post a photo
```
curl -X POST -H "Content-Type: multipart/form-data" -F caption='curl' -F "image=<IMAGE-NAME>" https://phototimeline-182520.appspot.com/post/<USERNAME>/?id_token=XXXX
```

to delete
```
curl -X POST http://phototimeline-182520.appspot.com/image/<IMAGE-KEY>/delete/?id_token=XXXX
```