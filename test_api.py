import requests
import json

print('Making 3 consecutive requests to /api/analyze/fake endpoint...')
print('=' * 60)

risk_scores = []
for i in range(1, 4):
    try:
        response = requests.post('http://localhost:8000/api/analyze/fake', json={})
        data = response.json()
        risk_score = data['risk']['score']
        risk_scores.append({'request': i, 'risk_score': risk_score})
        print(f'Request {i}: Status Code {response.status_code}')
        print(f'  Risk Score: {risk_score}')
    except Exception as e:
        print(f'Request {i}: Error - {e}')

print()
print('=' * 60)
print('RISK SCORES FROM 3 CONSECUTIVE REQUESTS:')
print('=' * 60)
for item in risk_scores:
    print(f"Request {item['request']}: Risk Score = {item['risk_score']}")

# Check if scores are different
if len(risk_scores) >= 3:
    scores = [item['risk_score'] for item in risk_scores]
    if len(set(scores)) > 1:
        print()
        print('Confirmed: Risk scores are DIFFERENT across requests')
        print(f'  Scores: {scores}')
    else:
        print()
        print('All risk scores are the SAME')
