import os
import os.path
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tqdm import tqdm

SCOPES = ["https://www.googleapis.com/auth/drive"]
MAX_RETRIES = 3
RETRY_DELAY = 5

def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print(f"讀取token時發生錯誤: {e}")
            os.remove("token.json")
    
    try:
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"刷新token失敗: {e}")
                    creds = None
            
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open("token.json", "w") as token:
                token.write(creds.to_json())
    except Exception as e:
        print(f"獲取憑證時發生錯誤: {e}")
        raise

    return creds

def create_folder_with_retry(service, folder_name, parent_id=None):
    for attempt in range(MAX_RETRIES):
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')
        except HttpError as error:
            if error.resp.status in [403, 429, 500, 503]:  # Rate limit or server errors
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
            raise
        except Exception as e:
            print(f"創建資料夾時發生錯誤: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise

def upload_file_with_retry(service, filename, filepath, parent_id):
    for attempt in range(MAX_RETRIES):
        try:
            file_metadata = {'name': filename, 'parents': [parent_id]}
            media = MediaFileUpload(filepath, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except HttpError as error:
            if error.resp.status in [403, 429, 500, 503]:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
            raise
        except Exception as e:
            print(f"上傳檔案 {filename} 時發生錯誤: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise

def count_files(folder_path):
    try:
        total_files = 0
        for root, dirs, files in os.walk(folder_path):
            total_files += len(files)
        return total_files
    except Exception as e:
        print(f"計算檔案數量時發生錯誤: {e}")
        raise

def upload_folder_contents(service, folder_path, parent_id, pbar):
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            try:
                if os.path.isfile(item_path):
                    upload_file_with_retry(service, item, item_path, parent_id)
                    pbar.update(1)
                elif os.path.isdir(item_path):
                    subfolder_id = create_folder_with_retry(service, item, parent_id)
                    upload_folder_contents(service, item_path, subfolder_id, pbar)
            except Exception as e:
                print(f"處理檔案 {item} 時發生錯誤: {e}")
                continue
    except Exception as e:
        print(f"讀取資料夾內容時發生錯誤: {e}")
        raise

def find_folder_with_retry(service, folder_name):
    for attempt in range(MAX_RETRIES):
        try:
            results = service.files().list(
                q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            items = results.get('files', [])
            return items[0]['id'] if items else None
        except HttpError as error:
            if error.resp.status in [403, 429, 500, 503]:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
            raise
        except Exception as e:
            print(f"查找資料夾時發生錯誤: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise

def upload_to_drive(local_folder_path):
    try:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)
        
        # 查找 "generated" 資料夾
        generated_folder_id = find_folder_with_retry(service, "generated")
        if not generated_folder_id:
            print("無法找到 'generated' 資料夾。請確保該資料夾存在於您的 Google Drive 中。")
            return None
        
        total_files = count_files(local_folder_path)
        print(f"準備上傳 {total_files} 個檔案到 'generated' 資料夾...")
        
        data_id = os.path.basename(local_folder_path)
        folder_id = create_folder_with_retry(service, data_id, generated_folder_id)
        
        with tqdm(total=total_files, unit='file') as pbar:
            upload_folder_contents(service, local_folder_path, folder_id, pbar)
        
        print("所有檔案和資料夾上傳完成。")
        return folder_id
    
    except HttpError as error:
        if 'invalid_grant' in str(error):
            print("授權權杖已過期，請刪除 token.json 檔案並重新運行程式進行授權。")
            if os.path.exists("token.json"):
                os.remove("token.json")
        else:
            print(f"發生 Google Drive API 錯誤: {error}")
        return None
    except Exception as e:
        print(f"上傳過程中發生錯誤: {e}")
        return None