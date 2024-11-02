import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import sys
from dateutil import parser

# .envファイルから設定を読み込む
load_dotenv()

# FIWARE Orionの設定を.envから取得
authorization = os.getenv("FIWARE_AUTHORIZATION")
orion_endpoint = os.getenv("FIWARE_ORION_ENDPOINT")
Fiware_Service = os.getenv("FIWARE_SERVICE")
Fiware_ServicePath = os.getenv("FIWARE_SERVICE_PATH")

# 特殊文字や制御文字を除去する関数
def sanitize_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return value

def main():
    # コマンドライン引数から日付を取得（YYYY-MM-DD形式）
    if len(sys.argv) < 2:
        print("使用法: python script.py YYYY-MM-DD")
        sys.exit(1)
    specified_date_str = sys.argv[1]
    try:
        specified_date = datetime.strptime(specified_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("日付の形式が正しくありません。YYYY-MM-DD形式で指定してください。")
        sys.exit(1)

    # FIWARE Orionからイベントデータを取得
    headers = {
        'Fiware-Service': Fiware_Service,
        'Fiware-ServicePath': Fiware_ServicePath,
    }
    if authorization:
        headers['Authorization'] = authorization

    params = {
        'type': 'Event',
        'options': 'keyValues'
    }
    response = requests.get(orion_endpoint + "/v2/entities", headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error {response.status_code}: Failed to retrieve data from FIWARE Orion.")
        print("Response:", response.text)
        sys.exit(1)
    events = response.json()

    print(f"Retrieved {len(events)} events from FIWARE Orion.")

    # イベントデータの構造を確認
    if events:
        print("Sample event data:")
        print(json.dumps(events[0], ensure_ascii=False, indent=4))
    else:
        print("No events found.")
        sys.exit(0)

    # 属性名のマッピングを作成
    attribute_mapping = {
        "都道府県コード又は市区町村コード": "prefecture_code",
        "NO": "event_no",
        "都道府県名": "prefecture_name",
        "市区町村名": "city_name",
        "イベント名": "event_name",
        "イベント名_カナ": "event_name_kana",
        "イベント名_英語": "event_name_english",
        "開始日": "start_date",
        "終了日": "end_date",
        "開始時間": "start_time",
        "終了時間": "end_time",
        "開始日時特記事項": "start_date_note",
        "説明": "description",
        "料金(基本)": "basic_fee",
        "料金(詳細)": "detailed_fee",
        "連絡先名称": "contact_name",
        "連絡先電話番号": "contact_phone",
        "連絡先内線番号": "contact_extension",
        "主催者": "organizer",
        "場所名称": "location_name",
        "住所": "address",
        "方書": "address_note",
        "緯度": "latitude",
        "経度": "longitude",
        "アクセス方法": "access_info",
        "駐車場情報": "parking_info",
        "定員": "capacity",
        "参加申込終了日": "registration_end_date",
        "参加申込終了時間": "registration_end_time",
        "参加申込方法": "registration_method",
        "URL": "URL",
        "備考": "note",
        "カテゴリー": "category",
        "区": "ward",
        "公開日": "published_date",
        "更新日": "updated_at",
        "子育て情報": "child_info",
        "施設No.": "facility_no"
    }

    # 指定された日付のイベントをフィルタリング
    filtered_events = []
    for event in events:
        start_date_str = event.get('start_date')
        end_date_str = event.get('end_date')

        # 日付のパース
        try:
            start_date = parser.isoparse(start_date_str).date() if start_date_str else None
            end_date = parser.isoparse(end_date_str).date() if end_date_str else None
        except (ValueError, TypeError):
            continue  # 日付の形式が不正な場合はスキップ

        # フィルタリング条件
        if (end_date is None and start_date == specified_date) or \
           (end_date is not None and start_date <= specified_date <= end_date):
            # イベント情報を収集
            event_info = {}
            for japanese_key, english_key in attribute_mapping.items():
                value = sanitize_value(event.get(english_key))
                if english_key in ['start_date', 'end_date', 'registration_end_date', 'published_date', 'updated_at']:
                    # 日付をYYYY-MM-DD形式に変換
                    if value:
                        try:
                            date_value = parser.isoparse(value).date()
                            value = date_value.strftime('%Y-%m-%d')
                        except (ValueError, TypeError):
                            value = None
                event_info[japanese_key] = value
            filtered_events.append(event_info)

    # JSON出力
    print(json.dumps(filtered_events, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    main()
