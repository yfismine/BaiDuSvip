from bs4 import BeautifulSoup
import requests
import random
import re
import datetime
import time
# import threading
# from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED
from PyQt5.QtCore import QThread, QThreadPool, QRunnable, pyqtSignal, QObject

class Sources:
    def __init__(self, url='https://www.mianfeivip.com', ipPool=None):
        self.url = url
        self.ipPool = ipPool
        self.headersList=[
            {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Mobile Safari/537.36'},
            {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
        ]

    def findWebSources(self, seed, days=30, price=0, flag=False):
        headers = random.choice(self.headersList)
        try:
            headers = random.choice(self.headersList)
            if self.ipPool == None:
                response = requests.post(self.url+'/orderquery.htm', timeout=1, data={'st': 'contact', 'kw': seed}
                                         , headers=headers)
            else:
                ip = random.choice(self.ipPool)
                response = requests.post(self.url+'/orderquery.htm', timeout=1,
                                         data={'st': 'contact', 'kw': seed}
                                         , headers=headers, proxies=ip)
        except:
            return False, []
        soup = BeautifulSoup(response.text,'html.parser')
        try:
            search_list = soup.find('div', class_='search_list').find('tr')
        except:
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
            if ((nowtime - theTime).days <= days and float(attributes[3]) >= price and attributes[3] == attributes[4]):
                # 剩余时间在要就天数和价格在要求范围内的支付订单
                if (flag):
                    if float(attributes[3]) in [1.68, 3, 4.5, 5.8, 12.8]:
                        entry = [attributes, (nowtime - theTime).days]
                        lists.append(entry)
                    else:
                        continue
                else:
                    entry = [attributes, (nowtime - theTime).days]
                    lists.append(entry)
        return True, lists


class Thread(QRunnable):

    def __init__(self, obj, lists, seccessSeeds, errorSeeds, timeoutSeeds, index, is_single, url, ipPool, seed, *args):
        super().__init__()
        self.obj = obj
        self.lists = lists
        self.seccessSeeds = seccessSeeds
        self.errorSeeds = errorSeeds
        self.timeoutSeeds = timeoutSeeds
        self.index = index
        self.is_single = is_single
        self.url = url
        self.ipPool = ipPool
        self.seed = seed
        self.args = args

    def run(self):
        sources = Sources(self.url, self.ipPool)
        flag, list = sources.findWebSources(self.seed, *self.args)
        if self.is_single:
            self.obj.sinOut_3.emit(len(list))
        if flag:
            if (len(list) == 0):
                self.errorSeeds.append(self.seed)
            else:
                self.seccessSeeds.append(self.seed)
                self.lists.extend(list)
        else:
            self.timeoutSeeds.append(self.seed)
        if self.index == 0:   #getCardInfo
            for entry in list:
                url = self.url+'/checkgoods.htm?orderid=' + entry[0][1]
                cardInfo = requests.get(url).json()['msg']
                entry.append(cardInfo)
                self.obj.sinOut_4.emit(entry, self.is_single)
            if not self.is_single:
                self.obj.sinOut_5.emit()


class ThreadManagement(QObject):
    sinOut_1 = pyqtSignal(list, bool)
    sinOut_2 = pyqtSignal(list, list, list, bool)
    sinOut_3 = pyqtSignal(int)
    sinOut_4 = pyqtSignal(list, bool)
    sinOut_5 = pyqtSignal()

    def __init__(self, max_workers, func1, func2, func3, func4, url='https://www.mianfeivip.com', ipPool=None):
        super().__init__()
        self.max_workers = max_workers
        self.url = url
        self.ipPool = ipPool
        self.is_stop = False
        self.threadPool = QThreadPool()
        self.sinOut_1.connect(func2)
        self.sinOut_2.connect(func3)
        self.sinOut_3.connect(func1)
        self.sinOut_4.connect(func2)
        self.sinOut_5.connect(func4)

    def start(self, seeds, days=30, price=0, flag=False, index=0):
        if len(seeds) <= 0:
            raise ValueError
        if index != 0:
            self.sinOut_3.emit(0)
        self.is_stop = False
        self.lists = []
        self.seccessSeeds = []
        self.errorSeeds = []
        self.timeoutSeeds = []
        self.threadPool.setMaxThreadCount(self.max_workers)
        seedsLen=len(seeds)
        for i in range(1, seedsLen + 1):
            if seedsLen == 1:
                task_thread = Thread(self, self.lists, self.seccessSeeds, self.errorSeeds, self.timeoutSeeds, index,
                                     True, self.url, self.ipPool, seeds[i - 1]
                                     , days, price, flag)
            else:
                task_thread = Thread(self, self.lists, self.seccessSeeds, self.errorSeeds, self.timeoutSeeds, index,
                                     False, self.url, self.ipPool, seeds[i - 1]
                                     , days, price, flag)
            task_thread.setAutoDelete(True)
            self.threadPool.start(task_thread)
        self.threadPool.waitForDone()
        if index != 0:
            self.listsSort(self.lists, index)
            self.sinOut_3.emit(len(self.lists))
            for entry in self.lists:
                url = self.url+'/checkgoods.htm?orderid=' + entry[0][1]
                cardInfo = requests.get(url).json()['msg']
                entry.append(cardInfo)
                self.sinOut_1.emit(entry, True)
        #print(self.seccessSeeds,self.errorSeeds,self.timeoutSeeds)
        self.sinOut_2.emit(self.seccessSeeds, self.errorSeeds, self.timeoutSeeds, self.is_stop)

    def stopAllThread(self):
        self.threadPool.clear()
        self.is_stop = True

    def changeThreadNum(self, number):
        self.threadPool.waitForDone()
        self.max_workers = number

    def changeWebsite(self,url):
        self.threadPool.waitForDone()
        self.url=url

    def listsSort(self, lists, index):
        if index == 1:
            lists.sort(key=lambda x: (x[1]))
        if index == 2:
            lists.sort(key=lambda x: float(x[0][3]), reverse=True)


'''class ThreadManagement:   #明天改进为Qt形式的工作进程
    def __init__(self,max_workers,url='http://fulivip.com/orderquery.htm',ipPool=None,mainWindow=None):
        self.max_workers=max_workers
        self.url=url
        self.ipPool=ipPool
        self.ThreadPool=ThreadPoolExecutor(self.max_workers)
        self.ThreadQueue=[]
        self.mainWindow=mainWindow

    def multiFunc(self,lists, errorSeeds, timeoutSeeds,index,is_singal, seed, *args):
        sources =Sources(self.url,self.ipPool)
        flag, list = sources.findWebSources(seed, *args)
        if is_singal and self.mainWindow.progressBar.maximum() !=len(list):
            self.mainWindow.progressBar.setMaximum(len(list))
        if flag:
            if (len(list) == 0):
                errorSeeds.append(seed)
            else:
                lists.extend(list)
        else:
            timeoutSeeds.append(seed)
        if index==0:
            for entry in list:
                url = 'http://fulivip.com/checkgoods.htm?orderid=' + entry[0][1]
                cardInfo = requests.get(url).json()['msg']
                entry.append(cardInfo)
                self.mainWindow.progressFunc1(entry)


    def multiFind(self,seeds, days=30, price=0, flag=False, index=0,ipPool=None):
        if len(seeds) <= 0:
            raise ValueError
        if len(seeds)!=1:
            self.mainWindow.progressBar.setMaximum(len(seeds)-1)
        lists = []
        errorSeeds = []
        timeoutSeeds = []
        for i in range(1,len(seeds)+1):
            if len(seeds)==1:
                t = self.ThreadPool.submit(self.multiFunc, lists, errorSeeds, timeoutSeeds, index,True,
                                           seeds[i - 1], days, price, flag)
            else:
                t = self.ThreadPool.submit(self.multiFunc, lists, errorSeeds, timeoutSeeds, index,False,
                                           seeds[i - 1], days, price, flag)
            self.ThreadQueue.append(t)
        wait(self.ThreadQueue, return_when=ALL_COMPLETED)
        self.ThreadQueue.clear()
        if index!=0:
            self.listsSort(lists, index)
        return lists, errorSeeds, timeoutSeeds

    def stopAllThread(self):
        for i in range(len(self.ThreadQueue)-1,-1,-1):
           if not self.ThreadQueue[i].cancel():
               break

    def changeThreadNum(self,number):
        wait(self.ThreadQueue, return_when=ALL_COMPLETED)
        self.max_workers=number
        self.ThreadPool=ThreadPoolExecutor(number)

    def listsSort(self,lists, index):
        if index == 1:
            lists.sort(key=lambda x: float(x[0][3]), reverse=True)
        if index == 2:
            lists.sort(key=lambda x: (x[1]))
    def __del__(self):
        self.ThreadPool.shutdown(True)'''

'''threads=ThreadManagement(3)
lists, errorSeeds, timeoutSeeds=threads.multiFind(['1008611'],index=1)
print(lists)'''