import json
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, InvalidSessionIdException, WebDriverException
from bs4 import BeautifulSoup

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

driver = create_driver()
base_url = "https://computer.cnu.ac.kr/computer/notice/project.do"
pinned_notices = []

print(f"'공지'글 크롤링을 시작합니다. (crawler time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

# '공지'글 목록 크롤링 (모든 페이지를 확인)
try:
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
            if no_text == "공지":
                title_element = cols[1].find('a')
                if not title_element: continue

                relative_url = title_element['href']
                detail_url = base_url + relative_url
                
                pinned_notices.append({
                    "no": no_text,
                    "date": cols[4].get_text(strip=True),
                    "url": detail_url,
                    "notice": {}
                })

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

print(f"총 {len(pinned_notices)}개의 '공지'글 목록을 가져왔습니다. 상세 페이지 크롤링을 시작합니다...")

# 상세 페이지 크롤링
for i, notice in enumerate(pinned_notices):
    retries = 3
    for attempt in range(retries):
        try:
            driver.get(notice['url'])
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//*[@id="item_body"]/div/div/div[3]/div[2]/div/div/div[1]/table/tbody/tr[1]/td')))

            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            title = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(1) > td')
            writer = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(2) > td')
            email = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(4) > td')
            content_div = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(5) > td > div')
            files_ul = soup.select_one('#item_body > div > div > div:nth-child(3) > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(6) > td > div > ul')

            notice['notice']['title'] = title.get_text(strip=True) if title else ""
            notice['notice']['writer'] = writer.get_text(strip=True) if writer else ""
            notice['notice']['email'] = email.get_text(strip=True) if email else ""

            content_text = ""
            images_list = []
            if content_div:
                # 텍스트 추출
                for p in content_div.find_all('p'):
                    content_text += p.get_text(strip=True) + "\n"
                
                # 이미지 URL 추출
                for img in content_div.find_all('img'):
                    img_src = img.get('src')
                    if img_src:
                        # 상대 경로일 경우, 절대 경로로 변환
                        if not img_src.startswith(('http', '//')):
                            img_src = "https://computer.cnu.ac.kr" + img_src
                        images_list.append(img_src)
                        
            notice['notice']['content'] = content_text.strip()
            notice['notice']['images'] = images_list

            files_list = []
            if files_ul:
                for li in files_ul.find_all('li'):
                    file_link = li.find('a')
                    if file_link:
                        files_list.append(file_link.get_text(strip=True))
            notice['notice']['files'] = files_list
            
            print(f"[{i+1}/{len(pinned_notices)}] 크롤링 완료: {notice['no']} - {notice['notice']['title']}")
            break
            
        except (InvalidSessionIdException, WebDriverException) as e:
            print(f"[{i+1}/{len(pinned_notices)}] 오류 발생! 드라이버를 재시작하고 {attempt + 1}/{retries}번 재시도합니다.")
            if attempt < retries - 1:
                driver.quit()
                driver = create_driver()
                time.sleep(5)
            else:
                print(f"[{i+1}/{len(pinned_notices)}] 재시도 횟수 초과. 다음 항목으로 넘어갑니다.")
                continue

        except Exception as e:
            print(f"상세 페이지 크롤링 중 오류가 발생했습니다 ({notice['url']}): {e}")
            break

driver.quit()

file_name = f"sw_pinned_{datetime.now().strftime('%y%m%d')}.json"
if not os.path.exists('./data'):
    os.makedirs('./data')
file_path = os.path.join('./data', file_name)

# JSON 파일로 저장
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(pinned_notices, f, ensure_ascii=False, indent=4)

print("\n-----------------------------------------------------")
print("크롤링이 모두 완료되었습니다.")
print(f"{datetime.now().strftime('%Y-%m-%d-%H%M')}'공지'글 정보가 파일에 저장되었습니다.")
print("-----------------------------------------------------")