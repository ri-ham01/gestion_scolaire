import requests
import re

s = requests.Session()
res1 = s.get('http://localhost:5000/auth/login')
csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', res1.text)
if not csrf_match:
    print("Could not find CSRF token")
    exit(1)
csrf_token = csrf_match.group(1)

res2 = s.post('http://localhost:5000/auth/login', data={
    'csrf_token': csrf_token,
    'username': '26infoA_1',
    'password': 'password123'
})
print("Login status:", res2.status_code)
if 'Tableau de bord' not in res2.text and 'Dashboard' not in res2.text and 'لوحة القيادة' not in res2.text:
    print("Failed to login properly.")

res3 = s.get('http://localhost:5000/etudiant/dashboard')
print("Dashboard status:", res3.status_code)
if "erreur" in res3.text.lower() or "error" in res3.text.lower():
    print("Found 'erreur' in the dashboard HTML!")
    print(res3.text[:1000])
else:
    print("No 'erreur' in dashboard html.")
