import requests

resume_text = """
John Doe
Senior Software Engineer
john.doe@email.com | 555-0199

SKILLS
Python, FastAPI, Django, PostgreSQL, Docker, Redis, Git, Unit Testing, AWS

EXPERIENCE
Lead Backend Engineer | Acme Tech (2021 - Present)
- Designed and built distributed microservices using FastAPI, Python, and PostgreSQL.
- Implemented high-throughput caching layer with Redis, reducing latency by 45%.
- Maintained 90% unit test coverage using pytest and automated CI/CD pipelines.

Software Developer | Beta Corp (2018 - 2021)
- Developed REST APIs and database schema migrations with Django and PostgreSQL.
- Containerized legacy services with Docker and deployed onto AWS EC2 instances.

EDUCATION
B.S. in Computer Science | State University (2014 - 2018)
"""

files = {'file': ('resume.txt', resume_text.encode('utf-8'), 'text/plain')}
data = {'target_role': 'Python Developer'}

res = requests.post('http://127.0.0.1:8000/api/resume/upload', files=files, data=data)
print('Resume Upload Status:', res.status_code)
resp_data = res.json()
resume_id = resp_data.get('resume_id')
print('Resume ID:', resume_id)
print('Candidate Name:', resp_data.get('candidate_name'))
print('Routed Track:', resp_data.get('routed_track'))
print('Integrity Status:', resp_data.get('authenticity_outcome'))
print('Integrity Headline:', resp_data.get('authenticity_headline'))
print('Eligibility Outcome:', resp_data.get('eligibility_status'))
print('Eligibility Headline:', resp_data.get('eligibility_headline'))
print('Eligibility Reasons:', len(resp_data.get('eligibility_reasons', [])))

# Test Eligibility Endpoint
el_res = requests.get(f'http://127.0.0.1:8000/api/resume/{resume_id}/eligibility?target_role=Python%20Developer')
print('Eligibility Endpoint Status:', el_res.status_code)
print('Eligibility Endpoint Outcome:', el_res.json().get('outcome'))

# Start Session
start_res = requests.post('http://127.0.0.1:8000/api/interview/start', json={
    'role': 'Python Developer',
    'track': 'python',
    'max_questions': 5,
    'difficulty_mode': 'adaptive',
    'dynamic_questions': False,
    'resume_id': resume_id
})
print('Start Interview Status:', start_res.status_code)
start_json = start_res.json()
session_id = start_json.get('session_id')
print('Session ID:', session_id)
print('Question 1 Text:', start_json.get('text'))
print('Response Type:', start_json.get('response_type'))

# Submit an answer to Q1
ans_res = requests.post(f'http://127.0.0.1:8000/api/interview/{session_id}/answer', json={
    'answer': 'A list in Python is mutable, dynamic array while a tuple is an immutable sequence stored in contiguous memory.'
})
print('Submit Answer Status:', ans_res.status_code)
ans_json = ans_res.json()
print('Awarded Marks:', ans_json.get('evaluation', {}).get('awarded_marks'))

# End Interview early to finalize report
end_res = requests.post(f'http://127.0.0.1:8000/api/interview/{session_id}/end', json={'status': 'completed'})
print('End Interview Status:', end_res.status_code)

# Test PDF Generation Endpoint
pdf_res = requests.get(f'http://127.0.0.1:8000/api/interview/{session_id}/pdf')
print('PDF Endpoint Status:', pdf_res.status_code)
print('PDF Content-Type:', pdf_res.headers.get('content-type'))
print('PDF Content Length:', len(pdf_res.content))
assert pdf_res.content[:4] == b'%PDF', 'Response must be valid PDF'
print('SUCCESS: Valid PDF received, %PDF header confirmed!')
