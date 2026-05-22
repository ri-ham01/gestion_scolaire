import urllib.request
import urllib.parse
from http.cookiejar import CookieJar

cj = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
urllib.request.install_opener(opener)

data = urllib.parse.urlencode({'username': '26infoA_1', 'password': 'password123'}).encode('utf-8')
req = urllib.request.Request('http://localhost:5000/auth/login', data=data)
try:
    res = urllib.request.urlopen(req)
    print("Login:", res.status)
except Exception as e:
    print("Login error:", e)

req2 = urllib.request.Request('http://localhost:5000/etudiant/dashboard')
try:
    res2 = urllib.request.urlopen(req2)
    print("Dashboard:", res2.status)
    content = res2.read().decode('utf-8')
    if "erreur" in content.lower():
         print("Found word erreur!")
    else:
         print("No erreur found in text")
except Exception as e:
    if hasattr(e, 'read'):
        content = e.read().decode('utf-8')
        print(content[:500])
    print("Dashboard error:", e)
