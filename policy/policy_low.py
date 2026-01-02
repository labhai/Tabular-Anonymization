# 저수준 익명화 정책

policy_low = {
    # 환자 ID / 보험 ID / 방문 ID / 진료 ID 등: 가명화
    "id": "pseudonymize",                # 예: 123456 → a83c1b
    "patient_id": "pseudonymize",
    "insurance_id": "pseudonymize",
    "encounter_id": "pseudonymize",

    # 주민등록번호 / 운전면허 / 여권 등: 삭제
    "ssn": "drop",
    "driver_license": "drop",
    "passport": "drop",

    # 이름: 가명화
    "name": "pseudonymize",              # 예: 홍길동 → 홍00

    # 생년월일 / 사망일: 연 단위 절삭
    "birthdate": "date_floor_year",
    "deathdate": "date_floor_year",

    # 방문일자: 연 단위 절삭
    "visit_date": "date_floor_year",

    # 나이/성별/혼인 상태/인종·민족: 유지
    "age": "keep",                 
    "gender": "keep",                
    "marital_status": "keep",       
    "race": "keep",
    "ethnicity": "keep",

    # 주소 텍스트: 행정구 단위 일반화
    "address": "region_generalize",

    # 우편번호: 일부 마스킹
    "zipcode": "mask_zip_leading",    

    # 좌표/위치좌표: 삭제
    "location": "drop",

    # 진단명/진단코드: 허용 시 유지
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
