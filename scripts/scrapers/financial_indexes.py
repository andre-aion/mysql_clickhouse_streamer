import asyncio
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from config.checkpoint import checkpoint_dict
from scripts.utils.mylogger import mylogger
from scripts.github_and_bsscraper_interface import Scraper

logger = mylogger(__file__)

class FinancialIndexes(Scraper):
    coin_abbr = {
        'nasdaq':'ndaq',
        'sp':'sp',
        'russell':'iwv'
    }

    def __init__(self, items):
        Scraper.__init__(self,collection='external_daily')
        self.items = items
        self.item_name = 'russell'
        self.close = 'close'
        self.volume = 'volume'
        self.url = 'https://www.nasdaq.com/symbol/{}/historical'\
            .format(self.coin_abbr[self.item_name])

        # checkpointing
        self.checkpoint_key = 'indexscraper'
        self.key_params = 'checkpoint:' + self.checkpoint_key
        self.checkpoint_column = 'close'
        self.dct = checkpoint_dict[self.checkpoint_key]
        self.DATEFORMAT_finindex = '%m/%d/%Y'
        self.offset = self.initial_date

        self.scraper_name = 'financial indexes'

    async def update(self):
        try:
            for self.item_name in self.items:
                if self.item_is_up_to_date(self.checkpoint_column,self.item_name):
                    pass
                else:
                    yesterday = datetime.combine(datetime.today().date(),datetime.min.time()) - timedelta(days=1)
                    self.offset = self.offset + timedelta(days=1)
                    url = 'https://www.nasdaq.com/symbol/{}/historical'\
                        .format(self.coin_abbr[self.item_name])
                    # launch url
                    self.driver.implicitly_wait(10)
                    self.driver.get(url)
                    await asyncio.sleep(5)
                    if self.scrape_period == 'history':
                        # click on the dropdown list to expose it
                        dropdown = self.driver.find_element_by_id('ddlTimeFrame')
                        logger.warning('DROPDOWN:%s', dropdown)
                        self.driver.execute_script("arguments[0].click();", dropdown)
                        await asyncio.sleep(3)

                        # click on the exposed link
                        link = self.driver.find_element_by_xpath("//select[@id='ddlTimeFrame']/option[@value='2y']")
                        logger.warning('LINK:%s', link)

                        link.click()
                        await asyncio.sleep(5)

                    count = 0
                    # get soup
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    div = soup.find('div', attrs={'id': 'quotes_content_left_pnlAJAX'})
                    rows = div.find('tbody').findAll('tr')
                    for row in rows:
                        if count >= 1:
                            # logger.warning('row:%s',row)
                            item = {}
                            item['timestamp'] = datetime.strptime(row.findAll('td')[0].contents[0].strip(),
                                                             self.DATEFORMAT_finindex)
                            item[self.close] = float(row.findAll('td')[4].contents[0].strip().replace(',', ''))
                            item[self.volume] = float(row.findAll('td')[5].contents[0].strip().replace(',', ''))

                            #logger.warning('%s: %s %s data added', self.item_name, item['timestamp'], item[self.volume])
                            self.process_item(item,self.item_name)
                        if self.scrape_period != 'history':
                            if count > 1:
                                break
                        count += 1

                    logger.warning('%s SCRAPER %s COMPLETED:', self.item_name.upper(), self.scrape_period)

                    # PAUSE THE LOADER, SWITCH THE USER AGENT, SWITCH THE IP ADDRESS
                    self.update_proxy()

        except Exception:
            logger.error('financial indicies:', exc_info=True)
