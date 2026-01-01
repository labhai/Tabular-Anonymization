# 고수준 익명화 정책

policy_high = {
    # 환자 ID / 보험 ID / 방문 ID / 진료 ID 등: 삭제
    "id": "drop",                       
    "patient_id": "drop",
    "insurance_id": "drop",
    "encounter_id": "drop",

    # 주민등록번호 / 운전면허 / 여권 등: 삭제
    "ssn": "drop",
    "driver_license": "drop",
    "passport": "drop",

    # 이름: 삭제
    "name": "drop",

    # 생년월일 / 사망일: 10년 단위 절삭
    #   예: 2025-11-03 → 2020-01-01
    "birthdate": "date_floor_decade",
    "deathdate": "date_floor_decade",

    # 방문일자: 연 단위 절삭
    #   예: 2025-11-03 → 2025-01-01
    "visit_date": "date_floor_year",

    # 나이/성별: 삭제
    "age": "drop",         
    "gender": "drop",              

    # 혼인 상태: 호칭 단순화
    "marital_status": "normalize_marital_prefix",

    # 인종 / 민족: 유지
    "race": "keep",
    "ethnicity": "keep",

    # 주소 텍스트: 행정시 단위 일반화
    "address": "region_generalize",

    # 우편번호: 일부 마스킹
    "zipcode": "mask_zip_leading",

    # 좌표: 삭제
    "location": "drop",

    # 진단명: 허용 시 유지
    "diagnosis": "keep_if_permitted_else_drop",

    # 검사 결과 / 측정값: 유지
    "measurement": "keep",

    # 재무 정보: 삭제
    "finance": "drop",

    # 자유기재 코멘트/노트: 삭제
    "comment": "drop",
    "note": "drop",

    # 기타 항목: 유지
    "other": "keep",
}
