import os
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def main():
    credentials_path = 'credentials.json'
    token_path = 'token.json'
    
    if not os.path.exists(credentials_path):
        print(f"Error: {credentials_path} not found. Make sure you are running this in the backend directory.")
        return
        
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    print("Starting authentication server... A browser window should open shortly.")
    creds = flow.run_local_server(port=0)
    
    with open(token_path, 'w') as token:
        token.write(creds.to_json())
        
    print(f"Success! Credentials saved to {token_path}")

if __name__ == '__main__':
    main()
