import json
import time
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, InvalidSessionIdException, WebDriverException
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

# 명령행 인자 파싱 설정
parser = argparse.ArgumentParser(description="충남대학교 컴퓨터융합학부 일반 공지글 크롤러")
parser.add_argument("--start_date", type=str, required=True, help="크롤링 시작 날짜 (YY.MM.DD 형식, 예: 25.07.01)")
parser.add_argument("--end_date", type=str, required=True, help="크롤링 종료 날짜 (YY.MM.DD 형식, 예: 25.07.24)")
args = parser.parse_args()

# 날짜 형식 변환
start_date = datetime.strptime(args.start_date, '%y.%m.%d').date()
end_date = datetime.strptime(args.end_date, '%y.%m.%d').date()

# 웹 드라이버 설정 함수
def create_driver():
    service = Service(executable_path='E:\Program Files\chromedriver-win64\chromedriver.exe')
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.page_load_strategy = 'eager'
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(300)
    return driver

# **로그인 기능 추가**
def perform_login(driver):
    print("로그인을 시도합니다...")

    # 환경 변수에서 아이디와 비밀번호를 가져옵니다.
    # YOUR_ID 및 YOUR_PASSWORD 부분은 실제 값으로 변경해야 합니다.
    login_id = os.getenv("WEBSITE_ID")
    login_pw = os.getenv("WEBSITE_PW")
    
    if not login_id or not login_pw:
        raise ValueError("환경 변수 WEBSITE_ID 또는 WEBSITE_PW가 설정되지 않았습니다.")

    # TODO: 로그인 페이지 URL로 변경해야 합니다.
    login_url = "https://computer.cnu.ac.kr/computer/etc/login.do"  
    driver.get(login_url)

    try:
        # TODO: 아이디, 비밀번호 입력창 및 로그인 버튼의 CSS 선택자 또는 Xpath로 변경해야 합니다.
        # 예시: 'id_input_field'는 실제 로그인 페이지의 아이디 필드 ID로 변경
        id_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'memberId')) 
        )
        pw_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'memberPw'))
        )
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="loginForm"]/fieldset/button'))
        )

        id_field.send_keys(login_id)
        pw_field.send_keys(login_pw)
        login_button.click()
        
        # 로그인 후 메인 페이지로 이동할 때까지 대기
        # TODO: 로그인 후 이동하는 페이지의 특정 요소를 찾도록 변경
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="item_body"]/div/div/div[1]'))
        )
        print("로그인 성공!")
        return True

    except TimeoutException:
        print("로그인 실패: 페이지 요소가 시간 내에 로드되지 않았습니다.")
        return False
    except Exception as e:
        print(f"로그인 중 오류가 발생했습니다: {e}")
        return False


driver = create_driver()
base_url = "https://computer.cnu.ac.kr/computer/notice/job.do"
regular_notices = []

print(f"일반 공지글 크롤링을 시작합니다. (기간: {args.start_date} ~ {args.end_date})")

# **로그인 프로세스 실행**
if not perform_login(driver):
    driver.quit()
    exit()

# 일반 공지글 목록 크롤링 (모든 페이지를 확인)
try:
    # 로그인 후, 원하는 공지사항 페이지로 이동
    driver.get(base_url)
    WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.XPATH, '//*[@id="item_body"]/div/div/div[3]/div[2]/div/div/div[2]/table/tbody/tr[1]')))
    
    page_num = 1
    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        notice_rows = soup.select('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(2) > table > tbody > tr')

        for row in notice_rows:
            cols = row.select('td')
            if len(cols) < 6:
                continue
            
            no_text = cols[0].get_text(strip=True)
            if no_text != "공지":
                title_element = cols[1].find('a')
                if not title_element: continue

                notice_date_str = cols[4].get_text(strip=True)
                notice_date = datetime.strptime(notice_date_str, '%y.%m.%d').date()

                if start_date <= notice_date <= end_date:
                    relative_url = title_element['href']
                    detail_url = base_url + relative_url
                    
                    regular_notices.append({
                        "no": no_text,
                        "date": notice_date_str,
                        "url": detail_url,
                        "notice": {}
                    })
                elif notice_date < start_date:
                    stop_crawling_regular = True
                    break

        next_page_link = driver.find_elements(By.XPATH, '//*[@id="item_body"]/div/div/div[3]/div[2]/div/div/div[3]/div/ul/li/a')
        next_button_found = False
        for link in next_page_link:
            if link.text == '다음':
                driver.execute_script("arguments[0].click();", link)
                time.sleep(2)
                next_button_found = True
                page_num += 1
                break
        
        if not next_button_found:
            break

except Exception as e:
    print(f"'공지'글 목록 크롤링 중 오류가 발생했습니다: {e}")
    driver.quit()
    exit()

print(f"총 {len(regular_notices)}개의 '공지'글 목록을 가져왔습니다. 상세 페이지 크롤링을 시작합니다...")

# 상세 페이지 크롤링
for i, notice in enumerate(regular_notices):
    retries = 3
    for attempt in range(retries):
        try:
            driver.get(notice['url'])
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//*[@id="item_body"]/div/div/div[3]/div[2]/div/div/div[1]/table/tbody/tr[1]/td')))

            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            title = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(1) > td')
            writer = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(2) > td')
            content_div = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(5) > td > div')
            files_ul = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(6) > td > div > ul')

            notice['notice']['title'] = title.get_text(strip=True) if title else ""
            notice['notice']['writer'] = writer.get_text(strip=True) if writer else ""

            content_text = ""
            images_list = []
            if content_div:
                for p in content_div.find_all('p'):
                    content_text += p.get_text(strip=True) + "\n"
                
                for img in content_div.find_all('img'):
                    img_src = img.get('src')
                    if img_src:
                        if not img_src.startswith(('http', '//')):
                            img_src = "https://computer.cnu.ac.kr" + img_src
                        images_list.append(img_src)
                        
            notice['notice']['content'] = content_text.strip()
            notice['notice']['images'] = images_list

            files_list = []
            if files_ul:
                for li in files_ul.find_all('li'):
                    file_name_link = li.find('a')
                    
                    if file_name_link:
                        files_list.append({
                            "name": file_name_link.get_text(strip=True)
                        })
            notice['notice']['files'] = files_list
            
            print(f"[{i+1}/{len(regular_notices)}] 크롤링 완료: {notice['no']} - {notice['notice']['title']}")
            break
            
        except (InvalidSessionIdException, WebDriverException) as e:
            print(f"[{i+1}/{len(regular_notices)}] 오류 발생! 드라이버를 재시작하고 {attempt + 1}/{retries}번 재시도합니다.")
            if attempt < retries - 1:
                driver.quit()
                driver = create_driver()
                time.sleep(5)
            else:
                print(f"[{i+1}/{len(regular_notices)}] 재시도 횟수 초과. 다음 항목으로 넘어갑니다.")
                continue

        except Exception as e:
            print(f"상세 페이지 크롤링 중 오류가 발생했습니다 ({notice['url']}): {e}")
            break

driver.quit()

# JSON 파일로 저장
today_date = datetime.now().strftime('%Y-%m-%d')
data_path = 'E:\Desktop\git\Chacha-Catch\Data-Process\data'
if not os.path.exists(data_path):
    os.makedirs(data_path)
file_path = os.path.join(data_path, f'job_regular_{start_date.strftime('%y%m%d')}-{end_date.strftime('%y%m%d')}.json')

with open(file_path, 'w+', encoding='utf-8') as f:
    json.dump(regular_notices, f, ensure_ascii=False, indent=4)

print("\n-----------------------------------------------------")
print("크롤링이 모두 완료되었습니다.")
print(f"'{args.start_date}'부터 '{args.end_date}'까지의 일반 공지글 정보가 파일에 저장되었습니다.")
print("-----------------------------------------------------")