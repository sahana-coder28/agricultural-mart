import urllib.request
import urllib.error
import urllib.parse
from http.cookiejar import CookieJar

def test_url(url, method='GET', data=None):
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(url, method=method, data=data)
    try:
        response = opener.open(req)
        print(f"{method} {url} - No error, status:", response.status)
    except urllib.error.HTTPError as e:
        content = e.read().decode('utf-8')
        import re
        title_match = re.search(r'<title>(.*?)</title>', content)
        h1_match = re.search(r'<h1>(.*?)</h1>', content)
        traceback_match = re.search(r'<div class="traceback">(.*?)</div>', content, re.DOTALL)
        
        print(f"{method} {url} - HTTP Error:", e.code)
        if title_match: print("TITLE:", title_match.group(1).strip())
        if h1_match: print("H1:", h1_match.group(1).strip())
        
        if traceback_match:
            text = re.sub(r'<[^>]+>', '', traceback_match.group(1))
            print("TRACEBACK:")
            for line in text.split('\n'):
                if line.strip(): print(line.strip())
    except Exception as e:
        print(f"Connection error on {url}:", e)

test_url('http://127.0.0.1:5000/')
test_url('http://127.0.0.1:5000/login')
# Test submitting login
data = urllib.parse.urlencode({'email':'admin@agromart.com', 'password':'password123'}).encode('ascii')
test_url('http://127.0.0.1:5000/admin/login', method='POST', data=data)

