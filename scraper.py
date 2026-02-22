import requests
from bs4 import BeautifulSoup

def get_exam_updates():
    url = "https://www.kollegeapply.com/articles/upcoming-government-exams-2025-26-complete-calendar-important-dates-and-notifications-1712"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    exams = []
    for item in soup.find_all("li"):
        text = item.get_text()
        if "Exam" in text or "Last date" in text or "Apply" in text:
            exams.append(text.strip())
    return exams
