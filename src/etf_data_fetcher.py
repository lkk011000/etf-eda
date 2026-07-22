"""네이버 금융 API로부터 ETF 데이터를 실시간 메모리 수집하고 전처리하는 모듈.

이 모듈은 네이버 금융 ETF API를 실시간 호출하여 로컬 파일 저장 없이
메모리 상에서 데이터를 수집하고, 브랜드 추출, 테마 분류, NAV 괴리율 계산 등
EDA 분석에 필요한 다양한 파생 변수를 생성하여 pandas DataFrame으로 반환합니다.
"""

from datetime import datetime
import json
import re
from typing import Any, Dict, List
import pandas as pd
import requests

# 네이버 금융 ETF API URL
NAVER_ETF_API_URL: str = (
    "https://finance.naver.com/api/sise/etfItemList.nhn?"
    "etfType=0&targetColumn=market_sum&sortOrder=desc&"
    "_callback=window.__jindo2_callback._2052"
)


def fetch_raw_etf_data(url: str = NAVER_ETF_API_URL) -> List[Dict[str, Any]]:
    """네이버 금융 API를 호출하여 원본 ETF 종목 리스트 데이터를 메모리로 가져옵니다.

    API 응답이 JSONP 형태일 경우 정규표현식을 이용하여 순수 JSON 문자열만 추출 후 파싱합니다.
    로컬 파일 저장은 일절 수행하지 않습니다.

    Args:
        url (str, optional): 요청을 보낼 네이버 금융 ETF API URL.

    Returns:
        List[Dict[str, Any]]: ETF 종목 정보가 포함된 딕셔너리 리스트.

    Raises:
        requests.RequestException: 네트워크 통신 문제 또는 HTTP 에러 발생 시.
        ValueError: JSON 데이터 파싱 실패 또는 etfItemList 항목 미존재 시.
    """
    headers: Dict[str, str] = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    # API HTTP 요청 수행 (타임아웃 10초)
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    content_text = response.text

    # JSONP 응답 패터닝 제거 (window.__jindo2_callback._2052(...) 형태)
    jsonp_match = re.search(r'^\s*[\w\.]+\s*\((.*)\)\s*;?\s*$', content_text, re.DOTALL)
    if jsonp_match:
        json_str = jsonp_match.group(1)
    else:
        json_str = content_text

    # JSON 데이터 객체로 변환
    data = json.loads(json_str)
    result = data.get('result', {})
    etf_item_list = result.get('etfItemList', [])

    if not etf_item_list:
        raise ValueError("네이버 금융 API 응답에서 etfItemList를 찾을 수 없습니다.")

    return etf_item_list


def extract_brand(itemname: str) -> str:
    """ETF 종목명에서 자산운용사 브랜드명을 추출합니다.

    Args:
        itemname (str): ETF 종목명 (예: 'KODEX 200', 'TIGER 미국S&P500')

    Returns:
        str: 추출된 브랜드명 (매칭되지 않을 경우 '기타')
    """
    known_brands = [
        'KODEX', 'TIGER', 'ACE', 'RISE', 'SOL', 'PLUS', 'HANARO', 'KOSEF',
        'WOORI', 'TIMEFOLIO', 'HERO', 'ARIRANG', 'KBSTAR', 'FOCUS', 'UNICORN',
        'WON', 'FIRST', 'KoAct', 'TRUSTON', 'Mighty', 'HK', '파워'
    ]

    tokens = itemname.split()
    if tokens:
        first_token = tokens[0]
        for brand in known_brands:
            if first_token.upper() == brand.upper():
                return brand
    return '기타'


def classify_theme(itemname: str) -> str:
    """ETF 종목명 키워드를 기반으로 자산/테마 유형을 자동 분류합니다.

    Args:
        itemname (str): ETF 종목명

    Returns:
        str: 분류된 테마 범주명
    """
    name_upper = itemname.upper()

    # 1. 파생 / 채권 / 금리
    if any(k in name_upper for k in ['2X', '레버리지', '인버스', '선물']):
        return '레버리지/인버스'
    if any(k in name_upper for k in ['채권', 'KTB', '국고채', '통안채', 'CD금리', 'KOFR', 'SOFR', '금리', '액티브채권']):
        return '채권/금리'
    if any(k in name_upper for k in ['커버드콜', '옵션', '타겟위클리', '타깃일간']):
        return '커버드콜/파생'

    # 2. 해외 / 지역
    if any(k in name_upper for k in ['미국', 'S&P500', '나스닥', 'NASDAQ', '차이나', '중국', '글로벌', '일본', 'TOPIX', '베트남', '인도']):
        return '해외주식'

    # 3. 주요 섹터 / 테마
    if any(k in name_upper for k in ['반도체', 'SOXX', 'AI', '인공지능', '테크', '빅테크', '소프트웨어']):
        return '반도체/AI/IT'
    if any(k in name_upper for k in ['2차전지', '배터리', '전기차']):
        return '2차전지/전기차'
    if any(k in name_upper for k in ['배당', '고배당', 'DIVIDEND', 'SCHD', '리츠']):
        return '배당/리츠'
    if any(k in name_upper for k in ['바이오', '헬스케어', '제약']):
        return '바이오/헬스케어'
    if any(k in name_upper for k in ['조선', '방산', '원자재', '원유', '골드', '금', '신재생']):
        return '산업/원자재'

    # 4. 국내 대표지수
    if any(k in name_upper for k in ['200', '코스닥150', 'KRX300', '대표', 'TOP10', '블루칩']):
        return '국내 대표지수'

    return '기타 주식/테마'


def get_live_etf_dataframe() -> pd.DataFrame:
    """실시간 API 데이터를 수집하고 파생변수를 추가하여 전처리된 DataFrame을 반환합니다.

    데이터는 오직 메모리(pandas DataFrame)에만 보관되며, 로컬 파일로 저장되지 않습니다.

    Returns:
        pd.DataFrame: 전처리가 완료된 ETF 종목 데이터프레임.
    """
    raw_data = fetch_raw_etf_data()
    df = pd.DataFrame(raw_data)

    # 수집 시각 기록 (메모리 칼럼)
    collected_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df['collected_at'] = collected_time

    # 숫자형 데이터 타입 변환 및 예외 처리
    numeric_cols = ['nowVal', 'changeVal', 'changeRate', 'nav', 'threeMonthEarnRate', 'quant', 'amonut', 'marketSum']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 1. 파생변수: 운용사 브랜드 & 테마 분류
    df['brand'] = df['itemname'].apply(extract_brand)
    df['theme'] = df['itemname'].apply(classify_theme)

    # 2. 파생변수: 금액 단위 조정 (억원 단위)
    # marketSum: 억원 단위 이미 제공됨
    # amonut: 백만원 단위 -> 억원 단위로 변환 (1 억원 = 100 백만원)
    df['amount_uk'] = df['amonut'] / 100.0

    # 3. 파생변수: NAV 대비 괴리금액 및 괴리율(%)
    df['nav_diff'] = df['nowVal'] - df['nav']
    df['nav_gap_rate'] = df.apply(
        lambda row: ((row['nowVal'] - row['nav']) / row['nav'] * 100.0) if row['nav'] > 0 else 0.0,
        axis=1
    )

    # 4. 등락 상태 명칭 부여 (risefall)
    risefall_map = {
        '1': '상한가',
        '2': '상승',
        '3': '보합',
        '4': '하한가',
        '5': '하락'
    }
    df['risefall_name'] = df['risefall'].astype(str).map(risefall_map).fillna('기타')

    return df
