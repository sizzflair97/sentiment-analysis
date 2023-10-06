from unittest import result
import requests
import pandas as pd
from bs4 import BeautifulSoup
from time import sleep
from itertools import count
import tweepy

ARTICLE_BASE_URL = "https://gall.dcinside.com"

TWITTER_API_KEY = ""
TWITTER_API_KEY_SECRET = ""
TWITTER_BEARER_TOKEN = ""
TWITTER_ACCESS_TOKEN = ""
TWITTER_ACCESS_TOKEN_SECRET = ""

headers = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.53",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ko,en;q=0.9,en-US;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua-mobile": "?0",
}

#Decorator for preventing traffic ban
def sleeper(func):
    def inner(*args, **kwargs):
        sleep(0.5)
        return func(*args, **kwargs)
    return inner
BeautifulSoup = sleeper(BeautifulSoup)

class Inspector:
    """Object to manage web scrap process.
    """
    gall2url = {"theatergoing":"https://gall.dcinside.com/mini/board/lists/", "theaterM":"https://gall.dcinside.com/board/lists/", "musicalplay":"https://gall.dcinside.com/mini/board/lists/"}
    int2gall = {0:"theaterM", 1:"theatergoing", 2:"musicalplay"}

    def __init__(self) -> None:
        self.__df:pd.DataFrame

    @property
    def df(self):
        return self.__df

    def add_df_row(self, new_row):
        self.df.loc[0 if pd.isnull(self.df.index.max()) else self.df.index.max() + 1] = new_row

    def clear_df(self):
        self.__df = pd.DataFrame(columns=["source", "nickname", "date", "title", "text", "href"])

    def inspect_dc(self, url:str, params):
        article_response = requests.get(ARTICLE_BASE_URL+url, params=params, headers=headers)
        article_soup = BeautifulSoup(article_response.content, 'html.parser')
        writing_box = article_soup.find('div', attrs={"class":"writing_view_box"})
        write_div = writing_box.find('div', attrs={"class":"write_div"})
        title_div = article_soup.select_one('#container > section > article:nth-child(3) > div.view_content_wrap > header > div > h3 > span.title_subject')
        nickname_span = article_soup.select('#container > section > article:nth-child(3) > \
                                div.view_content_wrap > header > div > div > div.fl > span.nickname > em')[0]
        date_span = article_soup.select('#container > section > article:nth-child(3) > \
                                div.view_content_wrap > header > div > div > div.fl > span.gall_date')[0]
        self.add_df_row(("dc", nickname_span.get_text(), date_span.get_text(), title_div.get_text(), write_div.get_text('\n'), ARTICLE_BASE_URL+url))
    
    def search(self, keyword:str, fromDate, toDate):
        for key in self.int2gall.keys():
            self.clear_df()
            self.search_dc(keyword, key, fromDate, toDate)
        self.clear_df()
        self.search_twitter(keyword, fromDate, toDate)

    def search_dc(self, keyword:str, id = 1, fromDate = "202206100000", toDate = "202212010000"):
        fromDate = [*map(int, [fromDate[2:4], fromDate[4:6], fromDate[6:8]])]
        toDate = [*map(int,[toDate[2:4], toDate[4:6], toDate[6:8]])]
        id = self.int2gall[id]
        
        #set params
        params = {"id":id,"page":"1", "search_pos":"", "s_type":"search_subject_memo",\
            "s_keyword":keyword}
        
        counter = count()
        for i in counter:
            #reset page to 1
            params["page"] = '1'

            #get search page
            search_response = requests.get(self.gall2url[id], params=params, headers=headers)
            search_soup = BeautifulSoup(search_response.content, 'html.parser')

            #find articles
            searched_articles = search_soup.select('.us-post')
            num_searched = len(searched_articles)

            #find #articles of current page 
            start_page, end_page = 0, 0
            if num_searched == 0:
                start_page, end_page = 1,0
            elif num_searched < 20:
                start_page, end_page = 1,1
            else:
                page_end_button_list = search_soup.select("a.page_end")
                if len(page_end_button_list) == 2:
                    start_page, end_page = 1, int(page_end_button_list[0]['href'].split('&page=')[1].split("&")[0]) + 1
                else:
                    #find page buttons area
                    page_box = search_soup.select('#container > section.left_content.result article > div.bottom_paging_wrap > '\
                                        'div.bottom_paging_box > a')
                    start_page = 1
                    end_page = 1 if len(page_box) == 1 else page_box[-2].text.strip()
                    #control string operation
                    if isinstance(end_page, str):
                        end_page = 1 if '이전' in end_page else int(end_page)

            #find next search position
            next_search_pos = search_soup.select('a.search_next')
            next_search_pos = next_search_pos[0]['href'].split('&search_pos=')[1].split("&")[0] if next_search_pos \
                else 'last'

            #search different pages
            for page in range(start_page, end_page+1):
                if page != start_page:
                    params["page"] = str(page)
                    search_response = requests.get(self.gall2url[id], params=params, headers=headers)
                    search_soup = BeautifulSoup(search_response.content, 'html.parser')
                    searched_articles = search_soup.select('.us-post')
                
                print(f'page: {page}, searched articles: {len(searched_articles)}')
                if len(searched_articles) != 0:
                    for article in searched_articles:
                        result_url = article.find('a')["href"]
                        print(result_url, id)
                        if result_url[0] == '/':
                            try:
                                self.inspect_dc(result_url, {"id":id,'page':str(page)})
                            except AttributeError:
                                continue
            
            params["search_pos"] = str(next_search_pos)
            print(i, len(params["search_pos"]), type(params["search_pos"]))
            self.save_csv(keyword, id)

            if params["search_pos"] == "last":
                break

            try:
                assert article
            except UnboundLocalError:
                print("no result.")
                continue

            date = article.select_one('.gall_date').get_text().split('.')
            date = [int(i.strip()) for i in date]
            print(date)
            if date < fromDate:
                break
    
    def search_twitter(self, keyword:str, fromDate = "202206100000", toDate = "202212010000"):
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_KEY_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)

        for tweet in tweepy.Cursor(api.search_full_archive, label="SKW", query=keyword, fromDate=fromDate, toDate=toDate).items():
        # for tweet in tweepy.Cursor(api.search_30_day, label="research", query=keyword, fromDate="202211241200", toDate=toDate).items(): # code for search 30 day, for not-academic-access user.
            nickname = tweet.user.screen_name
            date = tweet.created_at
            text = tweet.text
            href = f"https://twitter.com/twitter/status/{tweet.id}"
            self.add_df_row(("twitter", nickname, date, "", text, href))
            print(date)

        self.save_csv(keyword, src="twitter")

    def save_csv(self, query, src=None):
        if src:
            src = "_" + src
        self.df.to_csv(f'./search_data/{query}{src}.csv', encoding="utf-8-sig", index=False)
        print("df saved.")

if __name__ == '__main__':
    inspector = Inspector()
    # query = input("input query: ")
    timetable = { # string includes duration to search
        "30days":("202212010000", "202301110000"),
        "웃는남자":("202206100000", "202301110000"),
        "원더보이":("202208190000", "202301110000"),
        "불가불가":("202203260000", "202301110000")
        }
    queries = [#("웃는 남자", *timetable["웃는남자"]),
               ("원더보이", *timetable["원더보이"]),
            #    ("불가불가", *timetable["불가불가"]]
            # ("원더보이", *timetable["30days"]),
            # ("웃는남자", *timetable["웃는남자"]),
            # ("웃남", *timetable["웃는남자"]),
            # ("웃는 남자", *timetable["30days"]),
            # ("불가불가", *timetable["30days"])
            ]
    for query in queries:
        inspector.search(*query)
