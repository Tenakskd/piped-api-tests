import json
import requests
import urllib.parse
import time
import datetime
import random
import os
import subprocess
from cache import cache

max_api_wait_time = 3
max_time = 10
apis = [
    r"https://invidious.catspeed.cc/", 
    r"https://piped.kavin.rocks/"
]
url = requests.get(r'https://raw.githubusercontent.com/mochidukiyukimi/yuki-youtube-instance/main/instance.txt').text.rstrip()
version = "1.0"

os.system("chmod 777 ./yukiverify")

apichannels = []
apicomments = []
[[apichannels.append(i), apicomments.append(i)] for i in apis]
class APItimeoutError(Exception):
    pass

def is_json(json_str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

def apicommentsrequest(url):
    global apicomments
    global max_time
    starttime = time.time()
    for api in apicomments:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                return res.text
            else:
                print(f"エラー:{api}")
                apicomments.append(api)
                apicomments.remove(api)
        except:
            print(f"タイムアウト:{api}")
            apicomments.append(api)
            apicomments.remove(api)
    raise APItimeoutError("APIがタイムアウトしました")

def apirequest(url):
    global apis
    global max_time
    starttime = time.time()
    for api in apis:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                print(f"成功したAPI: {api}")  
                return res.text
            else:
                print(f"エラー: {api}")
                apis.append(api)
                apis.remove(api)
        except:
            print(f"タイムアウト: {api}")
            apis.append(api)
            apis.remove(api)
    raise APItimeoutError("APIがタイムアウトしました")

def apichannelrequest(url):
    global apichannels
    global max_time
    starttime = time.time()
    for api in apichannels:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                print(f"成功したAPI: {api}")  
                return res.text
            else:
                print(f"エラー: {api}")
                apichannels.append(api)
                apichannels.remove(api)
        except:
            print(f"タイムアウト: {api}")
            apichannels.append(api)
            apichannels.remove(api)
    raise APItimeoutError("APIがタイムアウトしました")

def get_info(request):
    global version
    return json.dumps([version, os.environ.get('RENDER_EXTERNAL_URL'), str(request.scope["headers"]), str(request.scope['router'])[39:-2]])

def get_data(videoid):
    t = json.loads(apirequest(f"api/v1/videos/{urllib.parse.quote(videoid)}"))
    video_data = {
        "title": t["title"],
        "description": t["description"],
        "thumbnail": t["thumbnailUrl"],
        "uploader": t["uploader"],
        "uploaderUrl": t["uploaderUrl"],
        "videoStreams": t["videoStreams"],
        "relatedStreams": t["relatedStreams"]
    }
    
    return video_data, [stream["url"] for stream in t["videoStreams"]], [related["url"] for related in t["relatedStreams"]]

def get_search(q, page):
    t = json.loads(apirequest(f"api/v1/search?q={urllib.parse.quote(q)}&page={page}&hl=jp"))
    def load_search(i):
        if i["type"] == "video":
            return {"title": i["title"], "id": i["videoId"], "author": i["uploader"], "type": "video"}
        elif i["type"] == "playlist":
            return {"title": i["title"], "id": i["playlistId"], "type": "playlist"}
        else:
            return {"author": i["author"], "id": i["authorId"], "thumbnail": i["authorThumbnails"][-1]["url"], "type": "channel"}
    return [load_search(i) for i in t]

def get_channel(channelid):
    t = json.loads(apichannelrequest(f"api/v1/channels/{urllib.parse.quote(channelid)}"))
    if t["relatedStreams"] == []:
        print("APIがチャンネルを返しませんでした")
        apichannels.append(apichannels[0])
        apichannels.remove(apichannels[0])
        raise APItimeoutError("APIがチャンネルを返しませんでした")
    
    return [[{"title": i["title"], "id": i["videoId"], "author": t["uploader"], "published": i["uploadedDate"], "type": "video"} for i in t["relatedStreams"]], {"channelname": t["name"], "channelicon": t["bannerUrl"], "channelprofile": t["description"]}]

def get_playlist(listid, page):
    t = json.loads(apirequest(f"/api/v1/playlists/{urllib.parse.quote(listid)}?page={urllib.parse.quote(page)}"))
    return [{"title": i["title"], "id": i["videoId"], "authorId": i["uploaderUrl"].split("/")[-1], "author": i["uploader"], "type": "video"} for i in t["relatedStreams"]]

def get_comments(videoid):
    t = json.loads(apicommentsrequest(f"api/v1/comments/{urllib.parse.quote(videoid)}?hl=jp"))
    return [{"author": i["author"], "authoricon": i["thumbnail"], "authorid": i["authorId"], "body": i["commentText"]} for i in t["comments"]]

def check_cokie(cookie):
    return cookie == "True"

def get_verifycode():
    try:
        result = subprocess.run(["./yukiverify"], encoding='utf-8', stdout=subprocess.PIPE)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

from fastapi import FastAPI, Depends
from fastapi import Response, Cookie, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.responses import RedirectResponse as redirect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/css", StaticFiles(directory="./css"), name="static")
app.add_middleware(GZipMiddleware, minimum_size=1000)

from fastapi.templating import Jinja2Templates
template = Jinja2Templates(directory='templates')

@app.get("/", response_class=HTMLResponse)
def home(response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    if check_cokie(yuki):
        response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)
        return template("home.html", {"request": request})
    return redirect("/word")

@app.get('/watch', response_class=HTMLResponse)
def video(v: str, response: Response, request: Request, yuki: Union[str] = Cookie(None), proxy: Union[str] = Cookie(None)):
    if not check_cokie(yuki):
        return redirect("/")
    videoid = v
    t, video_urls, related_urls = get_data(videoid)
    return template('video.html', {"request": request, "videoid": videoid, "videourls": video_urls, "res": t["relatedStreams"], "description": t["description"], "videotitle": t["title"], "author": t["uploader"], "authoricon": t["thumbnail"], "proxy": proxy})

@app.get("/search", response_class=HTMLResponse)
def search(q: str, response: Response, request: Request, page: Union[int, None] = 1, yuki: Union[str] = Cookie(None), proxy: Union[str] = Cookie(None)):
    if not check_cokie(yuki):
        return redirect("/")
    results = get_search(q, page)
    return template("search.html", {"request": request, "results": results, "word": q, "next": f"/search?q={q}&page={page + 1}", "proxy": proxy})

@app.get("/channel/{channelid}", response_class=HTMLResponse)
def channel(channelid: str, response: Response, request: Request, yuki: Union[str] = Cookie(None), proxy: Union[str] = Cookie(None)):
    if not check_cokie(yuki):
        return redirect("/")
    t = get_channel(channelid)
    return template("channel.html", {"request": request, "results": t[0], "channelname": t[1]["channelname"], "channelicon": t[1]["channelicon"], "channelprofile": t[1]["channelprofile"], "proxy": proxy})

@app.get("/playlist", response_class=HTMLResponse)
def playlist(list: str, response: Response, request: Request, page: Union[int, None] = 1, yuki: Union[str] = Cookie(None), proxy: Union[str] = Cookie(None)):
    if not check_cokie(yuki):
        return redirect("/")
    results = get_playlist(list, str(page))
    return template("search.html", {"request": request, "results": results, "word": "", "next": f"/playlist?list={list}", "proxy": proxy})

@app.get("/comments")
def comments(request: Request, v: str):
    return template("comments.html", {"request": request, "comments": get_comments(v)})

@app.get("/thumbnail")
def thumbnail(v: str):
    return Response(content=requests.get(f"https://img.youtube.com/vi/{v}/0.jpg").content, media_type="image/jpeg")

@app.exception_handler(500)
def page(request: Request, __):
    return template("APIwait.html", {"request": request}, status_code=500)

@app.exception_handler(APItimeoutError)
def APIwait(request: Request, exception: APItimeoutError):
    return template("APIwait.html", {"request": request}, status_code=500)
