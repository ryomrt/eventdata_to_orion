import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import sys

# .envファイルから設定を読み込む
load_dotenv()

# FIWARE Orionの設定を.envから取得
authorization = os.getenv("FIWARE_AUTHORIZATION")
orion_endpoint = os.getenv("FIWARE_ORION_ENDPOINT")
fiware_service = os.getenv("FIWARE_SERVICE")
fiware_service_path = os.getenv("FIWARE_SERVICE_PATH")

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

    # 日付のフォーマットを確認
    try:
        datetime.strptime(specified_date_str, '%Y-%m-%d')
    except ValueError:
        print("日付の形式が正しくありません。YYYY-MM-DD形式で指定してください。")
        sys.exit(1)

    # FIWARE Orionからイベントデータを取得
    headers = {
        'Fiware-Service': fiware_service,
        'Fiware-ServicePath': fiware_service_path,
    }
    if authorization:
        headers['Authorization'] = authorization

    # クエリパラメータの作成（値をクォーテーションで囲まない）
    q1 = f"start_date<={specified_date_str};end_date>={specified_date_str}"
    q2 = f"start_date=={specified_date_str};!end_date"

    params1 = {
        'type': 'Event',
        'options': 'keyValues',
        'limit': '1000',
        'q': q1
    }

    params2 = {
        'type': 'Event',
        'options': 'keyValues',
        'limit': '1000',
        'q': q2
    }

    # 最初のクエリを実行
    response1 = requests.get(orion_endpoint + "/v2/entities", headers=headers, params=params1)
    if response1.status_code != 200:
        print(f"Error {response1.status_code}: {response1.text}")
        sys.exit(1)
    events1 = response1.json()

    # 2つ目のクエリを実行
    response2 = requests.get(orion_endpoint + "/v2/entities", headers=headers, params=params2)
    if response2.status_code != 200:
        print(f"Error {response2.status_code}: {response2.text}")
        sys.exit(1)
    events2 = response2.json()

    # 結果を結合し、IDで重複を排除
    all_events = {event['id']: event for event in events1 + events2}
    events = list(all_events.values())

    print(f"Retrieved {len(events)} events from FIWARE Orion.")

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

    # イベント情報を収集し、日本語の項目名で出力
    filtered_events = []
    for event in events:
        event_info = {}
        for japanese_key, english_key in attribute_mapping.items():
            value = sanitize_value(event.get(english_key))
            if english_key in ['start_date', 'end_date', 'registration_end_date', 'published_date', 'updated_at']:
                # 日付をYYYY-MM-DD形式に変換
                if value:
                    try:
                        date_value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
                        value = date_value.strftime('%Y-%m-%d')
                    except ValueError:
                        value = None
            event_info[japanese_key] = value
        filtered_events.append(event_info)

    # JSONをファイルに書き込む
    output_filename = f"events_{specified_date_str}.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(filtered_events, f, ensure_ascii=False, indent=4)
    print(f"イベントデータを'{output_filename}'に出力しました。")

if __name__ == "__main__":
    main()
