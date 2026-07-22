"""네이버 금융 API로부터 ETF 시세 데이터를 수집하고 CSV 파일로 저장하는 모듈.

이 모듈은 네이버 금융의 ETF API를 호출하여 전체 ETF 종목 정보(종목코드, 종목명, 현재가,
변동률, 거래량, 시가총액 등)를 수집하고, 지정된 폴더에 CSV 파일 형식으로 저장합니다.
"""

from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional
import pandas as pd
import requests


def fetch_etf_data(url: str) -> List[Dict[str, Any]]:
    """네이버 금융 API를 호출하여 ETF 목록 데이터를 가져옵니다.

    JSONP 형태로 응답이 돌아올 경우 콜백 함수를 제거하여 순수 JSON 데이터만 추출합니다.

    Args:
        url (str): ETF 데이터를 가져올 네이버 금융 API URL.

    Returns:
        List[Dict[str, Any]]: ETF 종목 정보가 담긴 딕셔너리 리스트.

    Raises:
        requests.RequestException: HTTP 요청 실패 시 발생.
        ValueError: JSON 데이터 파싱 실패 시 발생.
    """
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    # API 요청 수행
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    content_text = response.text

    # _callback 파라미터로 인해 JSONP 형태일 경우 정규표현식으로 JSON 문자열만 추출
    jsonp_match = re.search(r'^\s*[\w\.]+\s*\((.*)\)\s*;?\s*$', content_text, re.DOTALL)
    if jsonp_match:
        json_str = jsonp_match.group(1)
    else:
        json_str = content_text

    # JSON 데이터 파싱
    data = json.loads(json_str)

    # API 응답 구조 검증 및 etfItemList 반환
    result = data.get('result', {})
    etf_item_list = result.get('etfItemList', [])

    if not etf_item_list:
        raise ValueError("API 응답에서 etfItemList 데이터를 찾을 수 없습니다.")

    return etf_item_list


def save_to_csv(etf_items: List[Dict[str, Any]], output_dir: str = "data") -> str:
    """수집된 ETF 목록 데이터를 pandas DataFrame으로 변환하여 CSV 파일로 저장합니다.

    한글 깨짐 방지를 위해 'utf-8-sig' 인코딩을 사용하며,
    최신 데이터 파일(etf_data_latest.csv) 및 타임스탬프 파일명을 모두 생성합니다.

    Args:
        etf_items (List[Dict[str, Any]]): 수집된 ETF 종목 데이터 리스트.
        output_dir (str, optional): CSV 파일이 저장될 상대/절대 경로. 기본값은 "data".

    Returns:
        str: 생성된 타임스탬프 CSV 파일의 상대 경로.
    """
    # 저장 디렉토리가 없는 경우 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # DataFrame 생성 및 컬럼명 한국어 직관화
    df = pd.DataFrame(etf_items)

    # 수집 시각 컬럼 추가
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df['collected_at'] = now_str

    # 저장할 파일명 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_filename = os.path.join(output_dir, f"etf_data_{timestamp}.csv")
    latest_filename = os.path.join(output_dir, "etf_data_latest.csv")

    # CSV 파일로 저장 (utf-8-sig로 저장하여 엑셀 호환성 확보)
    df.to_csv(timestamp_filename, index=False, encoding='utf-8-sig')
    df.to_csv(latest_filename, index=False, encoding='utf-8-sig')

    return timestamp_filename


def main() -> None:
    """ETF 데이터 수집 및 저장 메인 프로세스를 실행합니다."""
    target_url = (
        "https://finance.naver.com/api/sise/etfItemList.nhn?"
        "etfType=0&targetColumn=market_sum&sortOrder=desc&"
        "_callback=window.__jindo2_callback._2052"
    )

    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ETF 데이터 수집 시작...")
        etf_data = fetch_etf_data(target_url)
        saved_path = save_to_csv(etf_data, output_dir="data")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 성공적으로 저장되었습니다: {saved_path} (총 {len(etf_data)}건)")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 데이터 수집 실패: {e}")


if __name__ == "__main__":
    main()
