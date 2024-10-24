import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime

SCOPES = ["https://www.googleapis.com/auth/drive"]

def check_token_status():
    """檢查 Google Drive 權杖狀態"""
    try:
        # 檢查 token.json 是否存在
        if not os.path.exists("token.json"):
            print("未找到 token.json 檔案！需要重新進行授權。")
            return False
        
        # 讀取憑證
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception as e:
            print(f"讀取 token.json 時發生錯誤: {e}")
            return False

        # 檢查憑證是否有效
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    print("權杖已過期，嘗試更新...")
                    creds.refresh(Request())
                    # 保存更新後的權杖
                    with open("token.json", "w") as token:
                        token.write(creds.to_json())
                    print("權杖已成功更新！")
                    return True
                except Exception as e:
                    print(f"更新權杖時發生錯誤: {e}")
                    return False
            else:
                print("權杖無效且無法更新，需要重新授權。")
                return False
        
        # 測試連接
        try:
            service = build("drive", "v3", credentials=creds)
            # 嘗試列出檔案以驗證連接
            service.files().list(pageSize=1).execute()
            print("權杖狀態正常！可以使用。")
            
            # 顯示過期時間（如果可用）
            if hasattr(creds, 'expiry'):
                expiry_time = creds.expiry
                now = datetime.datetime.now(expiry_time.tzinfo)
                time_left = expiry_time - now
                print(f"權杖將在 {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} 過期")
                print(f"剩餘時間: {time_left}")
            
            return True
            
        except HttpError as error:
            print(f"測試連接時發生錯誤: {error}")
            return False
            
    except Exception as e:
        print(f"檢查過程中發生未預期的錯誤: {e}")
        return False

def main():
    print("=== Google Drive 權杖狀態檢查工具 ===")
    result = check_token_status()
    
    if not result:
        print("\n建議操作：")
        print("1. 刪除現有的 token.json 檔案（如果存在）")
        print("2. 重新執行主程式進行授權")
        print("3. 確保您有穩定的網路連接")
        # 如果檔案存在則嘗試刪除
        if os.path.exists("token.json"):
            try:
                os.remove("token.json")
                print("\n已自動刪除失效的 token.json 檔案")
            except Exception as e:
                print(f"\n刪除 token.json 時發生錯誤: {e}")
                print("請手動刪除 token.json 檔案")

if __name__ == "__main__":
    main()