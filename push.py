import json
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import re

# .envファイルから設定を読み込む
load_dotenv()

# FIWARE Orionの設定を.envから取得
authorization = os.getenv("FIWARE_AUTHORIZATION")
orion_endpoint = os.getenv("FIWARE_ORION_ENDPOINT")
Fiware_Service = os.getenv("FIWARE_SERVICE")
Fiware_ServicePath = os.getenv("FIWARE_SERVICE_PATH")
csv_url = os.getenv("CSV_URL")

# 現在時刻をUTCのISO形式で取得する関数
def getNowIsoFormatString():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

# 特殊文字や制御文字を除去する関数
def sanitize_value(value):
    if isinstance(value, str):
        value = re.sub(r'[^\w\s\-_.@/:;!]', '', value)
        value = re.sub(r'[\r\n\t]', ' ', value)
        value = value.strip()
    return value if value != '' else None

# 値をサニタイズし、適切な型に変換する関数
def get_sanitized_value(event_value, attribute_type):
    value = sanitize_value(event_value)
    if value is None:
        return None
    try:
        if attribute_type == "Number":
            number = float(value)
            if pd.isna(number) or pd.isnull(number):
                return None
            return number
        elif attribute_type == "DateTime":
            date_time = pd.to_datetime(value, utc=True)
            if pd.isna(date_time) or pd.isnull(date_time):
                return None
            return date_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            return value
    except (ValueError, TypeError):
        return None

# FIWARE Orionにデータを送信する関数
def DataSend(APIurl, PayLoad, method="post"):
    headers = {
        'Content-Type': 'application/json',
        'Fiware-Service': Fiware_Service,
        'Fiware-ServicePath': Fiware_ServicePath,
        'Authorization': authorization
    }
    try:
        payload_str = json.dumps(PayLoad, ensure_ascii=False, allow_nan=False)
        # print("Payload to send:", payload_str)
        if method == "post":
            response = requests.post(orion_endpoint + APIurl, headers=headers, data=payload_str)
        else:
            response = requests.patch(orion_endpoint + APIurl, headers=headers, data=payload_str)
        if response.status_code >= 400:
            print(f"Error {response.status_code}: Failed to send data to FIWARE Orion.")
            print("Response:", response.text)
        else:
            print(f"Success {response.status_code}: Data sent successfully to FIWARE Orion.")
        status = response.status_code
        response.close()
    except ValueError as e:
        print("JSON Serialization Error:", e)
        status = 0
    except Exception as e:
        print("Request Error:", e)
        status = 0
    return status

# エンティティが存在するか確認する関数
def check_entity_exists(entity_id):
    headers = {
        'Fiware-Service': Fiware_Service,
        'Fiware-ServicePath': Fiware_ServicePath,
        'Authorization': authorization
    }
    response = requests.get(orion_endpoint + f"/v2/entities/{entity_id}", headers=headers)
    exists = response.status_code == 200
    response.close()
    return exists

def main():
    # CSVデータをダウンロードして読み込む
    response = requests.get(csv_url)
    response.raise_for_status()
    csv_data = response.content.decode('cp932')
    events_df = pd.read_csv(pd.io.common.StringIO(csv_data))
    
    # '開始日'と'終了日'の列を日付型に変換
    events_df['開始日'] = pd.to_datetime(events_df['開始日'], errors='coerce')
    events_df['終了日'] = pd.to_datetime(events_df['終了日'], errors='coerce')
    
    # 明日の日付を取得（時間を含まない）
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    # 明日開催されるイベントをフィルタリング
    filtered_events = events_df[
        (
            # '終了日'が空欄の場合、'開始日'が明日と一致
            (events_df['終了日'].isna()) & (events_df['開始日'].dt.date == tomorrow)
        ) |
        (
            # '終了日'が存在する場合、明日が開始日と終了日の間に含まれる
            (events_df['終了日'].notna()) &
            (events_df['開始日'].dt.date <= tomorrow) &
            (events_df['終了日'].dt.date >= tomorrow)
        )
    ]
    
    # 各イベントをエンティティとしてFIWAREに送信
    for _, event in filtered_events.iterrows():
        event_data = {
            "id": f"Event_{event['NO']}",
            "type": "Event"
        }

        fields = {
            "prefecture_code": {"value": get_sanitized_value(event.get("都道府県コード又は市区町村コード"), "Number"), "type": "Number"},
            "event_no": {"value": get_sanitized_value(event.get("NO"), "Number"), "type": "Number"},
            "prefecture_name": {"value": get_sanitized_value(event.get("都道府県名"), "Text"), "type": "Text"},
            "city_name": {"value": get_sanitized_value(event.get("市区町村名"), "Text"), "type": "Text"},
            "event_name": {"value": get_sanitized_value(event.get("イベント名"), "Text"), "type": "Text"},
            "event_name_kana": {"value": get_sanitized_value(event.get("イベント名_カナ"), "Text"), "type": "Text"},
            "start_date": {"value": get_sanitized_value(event.get("開始日"), "DateTime"), "type": "DateTime"},
            "end_date": {"value": get_sanitized_value(event.get("終了日"), "DateTime"), "type": "DateTime"},
            "start_time": {"value": get_sanitized_value(event.get("開始時間"), "Text"), "type": "Text"},
            "end_time": {"value": get_sanitized_value(event.get("終了時間"), "Text"), "type": "Text"},
            "description": {"value": get_sanitized_value(event.get("説明"), "Text"), "type": "Text"},
            "basic_fee": {"value": get_sanitized_value(event.get("料金(基本)"), "Number"), "type": "Number"},
            "detailed_fee": {"value": get_sanitized_value(event.get("料金(詳細)"), "Text"), "type": "Text"},
            "contact_name": {"value": get_sanitized_value(event.get("連絡先名称"), "Text"), "type": "Text"},
            "contact_phone": {"value": get_sanitized_value(event.get("連絡先電話番号"), "Text"), "type": "Text"},
            "location_name": {"value": get_sanitized_value(event.get("場所名称"), "Text"), "type": "Text"},
            "address": {"value": get_sanitized_value(event.get("住所"), "Text"), "type": "Text"},
            "latitude": {"value": get_sanitized_value(event.get("緯度"), "Number"), "type": "Number"},
            "longitude": {"value": get_sanitized_value(event.get("経度"), "Number"), "type": "Number"},
            "registration_method": {"value": get_sanitized_value(event.get("参加申込方法"), "Text"), "type": "Text"},
            "category": {"value": get_sanitized_value(event.get("カテゴリー"), "Text"), "type": "Text"},
            "ward": {"value": get_sanitized_value(event.get("区"), "Text"), "type": "Text"},
            "published_date": {"value": get_sanitized_value(event.get("公開日"), "DateTime"), "type": "DateTime"},
            "facility_no": {"value": get_sanitized_value(event.get("施設No."), "Text"), "type": "Text"},
            "contact_extension": {"value": get_sanitized_value(event.get("連絡先内線番号"), "Text"), "type": "Text"},
            "organizer": {"value": get_sanitized_value(event.get("主催者"), "Text"), "type": "Text"},
            "address_note": {"value": get_sanitized_value(event.get("方書"), "Text"), "type": "Text"},
            "access_info": {"value": get_sanitized_value(event.get("アクセス方法"), "Text"), "type": "Text"},
            "parking_info": {"value": get_sanitized_value(event.get("駐車場情報"), "Text"), "type": "Text"},
            "capacity": {"value": get_sanitized_value(event.get("定員"), "Number"), "type": "Number"},
            "registration_end_date": {"value": get_sanitized_value(event.get("参加申込終了日"), "DateTime"), "type": "DateTime"},
            "registration_end_time": {"value": get_sanitized_value(event.get("参加申込終了時間"), "Text"), "type": "Text"},
            "child_info": {"value": get_sanitized_value(event.get("子育て情報"), "Text"), "type": "Text"},
            "updated_at": {"value": getNowIsoFormatString(), "type": "DateTime"}
        }

        # NoneおよびNaNではない属性のみを追加
        for key, field in fields.items():
            value = field["value"]
            if value is not None and value == value:  # NaNチェック
                event_data[key] = field

        entity_id = f"Event_{event['NO']}"
        if not check_entity_exists(entity_id):
            # 新しいエンティティを作成
            status = DataSend(APIurl="/v2/entities", PayLoad=event_data, method="post")
        else:
            # 更新用にidとtypeを削除
            update_data = event_data.copy()
            update_data.pop('id', None)
            update_data.pop('type', None)
            status = DataSend(APIurl=f"/v2/entities/{entity_id}/attrs", PayLoad=update_data, method="patch")

if __name__ == "__main__":
    main()
