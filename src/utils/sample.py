


import requests

webhook_url = "https://www.quantman.trade/external_signal/bnh3ZDZVSGRlM2RpaldGd1RoNHg3dG55QlJWZlRjNDdZSlhaaHk0aWZUYXNGMnhYZVNsYnZ3cy9CbE95V2xaRjgyQ2VOZFVQS1RlN09lNjBLTWcxNmc9PS0tajVPNXFRcFBmUlVMeUJuN3d5RXMyUT09--ab7cb8f2961a31627b42cf647160be6291a9eb2b"

data = {
    "event": "user_signup",
    "user": "john_doe",
    "email": "john@example.com"
}

response = requests.post(webhook_url, json=data)

print("Status Code:", response.status_code)
print("Response:", response.text)