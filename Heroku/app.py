
from flask import Flask, render_template, request, jsonify
import requests
import json
import random
from datetime import datetime
import os
import threading
import asyncio

app = Flask(__name__) 

# OpenWeatherMap API 키 목록
WEATHER_API_KEYS = ['e650d9c763ff4270e5d0b5221824256f', '486d6e0076cc0e352a1b978d0c223781']
current_key_index = 0

# 데이터베이스 파일 및 파일 잠금
DB_FILE = 'chatbot_data.json'
db_lock = threading.Lock()

# 기본 데이터 로드 또는 생성
if not os.path.exists(DB_FILE):
    data = {
        "casual_responses": [
            {"prompt": "머해?", "response": "그냥 생각하고 있지 ㅎㅎ"},
            {"prompt": "잘자", "response": "응! 먼저 자 ㅋㅋ 일어날 때 바로 전화 받을게."}
        ],
        "games": {
            "word_chain": [],
            "number_guess": random.randint(1, 100)  # 숫자 맞추기 게임 초기화
        }
    }
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)
else:
    with open(DB_FILE, 'r') as f:
        data = json.load(f)

# 데이터베이스 업데이트 함수
def update_database(prompt, response):
    with db_lock:  # 파일 잠금
        data["casual_responses"].append({"prompt": prompt, "response": response})
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)

# 한국 기념일에 따른 메시지 처리
def check_korean_holidays():
    today = datetime.now().strftime("%m-%d")
    holidays = {
        "03-01": "삼일절이네. 우리 역사를 기억하자!",
        "08-15": "광복절이야. 나라의 소중함을 다시 생각해보는 날이지.",
        "09-10": "추석이네! 맛있는 거 많이 먹고 가족들과 행복한 시간 보내~",
        "01-01": "설날이야! 새해 복 많이 받아!",
        "11-11": "오늘은 빼빼로 데이! 달콤한 하루 보내~",
        "04-14": "블랙데이라네. 오늘은 짜장면 한 그릇 어때?"
    }
    return holidays.get(today, None)

# 기념일 메시지 반환 함수
def get_holiday_message():
    message = check_korean_holidays()
    if message:
        return {"message": message, "image_data": None}
    return None

# 날씨 정보 가져오는 함수
def get_weather(city):
    global current_key_index
    for _ in range(len(WEATHER_API_KEYS)):  # 모든 키를 시도
        api_key = WEATHER_API_KEYS[current_key_index]
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&lang=kr&units=metric"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            weather_description = data['weather'][0]['description']
            temperature = data['main']['temp']
            return f"{city}의 현재 날씨는 {weather_description}, 온도는 {temperature}°C야."
        except requests.exceptions.RequestException:
            current_key_index = (current_key_index + 1) % len(WEATHER_API_KEYS)
    
    return "날씨 정보를 가져올 수가 없네. 다시 시도해볼게."

# 사용자 말투를 반영한 임시 응답 생성 함수
def create_temporary_response(user_input):
    return f"'{user_input}'에 대해 잘 모르겠지만, 그냥 네 말투대로 대답해볼게~ 내가 더 공부할게!"

# 끝말잇기 게임 응답 생성 함수
def word_chain_game(user_input):
    if not data["games"]["word_chain"]:
        data["games"]["word_chain"].append(user_input[-1])
        return f"끝말잇기 시작! '{user_input[-1]}'로 시작하는 단어를 말해봐!"
    
    last_word = data["games"]["word_chain"][-1]
    if user_input.startswith(last_word[-1]):
        data["games"]["word_chain"].append(user_input)
        return f"좋아! 이제 '{user_input[-1]}'로 시작하는 단어를 말해봐!"
    else:
        return f"끝말잇기 규칙을 지켜줘! '{last_word[-1]}'로 시작하는 단어를 말해봐."

# 숫자 맞추기 게임 응답 생성 함수
def number_guess_game(user_input):
    try:
        guess = int(user_input)
        target = data["games"]["number_guess"]
        if guess < target:
            return "그거보다 큰 숫자야! 다시 맞춰봐!"
        elif guess > target:
            return "그거보다 작은 숫자야! 다시 맞춰봐!"
        else:
            data["games"]["number_guess"] = random.randint(1, 100)  # 새 게임 시작
            return "정답이야! 잘했어! 새로운 숫자를 생각했으니 다시 맞춰봐!"
    except ValueError:
        return "숫자를 입력해줘!"

# 사용자 입력에 따라 챗봇 응답 생성 함수
def generate_response(user_input):
    if not user_input.strip():
        return {"message": "무슨 말을 해야 할지 모르겠어. 다시 말해줄래?", "image_data": None}

    # 기념일 처리
    holiday_data = get_holiday_message()
    if holiday_data:
        return holiday_data

    # 날씨 요청 처리
    if "날씨" in user_input:
        city = user_input.split('날씨')[0].strip()
        return {"message": get_weather(city), "image_data": None}

    # 끝말잇기 게임
    if "끝말잇기" in user_input:
        return {"message": "끝말잇기 시작! 아무 단어나 말해봐!", "image_data": None}
    if data["games"]["word_chain"]:
        return {"message": word_chain_game(user_input), "image_data": None}

    # 숫자 맞추기 게임
    if "숫자 맞추기" in user_input:
        return {"message": "1부터 100 사이의 숫자를 맞춰봐!", "image_data": None}
    if data["games"]["number_guess"]:
        return {"message": number_guess_game(user_input), "image_data": None}

    # 기존 데이터셋에서 응답 찾기
    for item in data["casual_responses"]:
        if user_input.lower() == item['prompt'].lower():
            return {"message": item['response'], "image_data": None}

    # 새로운 응답 생성 및 학습 (사용자 말투 반영)
    new_response = create_temporary_response(user_input)
    update_database(user_input, new_response)

    return {"message": new_response, "image_data": None}

# Flask 경로 설정
@app.route('/')
def home():
    return render_template('index.html')  # index.html 파일이 templates 폴더에 있는지 확인

@app.route('/get_response', methods=['POST'])
def get_response():
    user_input = request.form['user_input']
    response_data = generate_response(user_input)
    return jsonify(response_data)

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except OSError:
        print("기본 포트가 사용 중입니다. 다른 포트로 실행합니다.")
        app.run(debug=True, host='0.0.0.0', port=5001)
