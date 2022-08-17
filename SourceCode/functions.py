# 图像处理标准库
from PIL import Image
# web测试
from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.request import urlopen
# 鼠标操作
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
# 等待时间 产生随机数
import time, random
import re
import os
import requests
import json
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED


class Browser:
    def __init__(self, url='https://www.vipcdk.com/myorders.htm'):
        self.driver = webdriver.Chrome(executable_path='chromedriver.exe')
        self.driver.get(url)
        self.driver.implicitly_wait(2)
        self.input = self.driver.find_element_by_class_name('search_input')
        self.button = self.driver.find_element_by_id('yzm')

    def is_similar(self, image1, image2, x, y, sens=0):
        pixel1 = image1.getpixel((x, y))
        pixel2 = image2.getpixel((x, y))
        # 截图像素也许存在误差，50作为容差范围
        if abs(pixel1[0] - pixel2[0]) >= 50 - sens or abs(pixel1[1] - pixel2[1]) >= 50 - sens or \
                abs(pixel1[2] - pixel2[2]) >= 50 - sens:
            return False
        return True

    def get_diff_location(self, image1, image2, sensitivity=0):
        # （825,1082）（335,463）为滑块图片区域，可根据实际情况修改
        for i in range(0, 200):
            for j in range(0, 150):
                # 遍历原图与缺口图像素值寻找缺口位置
                if self.is_similar(image1, image2, i, j, sensitivity) == False:
                    return i
        return -1

    def crackCode(self, slider, left, top, width, height, mark='1'):
        count = 2
        first = True
        while True:
            try:
                if first:
                    slider.click()
                    first = False
                    time.sleep(2.5)
                    self.driver.save_screenshot('.\\pictures\\' + mark + 'screenshot.png')
                    picture = Image.open('.\\pictures\\' + mark + 'screenshot.png').crop((left, top, width, height))
                    picture.save('.\\pictures\\' + mark + 'phonto2.png')
                    # time.sleep(1)
                    diff = self.get_diff_location(Image.open('.\\pictures\\' + mark + 'phonto1.png'),
                                                  Image.open('.\\pictures\\' + mark + 'phonto2.png'))
                    # print(diff+50)
                    ActionChains(self.driver).drag_and_drop_by_offset(slider, diff + 55, 0).perform()
                else:
                    ActionChains(self.driver).drag_and_drop_by_offset(slider,
                                                                      diff + 55 + random.randint(-6, 6), 0).perform()
                if not slider.is_displayed():
                    raise Exception
                count -= 1
                if count == 0:
                    return False
            except Exception:
                return True

    def findWebSources(self, seed, days=30, price=0, flag1=False, flag2=True, mark='1'):
        self.input.send_keys(seed)
        self.button.click()
        time.sleep(2.5)
        slider = self.driver.find_element_by_class_name('slide_block')
        canvas = self.driver.find_element_by_class_name('tncode_canvas_bg')
        left = canvas.location['x'] + 55
        top = canvas.location['y']
        elementWidth = canvas.location['x'] + 250
        elementHeight = canvas.location['y'] + 150
        # print(left,top,elementWidth,elementHeight)
        self.driver.save_screenshot('.\\pictures\\' + mark + 'screenshot.png')
        picture = Image.open('.\\pictures\\' + mark + 'screenshot.png').crop((left, top, elementWidth, elementHeight))
        picture.save('.\\pictures\\' + mark + 'phonto1.png')
        if (self.crackCode(slider, left, top, elementWidth, elementHeight, mark)):
            if flag2:
                currentPath = os.getcwd() + '\\pictures\\'
                os.remove(currentPath + mark + 'screenshot.png')
                os.remove(currentPath + mark + 'phonto1.png')
                os.remove(currentPath + mark + 'phonto2.png')
            soup = BeautifulSoup(self.driver.page_source)
            try:
                search_list = soup.find('div', class_='search_list').find('tr')  # .find_next_sibling()
            except:
                self.driver.close()
                return True, []
            lists = []
            nowtime = datetime.datetime.now()
            for children in search_list.find_next_siblings():
                attributes = []
                times = []
                for child in children.children:
                    if child.string != '\n':
                        attributes.append(child.string)
                for n in re.findall('\d+', attributes[0]):
                    times.append(int(n))
                theTime = datetime.datetime(times[0], times[1], times[2], times[3], times[4], times[5])
                theDays = (nowtime - theTime).days
                if theDays <= days and float(attributes[3]) >= 4.0 and attributes[3] == attributes[4]:
                    entry = [attributes, (nowtime - theTime).days]
                    lists.append(entry)
            # self.driver.close()
            return True, lists
        else:
            if flag2:
                currentPath = os.getcwd() + '\\pictures\\'
                os.remove(currentPath + mark + 'screenshot.png')
                os.remove(currentPath + mark + 'phonto1.png')
                os.remove(currentPath + mark + 'phonto2.png')
            self.driver.close()
            return False, []

    def getCardInfos(self, lists, is_stop, is_wait=False, func=None):  # 可选择优化，浏览器池
        for entry in lists:
            if is_stop[0]:
                break
            url = 'https://www.vipcdk.com/orderquery.htm?orderid=' + entry[0][1]
            self.driver.get(url)
            soup = BeautifulSoup(self.driver.page_source)
            cardInfo = soup.find('div', id='cardinfo').text
            entry.append(cardInfo)
            print(entry)
            '''if (not is_wait):
                func(entry)'''


class ThreadManagement:
    def __init__(self, max_workers, url='https://www.vipcdk.com/myorders.htm'):
        self.max_workers = max_workers
        self.url = url
        self.ThreadPool = ThreadPoolExecutor(self.max_workers)
        self.ThreadQueue = []
        self.endFlag = [False]

    def multiFunc(self, lists, errorSeeds, timeoutSeeds, is_wait, func, progressBar, seed, *args):
        brower = Browser()
        flag, list = brower.findWebSources(seed, *args)
        if progressBar != None:
            progressBar.setMaximum(len(list) - 1)
        if flag:
            brower.getCardInfos(list, self.endFlag, is_wait, func)  # 获取cardInfo
            if (len(list) == 0):
                errorSeeds.append(seed)
            else:
                lists.extend(list)
        else:
            timeoutSeeds.append(seed)

    def multiFind(self, seeds, days=60, price=0, flag1=False, flag2=True
                  , index=0, is_wait=False, func=None, progressBar=None):
        if len(seeds) <= 0:
            raise ValueError
        self.endFlag[0] = False
        lists = []
        errorSeeds = []
        timeoutSeeds = []
        for i in range(1, len(seeds) + 1):
            t = self.ThreadPool.submit(self.multiFunc, lists, errorSeeds, timeoutSeeds, is_wait, func, progressBar,
                                       seeds[i - 1], days, price, flag1, flag2, str(i))
            if is_wait:
                t.add_done_callback(func)
            self.ThreadQueue.append(t)
        wait(self.ThreadQueue, return_when=ALL_COMPLETED)
        self.ThreadQueue.clear()
        if is_wait:
            self.listsSort(lists, index)
            return lists, errorSeeds, timeoutSeeds
        else:
            return lists, errorSeeds, timeoutSeeds

    def stopAllThread(self):
        for t in self.ThreadQueue:
            t.cancel()
        self.endFlag[0] = True

    def changeThreadNum(self, number):
        wait(self.ThreadQueue, return_when=ALL_COMPLETED)
        self.max_workers = number
        self.ThreadPool = ThreadPoolExecutor(number)

    def listsSort(self, lists, index):
        if index == 1:
            lists.sort(key=lambda x: float(x[0][3]), reverse=True)
        if index == 2:
            lists.sort(key=lambda x: (x[1]))

    def __del__(self):
        self.ThreadPool.shutdown(True)

threads = ThreadManagement(3)
lines = open("D:\\Code\\venv\\Include\\Sources\\PassWord.txt").readlines()
seeds=[]
for line in lines:
    line = line.rstrip('\n')
    seeds.append(line)
lists, errorSeeds, timeoutSeeds = threads.multiFind(seeds, index=1)
print(lists)
