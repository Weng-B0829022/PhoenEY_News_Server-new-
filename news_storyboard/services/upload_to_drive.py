import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tqdm import tqdm

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def create_folder(service, folder_name, parent_id=None):
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [parent_id]
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def upload_file(service, filename, filepath, parent_id):
    file_metadata = {'name': filename, 'parents': [parent_id]}
    media = MediaFileUpload(filepath, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def count_files(folder_path):
    total_files = 0
    for root, dirs, files in os.walk(folder_path):
        total_files += len(files)
    return total_files

def upload_folder_contents(service, folder_path, parent_id, pbar):
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path):
            upload_file(service, item, item_path, parent_id)
            pbar.update(1)
        elif os.path.isdir(item_path):
            subfolder_id = create_folder(service, item, parent_id)
            upload_folder_contents(service, item_path, subfolder_id, pbar)

def find_folder(service, folder_name):
    results = service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None

def upload_to_drive(local_folder_path):
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)
    #print(local_folder_path)
    try:
        # 找到 "generated" 文件夾
        generated_folder_id = find_folder(service, "generated")
        if not generated_folder_id:
            print("無法找到 'generated' 文件夾。請確保該文件夾存在於您的 Google Drive 中。")
            return None

        total_files = count_files(local_folder_path)
        
        print(f"準備上傳 {total_files} 個文件到 'generated' 文件夾...")
        
        data_id = os.path.basename(local_folder_path)
        # 在 "generated" 文件夾中創建新文件夾
        folder_id = create_folder(service, data_id, generated_folder_id)
        
        # 使用 tqdm 創建進度條
        with tqdm(total=total_files, unit='file') as pbar:
            # 上傳 data_id 資料夾內的所有內容
            upload_folder_contents(service, local_folder_path, folder_id, pbar)
        
        print("所有文件和資料夾上傳完成。")
        return folder_id
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None
